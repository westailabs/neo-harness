"""Typer CLI entrypoints: neo start | resume | status | end."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from neo_harness import __version__
from neo_harness.config import get_settings
from neo_harness.harness.budget import Budget
from neo_harness.harness.loop import HarnessLoop
from neo_harness.harness.memory import MemoryBundle
from neo_harness.neo4j.client import Neo4jClient
from neo_harness.neo4j import queries
from neo_harness.neo4j.schema import setup_schema
from neo_harness.providers import get_provider
from neo_harness.schemas.reflection import ReflectionTrigger
from neo_harness.schemas.session import HarnessState, Session, SessionStatus

app = typer.Typer(
    name="neo",
    help="neo-harness — agent harness with explicit state machine + Neo4j memory",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

# Local pointer so `neo status` / `neo end` work without always querying Neo4j.
STATE_DIR = Path.home() / ".neo-harness"
ACTIVE_FILE = STATE_DIR / "active_session.json"


def _ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _save_active(session_id: str) -> None:
    _ensure_state_dir()
    ACTIVE_FILE.write_text(json.dumps({"session_id": session_id}), encoding="utf-8")


def _load_active_id() -> str | None:
    if not ACTIVE_FILE.exists():
        return None
    try:
        data = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
        return data.get("session_id")
    except (json.JSONDecodeError, OSError):
        return None


def _clear_active() -> None:
    if ACTIVE_FILE.exists():
        ACTIVE_FILE.unlink()


def _client() -> Neo4jClient:
    s = get_settings()
    return Neo4jClient(
        uri=s.neo4j_uri,
        user=s.neo4j_user,
        password=s.neo4j_password,
        database=s.neo4j_database,
    )


def _require_neo4j(client: Neo4jClient) -> None:
    client.connect()
    if not client.verify():
        console.print(
            "[red]Cannot connect to Neo4j.[/red] "
            f"URI={client.uri} — check NEO4J_URI / NEO4J_PASSWORD and that the DB is running."
        )
        raise typer.Exit(code=1)


def _print_session(session: Session, *, title: str = "Session") -> None:
    table = Table(title=title, show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="cyan")
    table.add_column("value")
    table.add_row("id", session.id)
    table.add_row("task", session.task)
    table.add_row("status", session.status.value)
    table.add_row("state", session.state.value)
    table.add_row("goal", session.goal or "—")
    table.add_row("steps / actions / reflections", f"{session.step_count} / {session.action_count} / {session.reflection_count}")
    table.add_row("created", str(session.created_at))
    table.add_row("updated", str(session.updated_at))
    if session.last_error:
        table.add_row("last_error", session.last_error)
    console.print(table)


@app.callback()
def main_callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
) -> None:
    if version:
        console.print(f"neo-harness {__version__}")
        raise typer.Exit()


@app.command("init-db")
def init_db() -> None:
    """Create Neo4j constraints and indexes."""
    client = _client()
    _require_neo4j(client)
    try:
        setup_schema(client)
        console.print("[green]Schema ready.[/green]")
    finally:
        client.close()


@app.command("start")
def start(
    task: str = typer.Argument(..., help="Task description for the new session"),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="mock | grok_build | xai (default: env NEO_PROVIDER or mock)"
    ),
    steps: Optional[int] = typer.Option(
        None, "--steps", "-n", help="Max loop iterations this run (default: settings)"
    ),
    no_run: bool = typer.Option(
        False, "--no-run", help="Create session only; do not enter the loop"
    ),
) -> None:
    """Start a new session: INIT → PLAN → ACT → …"""
    settings = get_settings()
    client = _client()
    _require_neo4j(client)
    try:
        setup_schema(client)
        session = Session(task=task, status=SessionStatus.ACTIVE, state=HarnessState.INIT)
        queries.upsert_session(client, session)
        _save_active(session.id)

        console.print(Panel.fit(f"[bold]Started session[/bold] {session.id}", border_style="green"))
        _print_session(session)

        if no_run:
            console.print("[dim]Created without running loop (--no-run). Use `neo resume` later.[/dim]")
            return

        prov = get_provider(provider or settings.provider)
        memory = MemoryBundle.from_client(client, goal=task)
        budget = Budget(
            max_steps=settings.max_steps,
            max_tokens=settings.max_tokens,
            reflect_every_n_actions=settings.reflect_every_n,
        )
        loop = HarnessLoop(
            client=client,
            provider=prov,
            memory=memory,
            budget=budget,
            max_iterations=steps or settings.loop_iterations,
        )
        console.print(f"[dim]Provider: {prov.name} · running loop…[/dim]")
        result = asyncio.run(loop.run(session, steps=steps or settings.loop_iterations))

        console.print()
        for line in result.history:
            console.print(f"  [dim]•[/dim] {line}")
        console.print()
        _print_session(result.session, title="Session after run")
        if result.error:
            console.print(f"[yellow]Loop ended with error:[/yellow] {result.error}")
        if result.final_state.value in ("DONE", "FAILED"):
            _clear_active()
    finally:
        client.close()


@app.command("resume")
def resume(
    session_id: str = typer.Argument(..., help="Session id to resume"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p"),
    steps: Optional[int] = typer.Option(None, "--steps", "-n"),
) -> None:
    """Resume an existing session with full Neo4j context."""
    settings = get_settings()
    client = _client()
    _require_neo4j(client)
    try:
        session = queries.get_session(client, session_id)
        if session is None:
            console.print(f"[red]Session not found:[/red] {session_id}")
            raise typer.Exit(1)

        if session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
            console.print(
                f"[yellow]Session is {session.status.value}.[/yellow] "
                "Reopening as active for resume."
            )
            session.status = SessionStatus.ACTIVE
            if session.state in (HarnessState.DONE, HarnessState.FAILED):
                # Terminal states cannot continue — move to PLAN via BLOCKED? No.
                # DONE/FAILED have no exits. For resume of completed work we
                # force state to PLAN by rewriting (admin override for resume).
                session.state = HarnessState.PLAN
            session.ended_at = None
            session.touch()
            queries.upsert_session(client, session)

        if session.state == HarnessState.BLOCKED:
            # Unblock into PLAN on resume.
            session.state = HarnessState.PLAN
            session.status = SessionStatus.ACTIVE
            queries.upsert_session(client, session)

        _save_active(session.id)
        console.print(Panel.fit(f"[bold]Resuming[/bold] {session.id}", border_style="blue"))
        _print_session(session)

        # Hydrate working memory from recent episodes.
        episodes = queries.list_episodes(client, session.id, limit=20)
        prov = get_provider(provider or settings.provider)
        memory = MemoryBundle.from_client(client, goal=session.goal or session.task)
        for ep in episodes[-10:]:
            memory.working.push_observation(ep.summary, meta={"kind": ep.kind.value})

        budget = Budget(
            max_steps=settings.max_steps,
            max_tokens=settings.max_tokens,
            reflect_every_n_actions=settings.reflect_every_n,
        )
        # Account for prior steps roughly so budgets still apply.
        budget.steps_used = min(session.step_count, settings.max_steps - 1)

        loop = HarnessLoop(
            client=client,
            provider=prov,
            memory=memory,
            budget=budget,
            max_iterations=steps or settings.loop_iterations,
        )
        console.print(f"[dim]Provider: {prov.name} · {len(episodes)} prior episodes · running…[/dim]")
        result = asyncio.run(loop.run(session, steps=steps or settings.loop_iterations))

        console.print()
        for line in result.history:
            console.print(f"  [dim]•[/dim] {line}")
        console.print()
        _print_session(result.session, title="Session after resume")
        if result.final_state.value in ("DONE", "FAILED"):
            _clear_active()
    finally:
        client.close()


@app.command("status")
def status(
    session_id: Optional[str] = typer.Option(
        None, "--session", "-s", help="Session id (default: active local pointer or latest active)"
    ),
    all_sessions: bool = typer.Option(False, "--all", "-a", help="List recent sessions"),
) -> None:
    """Show current session status and recent episodes."""
    client = _client()
    _require_neo4j(client)
    try:
        if all_sessions:
            sessions = queries.list_sessions(client, limit=15)
            table = Table(title="Recent sessions")
            table.add_column("id", style="cyan")
            table.add_column("status")
            table.add_column("state")
            table.add_column("task")
            table.add_column("updated")
            for s in sessions:
                table.add_row(
                    s.id[:8] + "…",
                    s.status.value,
                    s.state.value,
                    s.task[:48] + ("…" if len(s.task) > 48 else ""),
                    str(s.updated_at)[:19],
                )
            console.print(table)
            return

        sid = session_id or _load_active_id()
        session: Session | None = None
        if sid:
            session = queries.get_session(client, sid)
        if session is None:
            session = queries.get_active_session(client)
        if session is None:
            console.print("[yellow]No active session.[/yellow] Start one with `neo start \"…\"`.")
            raise typer.Exit(0)

        _print_session(session, title="Current session")
        episodes = queries.list_episodes(client, session.id, limit=10)
        if episodes:
            et = Table(title="Recent episodes (last 10)")
            et.add_column("kind")
            et.add_column("state")
            et.add_column("summary")
            for ep in episodes[-10:]:
                et.add_row(ep.kind.value, ep.state, ep.summary[:80])
            console.print(et)
        else:
            console.print("[dim]No episodes yet.[/dim]")
    finally:
        client.close()


@app.command("end")
def end(
    session_id: Optional[str] = typer.Option(
        None, "--session", "-s", help="Session id (default: active)"
    ),
    fail: bool = typer.Option(False, "--fail", help="Mark as failed instead of completed"),
) -> None:
    """End the active (or specified) session and force a final reflection when possible."""
    settings = get_settings()
    client = _client()
    _require_neo4j(client)
    try:
        sid = session_id or _load_active_id()
        if not sid:
            active = queries.get_active_session(client)
            sid = active.id if active else None
        if not sid:
            console.print("[yellow]No session to end.[/yellow]")
            raise typer.Exit(0)

        session = queries.get_session(client, sid)
        if session is None:
            console.print(f"[red]Session not found:[/red] {sid}")
            raise typer.Exit(1)

        # Best-effort end-of-session reflection if still mid-loop.
        if session.state not in (HarnessState.DONE, HarnessState.FAILED) and session.state != HarnessState.INIT:
            try:
                from neo_harness.harness.reflection import run_reflection
                from neo_harness.harness.memory import Neo4jEpisodicMemory

                prov = get_provider(settings.provider)
                episodic = Neo4jEpisodicMemory(client)
                recent = episodic.list_for_session(session.id, limit=15)
                reflection = asyncio.run(
                    run_reflection(
                        prov,
                        session,
                        plan=None,
                        recent_episodes=recent,
                        trigger=ReflectionTrigger.SESSION_END,
                    )
                )
                episodic.store_reflection(reflection)
                session.reflection_count += 1
                console.print(
                    f"[dim]Final reflection:[/dim] {reflection.what_happened[:120]} "
                    f"→ {reflection.next_action.value}"
                )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[dim]Skipped final reflection: {exc}[/dim]")

        status = SessionStatus.FAILED if fail else SessionStatus.COMPLETED
        session.state = HarnessState.FAILED if fail else HarnessState.DONE
        session.mark_ended(status)
        queries.upsert_session(client, session)
        if _load_active_id() == session.id:
            _clear_active()

        console.print(Panel.fit(f"[bold]Ended[/bold] {session.id} as {status.value}", border_style="red" if fail else "green"))
        _print_session(session)
    finally:
        client.close()


@app.command("version")
def version_cmd() -> None:
    """Print package version."""
    console.print(f"neo-harness {__version__}")


if __name__ == "__main__":
    app()

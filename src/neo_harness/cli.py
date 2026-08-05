"""Typer CLI entrypoints: neo start | resume | status | end."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from neo_harness import __version__
from neo_harness.agents.loader import AgentProfile, list_agents, load_agent
from neo_harness.config import get_settings
from neo_harness.harness.budget import Budget
from neo_harness.harness.loop import HarnessLoop
from neo_harness.harness.memory import MemoryBundle
from neo_harness.neo4j import queries
from neo_harness.neo4j.client import Neo4jClient
from neo_harness.neo4j.schema import setup_schema
from neo_harness.profiles import (
    apply_profile_to_budget_kwargs,
    get_profile,
    profile_loop_iterations,
)
from neo_harness.providers import get_provider
from neo_harness.providers.fallback import fallback_mode
from neo_harness.providers.status import probe_all
from neo_harness.schemas.reflection import ReflectionTrigger
from neo_harness.schemas.session import HarnessState, Session, SessionStatus
from neo_harness.security.audit import export_audit
from neo_harness.security.policy import PolicyTier, load_policy, path_allowed
from neo_harness.workspace.init import init_workspace

app = typer.Typer(
    name="neo",
    help="neo-harness — agent harness with explicit state machine + Neo4j memory",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _load_run_policy():
    """Policy for this process from settings + env."""
    settings = get_settings()
    return load_policy(
        tier=settings.policy_tier,
        allow=settings.path_allow or None,
        deny=settings.path_deny or None,
        workspace_root=settings.provider_cwd,
    )

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


def _resolve_agent(agent_opt: str | None) -> AgentProfile | None:
    """CLI flag wins over NEO_AGENT; missing pack is a hard error when set."""
    settings = get_settings()
    agent_id = agent_opt if agent_opt is not None else settings.agent
    try:
        return load_agent(agent_id)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc


def task_summary(task: str, max_chars: int | None = None) -> str:
    """One-line summary for status UI and metadata."""
    if max_chars is None:
        max_chars = get_settings().task_display_chars
    text = task.strip()
    if not text:
        return ""
    # Prefer first markdown H1 / non-empty line
    for line in text.splitlines():
        s = line.strip().lstrip("#").strip()
        if s:
            text = s
            break
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _resolve_task_text(
    task: str | None,
    task_file: Path | None,
) -> str:
    """Resolve task from argument, --task-file, or stdin (`-`)."""
    if task_file is not None:
        path = task_file.expanduser()
        if not path.is_file():
            console.print(f"[red]Task file not found:[/red] {path}")
            raise typer.Exit(code=1)
        return path.read_text(encoding="utf-8")
    if task is None or task == "":
        console.print(
            "[red]Task required.[/red] Pass a string, `--task-file PATH`, or `-` for stdin."
        )
        raise typer.Exit(code=1)
    if task == "-":
        return sys.stdin.read()
    return task


def _print_session(session: Session, *, title: str = "Session") -> None:
    table = Table(title=title, show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="cyan")
    table.add_column("value")
    table.add_row("id", session.id)
    table.add_row("task", task_summary(session.task))
    table.add_row("status", session.status.value)
    table.add_row("state", session.state.value)
    table.add_row("goal", session.goal or "—")
    steps = f"{session.step_count} / {session.action_count} / {session.reflection_count}"
    table.add_row("steps / actions / reflections", steps)
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


@app.command("agents")
def agents_cmd() -> None:
    """List loadable agent packs (personas + phase system prompts)."""
    packs = list_agents()
    if not packs:
        console.print("[yellow]No agent packs found.[/yellow] See agents/README.md")
        raise typer.Exit(0)
    table = Table(title="Agent packs", show_header=True)
    table.add_column("id", style="cyan")
    table.add_column("name")
    table.add_column("description")
    table.add_column("targets")
    for p in packs:
        table.add_row(
            p.id,
            p.name,
            p.description[:80],
            ", ".join(p.target_repos) if p.target_repos else "—",
        )
    console.print(table)
    console.print("[dim]Use: neo start \"…\" --agent <id>   or  NEO_AGENT=<id>[/dim]")


@app.command("start")
def start(
    task: str | None = typer.Argument(
        None,
        help="Task description, or '-' to read stdin. Prefer --task-file for long briefs.",
    ),
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="mock | grok_build | copilot | xai"
    ),
    steps: int | None = typer.Option(
        None, "--steps", "-n", help="Max loop iterations this run (default: settings)"
    ),
    no_run: bool = typer.Option(
        False, "--no-run", help="Create session only; do not enter the loop"
    ),
    agent: str | None = typer.Option(
        None, "--agent", "-a", help="Agent pack id (e.g. sysadmin). Default: NEO_AGENT"
    ),
    task_file: Path | None = typer.Option(
        None,
        "--task-file",
        "-f",
        help="Read task brief from a markdown/text file",
        exists=False,
        dir_okay=False,
        readable=True,
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Run profile: default | cheap | deep (token/loop presets)",
    ),
) -> None:
    """Start a new session: INIT → PLAN → ACT → …"""
    settings = get_settings()
    try:
        run_profile = get_profile(profile)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    task_text = _resolve_task_text(task, task_file)
    summary = task_summary(task_text)
    agent_profile = _resolve_agent(agent)
    client = _client()
    _require_neo4j(client)
    try:
        setup_schema(client)
        session = Session(
            task=task_text,
            status=SessionStatus.ACTIVE,
            state=HarnessState.INIT,
            metadata={
                "task_summary": summary,
                "profile": run_profile.name,
            },
        )
        queries.upsert_session(client, session)
        _save_active(session.id)

        console.print(Panel.fit(f"[bold]Started session[/bold] {session.id}", border_style="green"))
        _print_session(session)
        if agent_profile:
            console.print(
                f"[dim]Agent: {agent_profile.id} ({agent_profile.name}) · "
                f"{agent_profile.root}[/dim]"
            )
        if run_profile.name != "default":
            console.print(
                f"[dim]Profile: {run_profile.name} — {run_profile.description}[/dim]"
            )

        if no_run:
            console.print(
                "[dim]Created without running loop (--no-run). Use `neo resume` later.[/dim]"
            )
            return

        policy = _load_run_policy()
        # REPORT tier forces tools off regardless of NEO_ACT_ALLOW_TOOLS
        if not policy.tools_allowed(settings.act_allow_tools):
            import os

            os.environ["NEO_ACT_ALLOW_TOOLS"] = "0"
        prov = get_provider(provider or settings.provider)
        memory = MemoryBundle.from_client(client, goal=summary or task_text)
        budget = Budget(**apply_profile_to_budget_kwargs(run_profile, settings))
        iters = profile_loop_iterations(run_profile, settings, steps)
        loop = HarnessLoop(
            client=client,
            provider=prov,
            memory=memory,
            budget=budget,
            max_iterations=iters,
            agent=agent_profile,
            policy=policy,
        )
        agent_label = agent_profile.id if agent_profile else "default"
        console.print(
            f"[dim]Provider: {prov.name} · agent: {agent_label} · "
            f"profile: {run_profile.name} · policy: {policy.tier.name.lower()} · "
            f"running loop…[/dim]"
        )
        result = asyncio.run(loop.run(session, steps=iters))

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
    provider: str | None = typer.Option(None, "--provider", "-p"),
    steps: int | None = typer.Option(None, "--steps", "-n"),
    agent: str | None = typer.Option(
        None, "--agent", "-a", help="Agent pack id (e.g. sysadmin). Default: NEO_AGENT"
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Run profile: default | cheap | deep",
    ),
) -> None:
    """Resume an existing session with full Neo4j context."""
    settings = get_settings()
    try:
        run_profile = get_profile(profile)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    agent_profile = _resolve_agent(agent)
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
        policy = _load_run_policy()
        if not policy.tools_allowed(settings.act_allow_tools):
            import os

            os.environ["NEO_ACT_ALLOW_TOOLS"] = "0"
        prov = get_provider(provider or settings.provider)
        memory = MemoryBundle.from_client(client, goal=session.goal or session.task)
        for ep in episodes[-10:]:
            memory.working.push_observation(ep.summary, meta={"kind": ep.kind.value})

        budget = Budget(**apply_profile_to_budget_kwargs(run_profile, settings))
        # Account for prior steps roughly so budgets still apply.
        budget.steps_used = min(session.step_count, max(budget.max_steps - 1, 0))
        iters = profile_loop_iterations(run_profile, settings, steps)

        loop = HarnessLoop(
            client=client,
            provider=prov,
            memory=memory,
            budget=budget,
            max_iterations=iters,
            agent=agent_profile,
            policy=policy,
        )
        agent_label = agent_profile.id if agent_profile else "default"
        console.print(
            f"[dim]Provider: {prov.name} · agent: {agent_label} · "
            f"profile: {run_profile.name} · policy: {policy.tier.name.lower()} · "
            f"{len(episodes)} prior episodes · running…[/dim]"
        )
        result = asyncio.run(loop.run(session, steps=iters))

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
    session_id: str | None = typer.Option(
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
                    task_summary(s.task, 48),
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
    session_id: str | None = typer.Option(
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
        terminal = (HarnessState.DONE, HarnessState.FAILED)
        if session.state not in terminal and session.state != HarnessState.INIT:
            try:
                from neo_harness.harness.memory import Neo4jEpisodicMemory
                from neo_harness.harness.reflection import run_reflection

                prov = get_provider(settings.provider)
                episodic = Neo4jEpisodicMemory(client)
                recent = episodic.list_for_session(session.id, limit=15)
                agent_profile = _resolve_agent(None)
                reflection = asyncio.run(
                    run_reflection(
                        prov,
                        session,
                        plan=None,
                        recent_episodes=recent,
                        trigger=ReflectionTrigger.SESSION_END,
                        agent=agent_profile,
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

        style = "red" if fail else "green"
        console.print(
            Panel.fit(
                f"[bold]Ended[/bold] {session.id} as {status.value}",
                border_style=style,
            )
        )
        _print_session(session)
    finally:
        client.close()


@app.command("policy")
def policy_cmd(
    check_path: Path | None = typer.Option(
        None,
        "--check-path",
        help="Test whether a path is allowed under current policy",
    ),
) -> None:
    """Show active policy tier and path gates (InfoSec control plane)."""
    policy = _load_run_policy()
    table = Table(title="neo-harness policy", show_header=True)
    table.add_column("key")
    table.add_column("value")
    table.add_row("tier", f"{policy.tier.name.lower()} ({int(policy.tier)})")
    table.add_row(
        "tools",
        "allowed if NEO_ACT_ALLOW_TOOLS=1"
        if policy.tier != PolicyTier.REPORT
        else "forced off (report tier)",
    )
    table.add_row(
        "workspace",
        str(policy.workspace_root) if policy.workspace_root else "(unset NEO_PROVIDER_CWD)",
    )
    table.add_row(
        "allow",
        ", ".join(policy.allow_globs) if policy.allow_globs else "(all under workspace)",
    )
    deny_s = ", ".join(policy.deny_globs[:12])
    if len(policy.deny_globs) > 12:
        deny_s += "…"
    table.add_row("deny", deny_s)
    console.print(table)
    if check_path is not None:
        decision = path_allowed(check_path, policy)
        style = "green" if decision.allowed else "red"
        console.print(
            f"[{style}]path {check_path}: "
            f"{'ALLOWED' if decision.allowed else 'DENIED'}[/{style}] — {decision.reason}"
        )


@app.command("audit")
def audit_cmd(
    session_id: str = typer.Argument(..., help="Session id to export"),
    out: Path = typer.Option(
        Path("neo-audit.json"),
        "--out",
        "-o",
        help="Output path (.json or .md)",
    ),
    no_redact: bool = typer.Option(
        False,
        "--no-redact",
        help="Disable secret redaction (not recommended)",
    ),
    fmt: str | None = typer.Option(
        None,
        "--format",
        help="json | md (default: from --out suffix)",
    ),
) -> None:
    """Export a session audit package for operator / InfoSec review."""
    settings = get_settings()
    client = _client()
    _require_neo4j(client)
    try:
        out_fmt = fmt
        if out_fmt is None:
            out_fmt = "md" if str(out).lower().endswith(".md") else "json"
        if out_fmt not in ("json", "md"):
            console.print("[red]format must be json or md[/red]")
            raise typer.Exit(1)
        redact = settings.redact_secrets and not no_redact
        path = export_audit(
            client, session_id, out, redact=redact, fmt=out_fmt
        )
        console.print(
            f"[green]Wrote audit package[/green] {path} "
            f"(redacted={redact})"
        )
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    finally:
        client.close()


@app.command("providers")
def providers_cmd() -> None:
    """Show reasoning provider readiness (binaries / API keys)."""
    table = Table(title="neo-harness providers", show_header=True)
    table.add_column("name", style="cyan")
    table.add_column("ready")
    table.add_column("detail")
    table.add_column("notes")
    for st in probe_all():
        mark = "[green]yes[/green]" if st.available else "[red]no[/red]"
        table.add_row(st.name, mark, st.detail, st.notes)
    console.print(table)
    console.print(
        f"[dim]NEO_PROVIDER_FALLBACK={fallback_mode()} "
        f"(mock = soft fallback; none = fail-closed)[/dim]"
    )
    console.print(
        "[dim]Select with --provider / NEO_PROVIDER=mock|grok_build|copilot|xai[/dim]"
    )


@app.command("init-workspace")
def init_workspace_cmd(
    path: Path = typer.Argument(
        Path("."),
        help="Target workspace root (default: cwd)",
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
    ),
    pack: str = typer.Option(
        "workspace",
        "--pack",
        help="Starter agent pack id under agents/<id>/",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing embed files",
    ),
    no_runner: bool = typer.Option(
        False,
        "--no-runner",
        help="Skip scripts/neo workspace runner",
    ),
    no_pack: bool = typer.Option(
        False,
        "--no-pack",
        help="Skip starter agent pack",
    ),
    force_no_git: bool = typer.Option(
        False,
        "--force-no-git",
        help="Allow init outside a git repository",
    ),
) -> None:
    """Populate a repo with a thin neo-harness embed (not a full project Forge)."""
    target = path if path.exists() else Path.cwd() / path
    if not target.exists():
        target.mkdir(parents=True)
    try:
        result = init_workspace(
            target,
            pack_id=pack,
            force=force,
            with_runner=not no_runner,
            with_pack=not no_pack,
            require_git=not force_no_git,
        )
    except (RuntimeError, NotADirectoryError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(
        Panel.fit(
            f"[bold]init-workspace[/bold] {result.root}",
            border_style="green",
        )
    )
    if result.created:
        console.print("[green]Created/updated:[/green]")
        for item in result.created:
            console.print(f"  + {item}")
    if result.skipped:
        console.print("[dim]Skipped (exists):[/dim]")
        for item in result.skipped:
            console.print(f"  · {item}")
    for msg in result.messages:
        console.print(f"[cyan]→[/cyan] {msg}")


@app.command("version")
def version_cmd() -> None:
    """Print package version."""
    console.print(f"neo-harness {__version__}")


if __name__ == "__main__":
    app()

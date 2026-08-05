"""Discover and load agent packs from repo / env / workspace paths."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Default system prompts when an agent pack omits a phase file.
DEFAULT_PLAN_SYSTEM = """You are a planning engine inside an agent harness.
Produce a short, concrete multi-step plan for the task.
Each step must be actionable and ordered."""

DEFAULT_ACT_SYSTEM = """You are an action engine inside an agent harness.
Given the current plan step and context, describe the action taken and its result.
This is a simulated/placeholder environment unless tools are wired."""

DEFAULT_REFLECT_SYSTEM = """You are a structured reflection engine inside an agent harness.
Given recent session context, produce a honest, concise reflection.
You must choose next_action from: continue, replan, done, fail, block.
Prefer continue when progress is being made; replan when the plan is wrong;
done only when the goal is achieved; fail for unrecoverable errors; block for human input.
"""

# Cap when falling back from full AGENT.md (token diet).
_DEFAULT_PERSONA_MAX = 1200


def _persona_max_chars() -> int:
    raw = os.environ.get("NEO_PERSONA_MAX_CHARS", str(_DEFAULT_PERSONA_MAX))
    try:
        return max(200, int(raw))
    except ValueError:
        return _DEFAULT_PERSONA_MAX


def _use_full_persona() -> bool:
    return os.environ.get("NEO_FULL_PERSONA", "").lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class AgentProfile:
    """A named agent pack: persona + per-phase system prompts."""

    id: str
    name: str
    description: str
    root: Path
    plan_system: str
    act_system: str
    reflect_system: str
    persona: str = ""  # short — injected into model system prompts
    persona_full: str = ""  # full AGENT.md for humans / NEO_FULL_PERSONA
    target_repos: tuple[str, ...] = field(default_factory=tuple)

    def system_for(self, phase: str) -> str:
        """Return the system prompt for plan | act | reflect (token-thrifty)."""
        base = {
            "plan": self.plan_system,
            "act": self.act_system,
            "reflect": self.reflect_system,
        }.get(phase)
        if base is None:
            raise ValueError(f"Unknown phase: {phase}")
        persona = self.persona_full if _use_full_persona() else self.persona
        if not persona.strip():
            persona = self.persona
        if persona.strip():
            return (
                f"{base.rstrip()}\n\n"
                "---\n"
                f"AGENT ({self.name}):\n"
                f"{persona.strip()}\n"
            )
        return base


def _repo_agents_dir() -> Path:
    # src/neo_harness/agents/loader.py → parents[3] = neo-harness repo root
    return Path(__file__).resolve().parents[3] / "agents"


def agent_search_paths() -> list[Path]:
    """
    Ordered search roots for agent packs.

    1. $NEO_PROVIDER_CWD/agents  (workspace embed)
    2. $NEO_AGENTS_DIR
    3. neo-harness repo agents/
    4. ~/.neo-harness/agents
    """
    paths: list[Path] = []
    cwd = os.environ.get("NEO_PROVIDER_CWD")
    if cwd:
        paths.append(Path(cwd).expanduser().resolve() / "agents")
    env = os.environ.get("NEO_AGENTS_DIR")
    if env:
        paths.append(Path(env).expanduser().resolve())
    paths.append(_repo_agents_dir())
    user = Path.home() / ".neo-harness" / "agents"
    if user.is_dir():
        paths.append(user.resolve())
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _clip(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + "\n…[truncated]"


def _load_pack(root: Path) -> AgentProfile:
    agent_id = root.name
    agent_md = root / "AGENT.md"
    persona_full = _read_text(agent_md) if agent_md.is_file() else ""

    short_path = root / "prompts" / "persona.short.md"
    if short_path.is_file():
        persona = _read_text(short_path).strip()
    elif persona_full:
        persona = _clip(persona_full, _persona_max_chars())
    else:
        persona = ""

    name = agent_id.replace("-", " ").replace("_", " ").title()
    description = ""
    targets: list[str] = []

    manifest = root / "manifest.yml"
    if not manifest.is_file():
        manifest = root / "manifest.yaml"
    if manifest.is_file():
        for line in _read_text(manifest).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip().strip("\"'")
            if key == "name" and val:
                name = val
            elif key == "description" and val:
                description = val
            elif key == "id" and val:
                agent_id = val
            elif key == "target_repos" and val:
                targets = [t.strip() for t in val.split(",") if t.strip()]

    prompts = root / "prompts"
    plan = (
        _read_text(prompts / "plan.md")
        if (prompts / "plan.md").is_file()
        else DEFAULT_PLAN_SYSTEM
    )
    act = (
        _read_text(prompts / "act.md")
        if (prompts / "act.md").is_file()
        else DEFAULT_ACT_SYSTEM
    )
    reflect = (
        _read_text(prompts / "reflect.md")
        if (prompts / "reflect.md").is_file()
        else DEFAULT_REFLECT_SYSTEM
    )

    if not description and (persona_full or persona):
        for line in (persona_full or persona).splitlines():
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("<!--"):
                description = s[:160]
                break

    return AgentProfile(
        id=agent_id,
        name=name,
        description=description or f"Agent pack: {agent_id}",
        root=root,
        plan_system=plan,
        act_system=act,
        reflect_system=reflect,
        persona=persona,
        persona_full=persona_full,
        target_repos=tuple(targets),
    )


def list_agents() -> list[AgentProfile]:
    """List all discoverable agent packs (first wins on id collisions)."""
    found: dict[str, AgentProfile] = {}
    for base in agent_search_paths():
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if not (child / "AGENT.md").is_file() and not (child / "prompts").is_dir():
                continue
            if child.name in found:
                continue
            found[child.name] = _load_pack(child)
    return list(found.values())


def load_agent(agent_id: str | None) -> AgentProfile | None:
    """
    Load an agent pack by id.

    Returns None if agent_id is None/empty. Raises FileNotFoundError if id set
    but pack is missing.
    """
    if not agent_id or not str(agent_id).strip():
        return None
    key = str(agent_id).strip().lower()
    for profile in list_agents():
        if profile.id.lower() == key or profile.root.name.lower() == key:
            return profile
    searched = ", ".join(str(p) for p in agent_search_paths())
    raise FileNotFoundError(
        f"Agent pack '{agent_id}' not found. Searched: {searched}. "
        f"Available: {[a.id for a in list_agents()] or '(none)'}"
    )

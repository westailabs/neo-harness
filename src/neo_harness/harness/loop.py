"""Minimal PLAN → ACT → OBSERVE → REFLECT loop owned by the harness."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from neo_harness.agents.loader import (
    DEFAULT_ACT_SYSTEM,
    DEFAULT_PLAN_SYSTEM,
    AgentProfile,
)
from neo_harness.config import get_settings
from neo_harness.harness.budget import Budget, BudgetExceededError
from neo_harness.harness.memory import MemoryBundle
from neo_harness.harness.reflection import next_state_for_reflection, run_reflection
from neo_harness.harness.state_machine import IllegalTransitionError, StateMachine
from neo_harness.neo4j import queries
from neo_harness.neo4j.client import Neo4jClient
from neo_harness.providers.base import ReasoningProvider
from neo_harness.schemas.episode import Episode, EpisodeKind
from neo_harness.schemas.plan import Plan, StepStatus
from neo_harness.schemas.reflection import ReflectionTrigger
from neo_harness.schemas.session import HarnessState, Session, SessionStatus

logger = logging.getLogger(__name__)

# Back-compat aliases (tests / importers)
PLAN_SYSTEM = DEFAULT_PLAN_SYSTEM
ACT_SYSTEM = DEFAULT_ACT_SYSTEM


def _clip(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 16)].rstrip() + "\n…[truncated]"


@dataclass
class LoopResult:
    session: Session
    plan: Plan | None = None
    final_state: HarnessState = HarnessState.INIT
    reflections: int = 0
    error: str | None = None
    history: list[str] = field(default_factory=list)


class HarnessLoop:
    """
    Owns control flow for one session turn (or full run until terminal/budget).

    The model is only invoked inside the current state via ReasoningProvider.
    """

    def __init__(
        self,
        client: Neo4jClient,
        provider: ReasoningProvider,
        memory: MemoryBundle,
        budget: Budget | None = None,
        *,
        max_iterations: int = 20,
        agent: AgentProfile | None = None,
    ) -> None:
        self.client = client
        self.provider = provider
        self.memory = memory
        self.budget = budget or Budget()
        self.max_iterations = max_iterations
        self.agent = agent
        self.machine = StateMachine()
        self.plan: Plan | None = None

    def _system(self, phase: str) -> str:
        if self.agent is not None:
            return self.agent.system_for(phase)
        if phase == "plan":
            return DEFAULT_PLAN_SYSTEM
        if phase == "act":
            return DEFAULT_ACT_SYSTEM
        raise ValueError(f"Unknown phase for default system prompt: {phase}")

    def _task_brief(self, session: Session) -> str:
        """Prefer short summary from metadata; else clip full task."""
        meta = session.metadata or {}
        summary = meta.get("task_summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
        s = get_settings()
        return _clip(session.task, min(500, s.prompt_max_chars_plan // 2))

    def _skip_interval_reflect(self) -> bool:
        """Token diet: skip interval REFLECT on short plans still progressing."""
        if self.plan is None:
            return False
        s = get_settings()
        max_steps = s.skip_interval_reflect_max_steps
        if max_steps <= 0 or len(self.plan.steps) > max_steps:
            return False
        if any(st.status == StepStatus.FAILED for st in self.plan.steps):
            return False
        # Still have work — defer reflect until plan complete / error
        return self.plan.next_pending_step() is not None

    def _persist_session(self, session: Session) -> None:
        session.state = self.machine.state
        session.touch()
        queries.upsert_session(self.client, session)

    def _episode(
        self,
        session: Session,
        kind: EpisodeKind,
        summary: str,
        content: dict[str, Any] | None = None,
        *,
        success: bool = True,
    ) -> Episode:
        ep = Episode(
            session_id=session.id,
            kind=kind,
            state=self.machine.state.value,
            summary=summary,
            content=content or {},
            step_index=session.step_count,
            success=success,
        )
        self.memory.episodic.append(ep)
        return ep

    async def run(self, session: Session, *, steps: int | None = None) -> LoopResult:
        """Run the harness loop until terminal, budget, or `steps` iterations."""
        self.machine.reset(session.state)
        self.memory.hydrate_working_from_session(session)
        limit = steps if steps is not None else self.max_iterations
        result = LoopResult(session=session)
        log = result.history

        try:
            if self.machine.state == HarnessState.INIT:
                self.machine.transition(HarnessState.PLAN, reason="session start")
                self._persist_session(session)
                log.append("INIT → PLAN")

            for _ in range(limit):
                if self.machine.is_terminal():
                    break

                try:
                    self.budget.record_step()
                except BudgetExceededError as exc:
                    session.last_error = str(exc)
                    if self.machine.can_transition(HarnessState.FAILED):
                        self.machine.transition(HarnessState.FAILED, reason=str(exc))
                    session.status = SessionStatus.FAILED
                    self._persist_session(session)
                    result.error = str(exc)
                    log.append(f"budget exceeded: {exc}")
                    break

                session.step_count += 1
                state = self.machine.state

                if state == HarnessState.PLAN:
                    await self._do_plan(session, log)
                elif state == HarnessState.ACT:
                    await self._do_act(session, log)
                elif state == HarnessState.OBSERVE:
                    await self._do_observe(session, log)
                elif state == HarnessState.REFLECT:
                    await self._do_reflect(session, log, ReflectionTrigger.INTERVAL)
                    result.reflections += 1
                elif state == HarnessState.BLOCKED:
                    log.append("BLOCKED — waiting for external input; stopping turn")
                    session.status = SessionStatus.BLOCKED
                    self._persist_session(session)
                    break
                else:
                    log.append(f"unexpected state {state}; stopping")
                    break

                self._persist_session(session)

        except IllegalTransitionError as exc:
            logger.exception("illegal transition")
            session.last_error = str(exc)
            result.error = str(exc)
            self._persist_session(session)
        except Exception as exc:  # noqa: BLE001
            logger.exception("loop error")
            session.last_error = str(exc)
            result.error = str(exc)
            try:
                if self.machine.can_transition(HarnessState.REFLECT):
                    self.machine.transition(HarnessState.REFLECT, reason="error")
                    await self._do_reflect(
                        session, log, ReflectionTrigger.ERROR, error=str(exc)
                    )
                    result.reflections += 1
                elif self.machine.can_transition(HarnessState.FAILED):
                    self.machine.transition(HarnessState.FAILED, reason=str(exc))
                    session.status = SessionStatus.FAILED
            except IllegalTransitionError:
                pass
            self._persist_session(session)

        result.plan = self.plan
        result.final_state = self.machine.state
        session.state = self.machine.state
        self._persist_session(session)
        return result

    async def _do_plan(self, session: Session, log: list[str]) -> None:
        s = get_settings()
        obs = self.memory.working.recent_observations(s.observation_tail)
        prompt = _clip(
            f"Task: {self._task_brief(session)}\n"
            f"Goal: {self.memory.working.get_goal() or self._task_brief(session)}\n"
            f"Recent observations: {obs}\n"
            "Produce an ordered plan with 2–6 concrete steps.",
            s.prompt_max_chars_plan,
        )
        plan = await self.provider.plan(
            system=self._system("plan"),
            prompt=prompt,
            session_id=session.id,
        )
        plan.session_id = session.id
        if not plan.goal:
            plan.goal = session.goal or session.task
        session.goal = plan.goal
        self.memory.working.set_goal(plan.goal)
        self.plan = plan
        self._episode(
            session,
            EpisodeKind.PLAN,
            f"Plan v{plan.version}: {len(plan.steps)} steps — {plan.goal}",
            plan.model_dump(mode="json"),
        )
        log.append(f"PLAN: {len(plan.steps)} steps for «{plan.goal}»")

        if plan.is_complete or not plan.steps:
            self.machine.transition(HarnessState.REFLECT, reason="empty or complete plan")
            log.append("PLAN → REFLECT")
        else:
            self.machine.transition(HarnessState.ACT, reason="plan ready")
            log.append("PLAN → ACT")

    async def _do_act(self, session: Session, log: list[str]) -> None:
        if self.plan is None:
            # ACT → PLAN is illegal; force REFLECT so the next cycle can replan.
            self.machine.transition(HarnessState.REFLECT, reason="no plan")
            log.append("ACT → REFLECT (no plan)")
            return

        step = self.plan.next_pending_step()
        if step is None:
            self.machine.transition(HarnessState.REFLECT, reason="no pending steps")
            log.append("ACT → REFLECT (plan exhausted)")
            return

        step.status = StepStatus.IN_PROGRESS
        s = get_settings()
        # Prefer last N observations over full working-memory blob
        obs = self.memory.working.recent_observations(s.observation_tail)
        prompt = _clip(
            f"Goal: {self.plan.goal}\n"
            f"Current step [{step.index}]: {step.description}\n"
            f"Recent observations: {obs}\n"
            "Execute this step (describe action and outcome).",
            s.prompt_max_chars_act,
        )
        action_result = await self.provider.act(
            system=self._system("act"),
            prompt=prompt,
            session_id=session.id,
            step=step,
        )
        session.action_count += 1
        self.budget.record_action()
        step.status = StepStatus.DONE if action_result.get("success", True) else StepStatus.FAILED

        summary = action_result.get("summary") or f"Executed: {step.description}"
        self._episode(
            session,
            EpisodeKind.ACTION,
            summary,
            {"step": step.model_dump(mode="json"), "result": action_result},
            success=bool(action_result.get("success", True)),
        )
        self.memory.working.push_observation(summary, meta={"step_id": step.id})
        log.append(f"ACT: {summary}")

        if not action_result.get("success", True):
            self.machine.transition(HarnessState.REFLECT, reason="action failed")
            log.append("ACT → REFLECT (action failed)")
            return

        self.machine.transition(HarnessState.OBSERVE, reason="action complete")
        log.append("ACT → OBSERVE")

    async def _do_observe(self, session: Session, log: list[str]) -> None:
        obs = self.memory.working.recent_observations(1)
        text = obs[-1]["text"] if obs else "No new observations."
        self._episode(session, EpisodeKind.OBSERVATION, text, {"raw": obs})
        log.append(f"OBSERVE: {text[:120]}")

        if self.budget.should_reflect():
            if self._skip_interval_reflect():
                log.append("OBSERVE: skip interval REFLECT (short plan, still progressing)")
            else:
                self.machine.transition(HarnessState.REFLECT, reason="reflection interval")
                log.append("OBSERVE → REFLECT (interval)")
                return

        if self.plan and self.plan.is_complete:
            self.machine.transition(HarnessState.REFLECT, reason="plan complete")
            log.append("OBSERVE → REFLECT (plan complete)")
            return

        if self.plan and self.plan.next_pending_step() is not None:
            self.machine.transition(HarnessState.ACT, reason="more steps")
            log.append("OBSERVE → ACT")
        else:
            self.machine.transition(HarnessState.REFLECT, reason="nothing pending")
            log.append("OBSERVE → REFLECT")

    async def _do_reflect(
        self,
        session: Session,
        log: list[str],
        trigger: ReflectionTrigger,
        error: str | None = None,
    ) -> None:
        if trigger == ReflectionTrigger.INTERVAL and self.plan and self.plan.is_complete:
            trigger = ReflectionTrigger.PLAN_COMPLETE

        s = get_settings()
        recent = self.memory.episodic.list_for_session(session.id, limit=s.episode_tail)
        reflection = await run_reflection(
            self.provider,
            session,
            self.plan,
            recent,
            trigger,
            error=error,
            agent=self.agent,
            max_prompt_chars=s.prompt_max_chars_reflect,
        )
        self.memory.episodic.store_reflection(reflection)
        session.reflection_count += 1
        self.budget.reset_reflection_counter()

        for decision_text in reflection.decisions:
            from neo_harness.schemas.episode import Decision

            self.memory.semantic.add_decision(
                Decision(
                    session_id=session.id,
                    statement=decision_text,
                    rationale=reflection.what_happened,
                )
            )

        log.append(
            f"REFLECT ({trigger.value}): next={reflection.next_action.value} "
            f"conf={reflection.confidence:.2f}"
        )

        target_name = next_state_for_reflection(reflection)
        target = HarnessState(target_name)

        # Harness-side guard: don't continue acting on a finished plan.
        if target == HarnessState.ACT and self.plan is not None and self.plan.is_complete:
            target = HarnessState.DONE
            log.append("harness override: plan complete → DONE")

        if not self.machine.can_transition(target):
            # Safety: if mapping is illegal, prefer DONE then FAILED if allowed.
            if self.machine.can_transition(HarnessState.DONE):
                target = HarnessState.DONE
            elif self.machine.can_transition(HarnessState.FAILED):
                target = HarnessState.FAILED
            else:
                log.append(f"cannot transition to {target_name}; stopping")
                return

        self.machine.transition(target, reason=f"reflection:{reflection.next_action.value}")
        log.append(f"REFLECT → {target.value}")

        if target == HarnessState.DONE:
            session.status = SessionStatus.COMPLETED
            session.mark_ended(SessionStatus.COMPLETED)
        elif target == HarnessState.FAILED:
            session.status = SessionStatus.FAILED
            session.mark_ended(SessionStatus.FAILED)
        elif target == HarnessState.BLOCKED:
            session.status = SessionStatus.BLOCKED

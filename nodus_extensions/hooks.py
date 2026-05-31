"""HookRunner — execute phase hooks registered by extensions."""
from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Standard phase names — extensions register against these
PHASE_INIT              = "init"
PHASE_BEFORE_AGENT_START = "before_agent_start"
PHASE_BEFORE_MODEL_RESOLVE = "before_model_resolve"
PHASE_AFTER_AGENT_END   = "after_agent_end"
PHASE_SHUTDOWN          = "shutdown"

ALL_PHASES: frozenset[str] = frozenset({
    PHASE_INIT, PHASE_BEFORE_AGENT_START, PHASE_BEFORE_MODEL_RESOLVE,
    PHASE_AFTER_AGENT_END, PHASE_SHUTDOWN,
})

HookFn = Callable[[dict[str, Any]], Any]


@dataclass
class HookRegistration:
    phase: str
    fn: HookFn
    extension_id: str
    priority: int = 0      # lower = runs first


class HookRunner:
    """Execute phase hooks registered by extensions.

    Hooks are called in priority order (ascending).  The first hook that
    returns a non-None result wins (first-match semantics) for phases that
    expect an override (e.g. ``before_model_resolve``).  For notification
    phases (``init``, ``shutdown``) all hooks are called regardless.

    Thread-safe registration; async execution.
    """

    _FIRST_MATCH_PHASES: frozenset[str] = frozenset({
        PHASE_BEFORE_MODEL_RESOLVE,
    })

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookRegistration]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        phase: str,
        fn: HookFn,
        *,
        extension_id: str,
        priority: int = 0,
    ) -> None:
        """Register *fn* for *phase*."""
        with self._lock:
            if phase not in self._hooks:
                self._hooks[phase] = []
            reg = HookRegistration(phase=phase, fn=fn, extension_id=extension_id, priority=priority)
            self._hooks[phase].append(reg)
            self._hooks[phase].sort(key=lambda r: r.priority)

    def unregister(self, extension_id: str) -> int:
        """Remove all hooks registered by *extension_id*. Returns count removed."""
        removed = 0
        with self._lock:
            for phase in self._hooks:
                before = len(self._hooks[phase])
                self._hooks[phase] = [r for r in self._hooks[phase] if r.extension_id != extension_id]
                removed += before - len(self._hooks[phase])
        return removed

    async def run(
        self,
        phase: str,
        params: dict[str, Any],
    ) -> list[Any]:
        """Execute all hooks for *phase*.

        For first-match phases, stops after the first non-None result.
        Returns a list of all non-None results from all hooks.
        """
        with self._lock:
            registrations = list(self._hooks.get(phase, []))

        results: list[Any] = []
        first_match = phase in self._FIRST_MATCH_PHASES

        for reg in registrations:
            try:
                result = reg.fn(params)
                if asyncio.iscoroutine(result):
                    result = await result
                if result is not None:
                    results.append(result)
                    if first_match:
                        break
            except Exception as exc:
                logger.warning(
                    "[HookRunner] hook %s/%s failed: %s",
                    reg.extension_id, phase, exc,
                )

        return results

    def registered_phases(self) -> list[str]:
        with self._lock:
            return [p for p, hooks in self._hooks.items() if hooks]

    def hook_count(self, phase: Optional[str] = None) -> int:
        with self._lock:
            if phase is not None:
                return len(self._hooks.get(phase, []))
            return sum(len(h) for h in self._hooks.values())

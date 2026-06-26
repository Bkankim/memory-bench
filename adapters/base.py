"""Memory backend abstraction for a same-conditions comparison.

Each backend implements provision/retain/recall over a named scope (a "bank"/user),
and declares capabilities on the axes that actually decide which OSS fits a situation:
offline operation, whether an extraction LLM is mandatory, native isolation enforcement,
and audit logging. The harness times every op and scores recall against expected text.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class Capabilities:
    name: str
    offline: bool                 # can run with zero external cloud calls
    llm_required: bool            # is an extraction LLM mandatory for retain?
    native_isolation: bool        # does the system itself enforce per-scope isolation?
    audit_log: bool               # built-in access audit trail?
    notes: str = ""


@dataclass
class OpResult:
    ok: bool
    latency_ms: float
    raw: Any = None
    error: Optional[str] = None


@dataclass
class RecallResult:
    ok: bool
    latency_ms: float
    texts: List[str] = field(default_factory=list)
    raw: Any = None
    error: Optional[str] = None

    def contains(self, needle: str) -> bool:
        n = needle.lower()
        return any(n in (t or "").lower() for t in self.texts)


class MemoryBackend(Protocol):
    def capabilities(self) -> Capabilities: ...
    def provision(self, scope: str) -> OpResult: ...
    def retain(self, scope: str, content: str, metadata: Optional[Dict] = None, *, actor: Optional[str] = None) -> OpResult: ...
    def recall(self, scope: str, query: str, *, actor: Optional[str] = None) -> RecallResult: ...


def timed(fn):
    """Wrap a call, returning (value, elapsed_ms)."""
    t0 = time.perf_counter()
    val = fn()
    return val, (time.perf_counter() - t0) * 1000.0

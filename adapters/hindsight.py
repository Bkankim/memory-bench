"""Hindsight backend — via the Hindsight-Crew gateway (the isolation-enforcing front door).

Talks the REST surface the gateway proxies: /v1/{tenant}/banks/{bank}/memories(/recall).
Scope = bank; actor token selects the principal (the gateway enforces ACL). Offline
(LLM=none) per the Hindsight-Crew cpu-en profile.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

import httpx

from .base import Capabilities, MemoryBackend, OpResult, RecallResult, timed


class HindsightBackend:
    def __init__(self, base_url: Optional[str] = None, tenant: str = "default",
                 token_map: Optional[Dict[str, str]] = None, default_token: Optional[str] = None):
        self.base = (base_url or os.environ.get("HC_GW", "http://127.0.0.1:8888")).rstrip("/")
        self.tenant = tenant
        # token_map: actor identity -> member token (gateway ACL). default_token for provisioning.
        self.token_map = token_map or {}
        self.default_token = default_token or os.environ.get("HC_DEMO_TOKEN_ALICE", "")
        self.http = httpx.Client(timeout=30.0)

    def capabilities(self) -> Capabilities:
        return Capabilities(
            name="hindsight", offline=True, llm_required=False,
            native_isolation=False, audit_log=True,
            notes="No identity->bank enforcement in Hindsight itself; isolation enforced by the "
                  "Hindsight-Crew gateway (deny-by-default ACL + audit). Runs offline with LLM_PROVIDER=none.",
        )

    def _tok(self, actor: Optional[str]) -> str:
        return self.token_map.get(actor or "", self.default_token)

    def _path(self, scope: str, suffix: str = "") -> str:
        return f"{self.base}/v1/{self.tenant}/banks/{scope}{suffix}"

    def provision(self, scope: str) -> OpResult:
        def _do():
            return self.http.put(self._path(scope), json={"name": scope},
                                 headers={"authorization": f"Bearer {self.default_token}"})
        try:
            r, ms = timed(_do)
            return OpResult(ok=r.status_code in (200, 201), latency_ms=ms, raw=r.status_code,
                            error=None if r.status_code in (200, 201) else f"HTTP {r.status_code}")
        except Exception as e:
            return OpResult(ok=False, latency_ms=0.0, error=str(e))

    def retain(self, scope: str, content: str, metadata: Optional[Dict] = None, *, actor: Optional[str] = None) -> OpResult:
        item = {"content": content}
        if metadata:
            item["metadata"] = metadata
        def _do():
            return self.http.post(self._path(scope, "/memories"), json={"items": [item]},
                                  headers={"authorization": f"Bearer {self._tok(actor)}"})
        try:
            r, ms = timed(_do)
            return OpResult(ok=r.status_code == 200, latency_ms=ms, raw=r.status_code,
                            error=None if r.status_code == 200 else f"HTTP {r.status_code}: {r.text[:120]}")
        except Exception as e:
            return OpResult(ok=False, latency_ms=0.0, error=str(e))

    def recall(self, scope: str, query: str, *, actor: Optional[str] = None) -> RecallResult:
        def _do():
            return self.http.post(self._path(scope, "/memories/recall"), json={"query": query},
                                  headers={"authorization": f"Bearer {self._tok(actor)}"})
        try:
            r, ms = timed(_do)
            if r.status_code != 200:
                return RecallResult(ok=False, latency_ms=ms, raw=r.status_code, error=f"HTTP {r.status_code}")
            data = r.json()
            texts = [m.get("text", "") for m in (data.get("results") or [])]
            return RecallResult(ok=True, latency_ms=ms, texts=texts, raw=data)
        except Exception as e:
            return RecallResult(ok=False, latency_ms=0.0, error=str(e))

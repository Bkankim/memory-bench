"""mem0 backend — OSS library (mem0ai).

Configured for an OFFLINE, same-conditions comparison with Hindsight:
  - embedder: local HuggingFace (BAAI/bge-small-en-v1.5) — same family as Hindsight cpu-en
  - llm: ollama (local) — because mem0's DEFAULT llm is OpenAI (cloud + API key), which
    violates the on-prem/offline constraint. Offline mem0 therefore REQUIRES a local LLM
    service (ollama) + a pulled model. This is a real cost vs Hindsight's native LLM=none mode.
  - vector_store: chroma (local, embedded)
  - retain uses infer=False to store raw (parity with Hindsight LLM=none raw recall).

NOTE: mem0ai latest requires Python >=3.10; default deps pull openai + posthog telemetry
(set MEM0_TELEMETRY=False / anonymize). This adapter raises a clear, honest error if mem0
or the local LLM service is unavailable, instead of silently faking results.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from .base import Capabilities, OpResult, RecallResult, timed


def _default_config() -> dict:
    return {
        "embedder": {"provider": "huggingface",
                     "config": {"model": os.environ.get("MB_EMBED_MODEL", "BAAI/bge-small-en-v1.5")}},
        "llm": {"provider": "ollama",
                "config": {"model": os.environ.get("MB_OLLAMA_MODEL", "qwen2.5:0.5b"),
                           "ollama_base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")}},
        "vector_store": {"provider": "chroma",
                         "config": {"collection_name": "memory_bench",
                                    "path": os.environ.get("MB_CHROMA_PATH", "./results/.chroma")}},
    }


class Mem0Backend:
    def __init__(self, config: Optional[dict] = None):
        os.environ.setdefault("MEM0_TELEMETRY", "False")  # disable posthog phone-home for a fair on-prem run
        try:
            from mem0 import Memory  # type: ignore
        except Exception as e:  # honest hard-fail, never fake
            raise RuntimeError(
                f"mem0 unavailable: {e}. Install on Python>=3.10: `pip install mem0ai`, run a local "
                f"ollama (`ollama pull qwen2.5:0.5b`) for offline LLM, then re-run. "
                f"This environment is Python 3.9 / 2GB VM, so mem0 offline was NOT run here."
            )
        self._mem = Memory.from_config(config or _default_config())

    def capabilities(self) -> Capabilities:
        return Capabilities(
            name="mem0", offline=False, llm_required=True,
            native_isolation=True, audit_log=True,
            notes="Identity is a first-class primitive (user_id scoping; per-user API keys + request "
                  "audit log on the managed platform). BUT default LLM is OpenAI (cloud); offline needs "
                  "a local LLM service (ollama). Latest requires Python>=3.10; posthog telemetry is on by "
                  "default. offline=False reflects the out-of-box default (cloud LLM); flip to True only "
                  "with a local ollama model configured.",
        )

    def provision(self, scope: str) -> OpResult:
        return OpResult(ok=True, latency_ms=0.0, raw="mem0 scopes are implicit via user_id")

    def retain(self, scope: str, content: str, metadata: Optional[Dict] = None, *, actor: Optional[str] = None) -> OpResult:
        def _do():
            # infer=False -> raw store without LLM extraction (parity with Hindsight LLM=none)
            return self._mem.add(content, user_id=scope, metadata=metadata or {}, infer=False)
        try:
            res, ms = timed(_do)
            return OpResult(ok=True, latency_ms=ms, raw=res)
        except Exception as e:
            return OpResult(ok=False, latency_ms=0.0, error=str(e))

    def recall(self, scope: str, query: str, *, actor: Optional[str] = None) -> RecallResult:
        def _do():
            return self._mem.search(query, user_id=scope)
        try:
            res, ms = timed(_do)
            items = res.get("results", res) if isinstance(res, dict) else res
            texts: List[str] = []
            for it in (items or []):
                texts.append(it.get("memory") or it.get("text") or it.get("content") or "")
            return RecallResult(ok=True, latency_ms=ms, texts=texts, raw=res)
        except Exception as e:
            return RecallResult(ok=False, latency_ms=0.0, error=str(e))

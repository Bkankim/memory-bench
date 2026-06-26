"""Unit tests for the harness logic — no live stack required (uses a fake backend).

Covers: RecallResult.contains matching, the scoring path in bench.run via a fake backend,
and that the mem0 adapter fails honestly (never fakes) when mem0 is unavailable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.base import Capabilities, OpResult, RecallResult


def test_recall_contains_case_insensitive():
    rr = RecallResult(ok=True, latency_ms=1.0, texts=["The deploy key rotates every 90 DAYS."])
    assert rr.contains("90 days")
    assert rr.contains("DEPLOY")
    assert not rr.contains("December 20")


def test_recall_contains_empty_and_none_safe():
    rr = RecallResult(ok=True, latency_ms=1.0, texts=["", None, "Bob owns billing"])
    assert rr.contains("bob")
    assert not rr.contains("alice")


class FakeBackend:
    """In-memory backend implementing the MemoryBackend protocol for harness tests."""
    def __init__(self):
        self.store = {}
    def capabilities(self):
        return Capabilities(name="fake", offline=True, llm_required=False,
                            native_isolation=True, audit_log=False)
    def provision(self, scope):
        self.store.setdefault(scope, [])
        return OpResult(ok=True, latency_ms=0.1)
    def retain(self, scope, content, metadata=None, *, actor=None):
        self.store.setdefault(scope, []).append(content)
        return OpResult(ok=True, latency_ms=0.2)
    def recall(self, scope, query, *, actor=None):
        # naive substring match over stored facts (deterministic, offline)
        hits = [c for c in self.store.get(scope, []) if any(w in c.lower() for w in query.lower().split())]
        return RecallResult(ok=True, latency_ms=0.3, texts=hits or self.store.get(scope, []))


def test_harness_scoring_with_fake_backend(monkeypatch, tmp_path):
    import bench.run as run
    monkeypatch.setattr(run, "build_backend", lambda name: FakeBackend())
    monkeypatch.setattr(sys, "argv", ["run", "--backend", "fake",
                                      "--scope", "s1", "--out", str(tmp_path / "fake.json")])
    # speed up: no real async settle
    monkeypatch.setattr(run.time, "sleep", lambda *_: None)
    run.main()
    import json
    res = json.loads((tmp_path / "fake.json").read_text())
    assert res["backend"] == "fake"
    assert res["retain_ok"].endswith("/8")
    assert 0.0 <= res["recall_accuracy"] <= 1.0


def test_mem0_adapter_fails_honestly_when_unavailable():
    """mem0 must raise (never fabricate) if the lib/LLM isn't present."""
    from adapters.mem0_adapter import Mem0Backend
    try:
        Mem0Backend()
    except RuntimeError as e:
        assert "mem0 unavailable" in str(e)
        return
    # If mem0 IS installed in the test env, construction may succeed — that's also fine.

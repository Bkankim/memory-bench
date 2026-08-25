"""Unit tests for the harness logic — no live stack required (uses a fake backend).

Covers: RecallResult.contains matching, the scoring path in bench.run via a fake backend,
and that the mem0 adapter fails honestly (never fakes) when mem0 is unavailable.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.base import Capabilities, OpResult, RecallResult


def test_recall_contains_case_insensitive():
    rr = RecallResult(ok=True, latency_ms=1.0, texts=["The deploy key rotates every 90 DAYS."])
    assert rr.contains("90 days")
    assert rr.contains("DEPLOY")
    assert not rr.contains("December 20")


def test_recall_contains_empty_and_none_safe():
    rr = RecallResult(ok=True, latency_ms=1.0, texts=json.loads('["", null, "Bob owns billing"]'))
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
    res = json.loads((tmp_path / "fake.json").read_text())
    assert res["backend"] == "fake"
    assert res["status"] == "measured"
    datetime.fromisoformat(res["run_at"])
    assert res["run_env"]["python"]
    assert res["run_env"]["host"]
    assert isinstance(res["run_env"]["ollama_installed"], bool)
    assert res["retain_ok"].endswith("/8")
    assert 0.0 <= res["recall_accuracy"] <= 1.0


def test_harness_records_current_environment_when_backend_unavailable(monkeypatch, tmp_path):
    import bench.run as run
    out = tmp_path / "failed.json"
    monkeypatch.setattr(run, "build_backend", lambda name: (_ for _ in ()).throw(RuntimeError("offline backend unavailable")))
    monkeypatch.setattr(sys, "argv", ["run", "--backend", "mem0", "--out", str(out)])

    run.main()

    res = json.loads(out.read_text())
    assert res["backend"] == "mem0"
    assert res["status"] == "failed"
    assert res["recall_accuracy"] is None
    assert res["reason"] == "offline backend unavailable"
    datetime.fromisoformat(res["run_at"])
    assert res["run_env"]["python"]
    assert res["run_env"]["host"]
    assert isinstance(res["run_env"]["ollama_installed"], bool)


def test_hindsight_retain_satisfies_required_bank_policy(monkeypatch):
    from adapters.hindsight import HindsightBackend
    captured = {}
    backend = HindsightBackend(base_url="http://gateway", token_map={"alice": "token"})

    def post(url, *, json, headers):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return SimpleNamespace(status_code=200, text="")

    monkeypatch.setattr(backend.http, "post", post)

    result = backend.retain("personal-alice", "The deploy key rotates every 90 days.", actor="alice")

    assert result.ok
    item = captured["json"]["items"][0]
    assert item["content"] == "[benchmark] The deploy key rotates every 90 days."
    assert item["tags"] == ["project:memory-bench", "kind:benchmark"]


def test_report_uses_live_mem0_measurements(monkeypatch, tmp_path):
    from bench import report
    results = tmp_path / "results"
    results.mkdir()
    capabilities = {
        "offline": True,
        "llm_required": False,
        "audit_log": True,
    }
    (results / "hindsight.json").write_text(json.dumps({
        "status": "measured",
        "recall_accuracy": 1.0,
        "recall_hits": "8/8",
        "retain_latency_ms": {"p50": 1.0, "p95": 2.0},
        "recall_latency_ms": {"p50": 5.0, "p95": 6.0},
        "run_env": {
            "python": "3.13.14",
            "host": "macOS-test",
            "ollama_installed": True,
            "ollama_model": "qwen2.5:0.5b",
        },
        "capabilities": capabilities,
    }))
    (results / "mem0.json").write_text(json.dumps({
        "status": "measured",
        "recall_accuracy": 0.875,
        "recall_hits": "7/8",
        "retain_latency_ms": {"p50": 3.0, "p95": 4.0},
        "recall_latency_ms": {"p50": 7.0, "p95": 8.0},
        "run_env": {
            "python": "3.13.14",
            "host": "macOS-test",
            "ollama_installed": True,
            "ollama_model": "qwen2.5:0.5b",
        },
        "capabilities": capabilities,
    }))
    monkeypatch.setattr(report, "ROOT", tmp_path)

    report.main()

    comparison = (tmp_path / "COMPARISON.md").read_text()
    assert "| recall accuracy (eval-mini, 8 q) | 8/8 (MEASURED) | 7/8 (MEASURED) |" in comparison
    assert "| retain latency p50/p95 ms | 1.0/2.0 (MEASURED) | 3.0/4.0 (MEASURED) |" in comparison
    assert "| recall latency p50/p95 ms | 5.0/6.0 (MEASURED) | 7.0/8.0 (MEASURED) |" in comparison
    assert "| benchmark interpreter | Python 3.13.14 | Python 3.13.14 |" in comparison
    assert "| benchmark LLM configuration | LLM=none | Ollama qwen2.5:0.5b (0.5B, required provider) |" in comparison


def test_mem0_recall_uses_v2_entity_filters():
    from adapters.mem0_adapter import Mem0Backend
    captured = {}

    class FakeMemory:
        def search(self, query, **kwargs):
            captured["query"] = query
            captured["kwargs"] = kwargs
            return {"results": [{"memory": "The deploy key rotates every 90 days."}]}

    backend = Mem0Backend.__new__(Mem0Backend)
    setattr(backend, "_mem", FakeMemory())

    result = backend.recall("alice", "deploy key")

    assert result.ok
    assert result.contains("90 days")
    assert captured["kwargs"] == {"filters": {"user_id": "alice"}}


def test_mem0_adapter_reports_offline_for_local_ollama_config():
    from adapters.mem0_adapter import Mem0Backend
    backend = Mem0Backend.__new__(Mem0Backend)

    capabilities = backend.capabilities()

    assert capabilities.offline is True
    assert capabilities.llm_required is True


def test_mem0_adapter_fails_honestly_when_unavailable(monkeypatch):
    """mem0 must raise (never fabricate) if the library is unavailable."""
    from adapters.mem0_adapter import Mem0Backend
    monkeypatch.setitem(sys.modules, "mem0", None)

    try:
        Mem0Backend()
    except RuntimeError as error:
        assert "mem0 unavailable" in str(error)
        return
    raise AssertionError("Mem0Backend must fail when the mem0 module is unavailable")

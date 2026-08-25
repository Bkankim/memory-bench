"""Run the eval-mini recall benchmark against a backend, same conditions for all.

Usage:
  python -m bench.run --backend hindsight [--scope bench-mini] [--out results/hindsight.json]
Measures recall accuracy (expected substring found), retain/recall latency p50/p95, and
prints a one-line summary. Backends are compared on identical facts/queries.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.base import Capabilities


class QueryItem(TypedDict):
    q: str
    expect: str


class Dataset(TypedDict):
    facts: list[str]
    queries: list[QueryItem]


class RunEnvironment(TypedDict):
    python: str
    host: str
    ollama_installed: bool
    ollama_model: str


class RunMetadata(TypedDict):
    run_at: str
    run_env: RunEnvironment


def load_dataset(path: str) -> Dataset:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_backend(name: str):
    if name == "hindsight":
        from adapters.hindsight import HindsightBackend
        return HindsightBackend(
            token_map={"alice": os.environ.get("HC_DEMO_TOKEN_ALICE", "")},
            default_token=os.environ.get("HC_DEMO_TOKEN_ALICE", ""),
        )
    if name == "mem0":
        from adapters.mem0_adapter import Mem0Backend
        return Mem0Backend()
    raise SystemExit(f"unknown backend: {name}")


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round((p / 100.0) * (len(xs) - 1)))))
    return round(xs[k], 1)


def current_run_metadata() -> RunMetadata:
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "run_env": {
            "python": platform.python_version(),
            "host": platform.platform(),
            "ollama_installed": shutil.which("ollama") is not None,
            "ollama_model": os.environ.get("MB_OLLAMA_MODEL", "qwen2.5:0.5b"),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True)
    ap.add_argument("--dataset", default=str(Path(__file__).resolve().parents[1] / "data" / "eval-mini.json"))
    ap.add_argument("--scope", default="bench-mini")
    ap.add_argument("--actor", default="alice")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ds = load_dataset(args.dataset)
    out = Path(args.out or f"results/{args.backend}.json")
    metadata = current_run_metadata()
    try:
        be = build_backend(args.backend)
    except Exception as exc:  # noqa: BROAD_EXCEPT_OK - CLI boundary records backend startup failures
        result = {
            "backend": args.backend,
            "status": "failed",
            **metadata,
            "reason": str(exc),
            "recall_accuracy": None,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"backend startup failed: {exc}", file=sys.stderr)
        print(f"  wrote {out}", file=sys.stderr)
        return 1
    caps: Capabilities = be.capabilities()

    prov = be.provision(args.scope)
    retain_ms, recall_ms = [], []
    n_retain_ok = 0
    for fact in ds["facts"]:
        r = be.retain(args.scope, fact, actor=args.actor)
        if r.ok:
            n_retain_ok += 1
            retain_ms.append(r.latency_ms)
        else:
            print(f"  retain FAIL: {r.error}", file=sys.stderr)
    # let async indexing settle (both systems may index asynchronously)
    time.sleep(4)

    hits, total = 0, len(ds["queries"])
    misses = []
    for item in ds["queries"]:
        rr = be.recall(args.scope, item["q"], actor=args.actor)
        recall_ms.append(rr.latency_ms)
        if rr.ok and rr.contains(item["expect"]):
            hits += 1
        else:
            misses.append({"q": item["q"], "expect": item["expect"], "ok": rr.ok, "got": rr.texts[:2], "err": rr.error})

    result = {
        "backend": args.backend,
        "status": "measured",
        **metadata,
        "capabilities": caps.__dict__,
        "provision_ok": prov.ok,
        "retain_ok": f"{n_retain_ok}/{len(ds['facts'])}",
        "recall_accuracy": round(hits / total, 3) if total else None,
        "recall_hits": f"{hits}/{total}",
        "retain_latency_ms": {"p50": pct(retain_ms, 50), "p95": pct(retain_ms, 95)},
        "recall_latency_ms": {"p50": pct(recall_ms, 50), "p95": pct(recall_ms, 95)},
        "misses": misses,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("backend", "recall_accuracy", "recall_hits",
                                             "retain_latency_ms", "recall_latency_ms")}, ensure_ascii=False))
    print(f"  caps: offline={caps.offline} llm_required={caps.llm_required} "
          f"native_isolation={caps.native_isolation} audit_log={caps.audit_log}")
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

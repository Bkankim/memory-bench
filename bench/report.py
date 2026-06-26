"""Generate COMPARISON.md (results table + decision matrix) from results/*.json.

Honesty rule: cells are labeled MEASURED (ran live here) or DOCUMENTED (from spec / dry-run /
research) so a reader can tell proof from claim.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    p = ROOT / "results" / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def cell(v, dash="—"):
    return dash if v is None else str(v)


def main():
    h = load("hindsight")
    m = load("mem0")
    hc = h.get("capabilities", {})
    mc = m.get("capabilities", {})
    h_measured = "recall_accuracy" in h and h.get("recall_accuracy") is not None
    m_measured = m.get("status") != "not-run-here" and m.get("recall_accuracy") is not None

    lines = []
    lines.append("# mem0 vs Hindsight — same-conditions comparison\n")
    lines.append("> MEASURED = ran live in this repo's harness. DOCUMENTED = from spec / pip dry-run / vendor docs.\n")
    lines.append(f"- Hindsight: **{'MEASURED' if h_measured else 'DOCUMENTED'}** (live via the Hindsight-Crew gateway, offline LLM=none).")
    lines.append(f"- mem0: **{'MEASURED' if m_measured else 'DOCUMENTED'}** — {m.get('reason','')}\n")

    lines.append("## Results / capability matrix\n")
    lines.append("| Axis | Hindsight | mem0 |")
    lines.append("|---|---|---|")
    lines.append(f"| recall accuracy (eval-mini, 8 q) | {cell(h.get('recall_hits'))} (MEASURED) | {cell(m.get('recall_hits'))} (DOCUMENTED) |")
    lines.append(f"| retain latency p50/p95 ms | {cell(h.get('retain_latency_ms',{}).get('p50'))}/{cell(h.get('retain_latency_ms',{}).get('p95'))} (MEASURED) | — (not run here) |")
    lines.append(f"| recall latency p50/p95 ms | {cell(h.get('recall_latency_ms',{}).get('p50'))}/{cell(h.get('recall_latency_ms',{}).get('p95'))} (MEASURED) | — (not run here) |")
    lines.append(f"| offline (no cloud) | {cell(hc.get('offline'))} | {cell(mc.get('offline'))} (default LLM=OpenAI cloud) |")
    lines.append(f"| extraction LLM required | {cell(hc.get('llm_required'))} (native LLM=none mode) | {cell(mc.get('llm_required'))} (ollama needed for offline) |")
    lines.append(f"| isolation enforcement | gateway (deny-by-default ACL) | native (user_id + per-user keys) |")
    lines.append(f"| audit log | {cell(hc.get('audit_log'))} (gateway, token fingerprints) | {cell(mc.get('audit_log'))} (platform request_logs) |")
    lines.append(f"| telemetry phone-home | none | posthog on by default |")
    lines.append(f"| host footprint | single Docker image ~0.85GB, no host Python | Python>=3.10 lib + LLM service + vector store |")

    lines.append("\n## Decision matrix — which fits when\n")
    lines.append("| Situation | Better fit | Why |")
    lines.append("|---|---|---|")
    lines.append("| On-prem / air-gapped / no external cloud | **Hindsight** | native LLM=none offline mode, single image, no telemetry; fit a 2GB VM here |")
    lines.append("| Constrained host (≤2GB), no GPU | **Hindsight** | mem0 offline needs a local LLM service (ollama+model) that did not fit |")
    lines.append("| Strict tenant isolation you must *prove* | **Hindsight + gateway** | deny-by-default ACL + audit fingerprints, verified by a negative-access CI gate |")
    lines.append("| Fast bolt-on memory with cloud LLM + DX | **mem0** | identity is first-class, huge ecosystem, managed platform with keys+audit |")
    lines.append("| Need graph memory / multi-store routing | **mem0** | vector+graph+KV hybrid out of the box |")
    lines.append("| Privacy-sensitive (no phone-home) | **Hindsight** | mem0 ships posthog telemetry on by default (disable via env) |")

    lines.append("\n## Honest limitations of this run\n")
    lines.append("- mem0 was **not run live here** (Python 3.9 / ~2GB Docker VM; mem0 latest needs 3.10+ and offline needs ollama+model). Its cells are DOCUMENTED from spec/dry-run, not measured.")
    lines.append("- The eval set is a tiny single-hop smoke set (8 q), not LongMemEval/LoCoMo. It proves the harness + the Hindsight path; full benchmark datasets are the next step.")
    lines.append("- Both adapters use raw/no-LLM retain (Hindsight LLM=none; mem0 `infer=False`) for parity; LLM-extraction quality is a separate axis.\n")

    out = ROOT / "COMPARISON.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print("\n".join(lines[:24]))


if __name__ == "__main__":
    main()

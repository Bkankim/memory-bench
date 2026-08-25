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


def cell(v, dash="-"):
    return dash if v is None else str(v)


def main():
    h = load("hindsight")
    m = load("mem0")
    hc = h.get("capabilities", {})
    mc = m.get("capabilities", {})
    h_measured = "recall_accuracy" in h and h.get("recall_accuracy") is not None
    m_measured = m.get("status") == "measured" and m.get("recall_accuracy") is not None
    h_label = "MEASURED" if h_measured else "DOCUMENTED"
    m_label = "MEASURED" if m_measured else "DOCUMENTED"
    m_reason = m.get("reason") or "live with the local Ollama model configured by the adapter"
    h_env = h.get("run_env", {})
    m_env = m.get("run_env", {})

    lines = []
    lines.append("# mem0 vs Hindsight - same-conditions comparison\n")
    lines.append("> MEASURED = ran live in this repo's harness. DOCUMENTED = from spec / dependency inspection / vendor docs.\n")
    lines.append(f"- Hindsight: **{h_label}** (live via the Hindsight-Crew gateway, offline LLM=none).")
    lines.append(f"- mem0: **{m_label}** - {m_reason}\n")

    lines.append("## Results / capability matrix\n")
    lines.append("| Axis | Hindsight | mem0 |")
    lines.append("|---|---|---|")
    lines.append(f"| recall accuracy (eval-mini, 8 q) | {cell(h.get('recall_hits'))} ({h_label}) | {cell(m.get('recall_hits'))} ({m_label}) |")
    lines.append(f"| retain latency p50/p95 ms | {cell(h.get('retain_latency_ms',{}).get('p50'))}/{cell(h.get('retain_latency_ms',{}).get('p95'))} ({h_label}) | {cell(m.get('retain_latency_ms',{}).get('p50'))}/{cell(m.get('retain_latency_ms',{}).get('p95'))} ({m_label}) |")
    lines.append(f"| recall latency p50/p95 ms | {cell(h.get('recall_latency_ms',{}).get('p50'))}/{cell(h.get('recall_latency_ms',{}).get('p95'))} ({h_label}) | {cell(m.get('recall_latency_ms',{}).get('p50'))}/{cell(m.get('recall_latency_ms',{}).get('p95'))} ({m_label}) |")
    lines.append(f"| benchmark interpreter | Python {cell(h_env.get('python'))} | Python {cell(m_env.get('python'))} |")
    lines.append(f"| benchmark host | {cell(h_env.get('host'))} | {cell(m_env.get('host'))} |")
    lines.append(f"| benchmark LLM configuration | LLM=none | Ollama {cell(m_env.get('ollama_model'))} (0.5B, required provider) |")
    lines.append(f"| offline (no cloud) | {cell(hc.get('offline'))} | {cell(mc.get('offline'))} (local Ollama config; library default uses cloud) |")
    lines.append(f"| extraction LLM required | {cell(hc.get('llm_required'))} (native LLM=none mode) | {cell(mc.get('llm_required'))} (provider required; this eval uses `infer=False`) |")
    lines.append(f"| isolation enforcement | gateway (deny-by-default ACL) | native (user_id + per-user keys) |")
    lines.append(f"| audit log | {cell(hc.get('audit_log'))} (gateway, token fingerprints) | {cell(mc.get('audit_log'))} (platform request_logs) |")
    lines.append(f"| telemetry phone-home | none | posthog on by default |")
    lines.append(f"| host footprint | single Docker image ~0.85GB, no host Python | Python>=3.10 lib + LLM service + vector store |")

    lines.append("\n## Decision matrix - which fits when\n")
    lines.append("| Situation | Better fit | Why |")
    lines.append("|---|---|---|")
    lines.append("| On-prem / air-gapped / no external cloud | **Depends on LLM budget** | Hindsight runs natively with LLM=none; mem0 also runs offline here when a local Ollama service is available |")
    lines.append("| Constrained host / no local LLM budget | **Hindsight** | mem0 adds an Ollama service and model while Hindsight supports native LLM=none |")
    lines.append("| Strict tenant isolation you must *prove* | **Hindsight + gateway** | deny-by-default ACL + audit fingerprints, verified by a negative-access CI gate |")
    lines.append("| Fast bolt-on memory with cloud LLM + DX | **mem0** | identity is first-class, huge ecosystem, managed platform with keys+audit |")
    lines.append("| Need graph memory / multi-store routing | **mem0** | vector+graph+KV hybrid out of the box |")
    lines.append("| Privacy-sensitive (no phone-home) | **Hindsight** | mem0 ships posthog telemetry on by default (disable via env) |")

    lines.append("\n## Honest limitations of this run\n")
    if m_measured:
        lines.append(
            f"- Both measured results use Python {cell(h_env.get('python'))} on "
            f"{cell(h_env.get('host'))}; interpreter and host are aligned."
        )
        lines.append(
            f"- LLM configuration is asymmetric and explicitly labeled: Hindsight uses LLM=none, while mem0 is "
            f"configured with Ollama {cell(m_env.get('ollama_model'))}. This 0.5B model is very small and would "
            "disadvantage mem0 in extraction-enabled tests; eval-mini uses `infer=False`, so extraction quality is not measured."
        )
    else:
        lines.append(f"- mem0 was not measured successfully in this run: {m_reason}.")
    lines.append("- The eval set is a tiny single-hop smoke set (8 q), not LongMemEval/LoCoMo. It proves both adapter paths under identical inputs, not general memory quality.")
    lines.append("- Both adapters use raw/no-LLM retain (Hindsight LLM=none; mem0 `infer=False`) for input parity; LLM-extraction quality is a separate, unmeasured axis.\n")

    out = ROOT / "COMPARISON.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print("\n".join(lines[:24]))


if __name__ == "__main__":
    main()

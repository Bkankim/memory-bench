# mem0 vs Hindsight — same-conditions comparison

> MEASURED = ran live in this repo's harness. DOCUMENTED = from spec / pip dry-run / vendor docs.

- Hindsight: **MEASURED** (live via the Hindsight-Crew gateway, offline LLM=none).
- mem0: **DOCUMENTED** — This host is Python 3.9.6 on a ~2GB Docker VM. mem0ai latest requires Python>=3.10; offline mem0 needs a local LLM service (ollama) + a pulled model (multi-GB) since the DEFAULT llm is OpenAI (cloud+key). That does not fit the 2GB VM. Adapter raised the honest error instead of faking numbers.

## Results / capability matrix

| Axis | Hindsight | mem0 |
|---|---|---|
| recall accuracy (eval-mini, 8 q) | 8/8 (MEASURED) | not-measured-here (DOCUMENTED) |
| retain latency p50/p95 ms | 32.3/92.7 (MEASURED) | — (not run here) |
| recall latency p50/p95 ms | 153.0/206.7 (MEASURED) | — (not run here) |
| offline (no cloud) | True | False (default LLM=OpenAI cloud) |
| extraction LLM required | False (native LLM=none mode) | True (ollama needed for offline) |
| isolation enforcement | gateway (deny-by-default ACL) | native (user_id + per-user keys) |
| audit log | True (gateway, token fingerprints) | True (platform request_logs) |
| telemetry phone-home | none | posthog on by default |
| host footprint | single Docker image ~0.85GB, no host Python | Python>=3.10 lib + LLM service + vector store |

## Decision matrix — which fits when

| Situation | Better fit | Why |
|---|---|---|
| On-prem / air-gapped / no external cloud | **Hindsight** | native LLM=none offline mode, single image, no telemetry; fit a 2GB VM here |
| Constrained host (≤2GB), no GPU | **Hindsight** | mem0 offline needs a local LLM service (ollama+model) that did not fit |
| Strict tenant isolation you must *prove* | **Hindsight + gateway** | deny-by-default ACL + audit fingerprints, verified by a negative-access CI gate |
| Fast bolt-on memory with cloud LLM + DX | **mem0** | identity is first-class, huge ecosystem, managed platform with keys+audit |
| Need graph memory / multi-store routing | **mem0** | vector+graph+KV hybrid out of the box |
| Privacy-sensitive (no phone-home) | **Hindsight** | mem0 ships posthog telemetry on by default (disable via env) |

## Honest limitations of this run

- mem0 was **not run live here** (Python 3.9 / ~2GB Docker VM; mem0 latest needs 3.10+ and offline needs ollama+model). Its cells are DOCUMENTED from spec/dry-run, not measured.
- The eval set is a tiny single-hop smoke set (8 q), not LongMemEval/LoCoMo. It proves the harness + the Hindsight path; full benchmark datasets are the next step.
- Both adapters use raw/no-LLM retain (Hindsight LLM=none; mem0 `infer=False`) for parity; LLM-extraction quality is a separate axis.


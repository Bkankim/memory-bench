# mem0 vs Hindsight - same-conditions comparison

> MEASURED = ran live in this repo's harness. DOCUMENTED = from spec / dependency inspection / vendor docs.

- Hindsight: **MEASURED** (live via the Hindsight-Crew gateway, offline LLM=none).
- mem0: **MEASURED** - live with the local Ollama model configured by the adapter

## Results / capability matrix

| Axis | Hindsight | mem0 |
|---|---|---|
| recall accuracy (eval-mini, 8 q) | 8/8 (MEASURED) | 8/8 (MEASURED) |
| retain latency p50/p95 ms | 5466.0/6466.8 (MEASURED) | 13.3/151.5 (MEASURED) |
| recall latency p50/p95 ms | 399.3/1190.0 (MEASURED) | 11.4/409.1 (MEASURED) |
| benchmark interpreter | Python 3.13.14 | Python 3.13.14 |
| benchmark host | macOS-26.5.2-arm64-arm-64bit-Mach-O | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| benchmark LLM configuration | LLM=none | Ollama qwen2.5:0.5b (0.5B, required provider) |
| offline (no cloud) | True | True (local Ollama config; library default uses cloud) |
| extraction LLM required | False (native LLM=none mode) | True (provider required; this eval uses `infer=False`) |
| isolation enforcement | gateway (deny-by-default ACL) | native (user_id + per-user keys) |
| audit log | True (gateway, token fingerprints) | True (platform request_logs) |
| telemetry phone-home | none | posthog on by default |
| host footprint | single Docker image ~0.85GB, no host Python | Python>=3.10 lib + LLM service + vector store |

## Decision matrix - which fits when

| Situation | Better fit | Why |
|---|---|---|
| On-prem / air-gapped / no external cloud | **Depends on LLM budget** | Hindsight runs natively with LLM=none; mem0 also runs offline here when a local Ollama service is available |
| Constrained host / no local LLM budget | **Hindsight** | mem0 adds an Ollama service and model while Hindsight supports native LLM=none |
| Strict tenant isolation you must *prove* | **Hindsight + gateway** | deny-by-default ACL + audit fingerprints, verified by a negative-access CI gate |
| Fast bolt-on memory with cloud LLM + DX | **mem0** | identity is first-class, huge ecosystem, managed platform with keys+audit |
| Need graph memory / multi-store routing | **mem0** | vector+graph+KV hybrid out of the box |
| Privacy-sensitive (no phone-home) | **Hindsight** | mem0 ships posthog telemetry on by default (disable via env) |

## Honest limitations of this run

- Both measured results use Python 3.13.14 on macOS-26.5.2-arm64-arm-64bit-Mach-O; interpreter and host are aligned.
- LLM configuration is asymmetric and explicitly labeled: Hindsight uses LLM=none, while mem0 is configured with Ollama qwen2.5:0.5b. This 0.5B model is very small and would disadvantage mem0 in extraction-enabled tests; eval-mini uses `infer=False`, so extraction quality is not measured.
- The eval set is a tiny single-hop smoke set (8 q), not LongMemEval/LoCoMo. It proves both adapter paths under identical inputs, not general memory quality.
- Both adapters use raw/no-LLM retain (Hindsight LLM=none; mem0 `infer=False`) for input parity; LLM-extraction quality is a separate, unmeasured axis.


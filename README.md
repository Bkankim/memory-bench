# memory-bench

A **same-conditions** comparison harness for self-hosted AI memory layers - **mem0 vs Hindsight** - built to develop discernment about *which open-source memory fits which situation* (on-prem vs cloud, constrained vs not, isolation-critical vs DX-first).

It is the downstream eval companion to [Hindsight-Crew](https://github.com/Bkankim/Hindsight-Crew): it plugs the live Hindsight-Crew gateway in as one backend and mem0 as the other, behind one adapter interface, and scores them on the axes that actually drive the decision.

## Thesis

Most memory comparisons stop at recall accuracy. The decision that matters for real deployments also hinges on **offline-ability, LLM dependency, isolation enforcement, audit/telemetry, and host footprint** - so this harness measures those too and emits a **decision matrix**, not just a leaderboard.

## What it measures

- **recall accuracy** on a reproducible eval set (retain facts → query → expected substring)
- **retain / recall latency** (p50/p95)
- **capability axes**: offline, extraction-LLM-required, isolation enforcement, audit log, telemetry, host footprint
- → a **decision matrix** ("which fits when") in [`COMPARISON.md`](COMPARISON.md)

## Headline result (this run)

| | Hindsight (MEASURED, live) | mem0 (MEASURED, live) |
|---|---|---|
| recall acc (eval-mini) | **8/8** | **8/8** |
| offline / LLM-required | **yes / no** (native `LLM=none`) | **yes / yes** (local Ollama provider; eval uses `infer=False`) |
| isolation | gateway deny-by-default ACL + audit | native `user_id` + per-user keys |
| host footprint | single Docker image ~0.85 GB | Python 3.13 + Ollama + Chroma |

**Honesty:** both backends were run live with the same eval input, Python 3.13.14, and host. Their LLM configuration is intentionally asymmetric: Hindsight uses `LLM=none`; mem0 initializes a required local Ollama provider with `qwen2.5:0.5b`, a very small model. This eval retains raw facts with `infer=False`, so it does not measure LLM extraction quality. See [`COMPARISON.md`](COMPARISON.md) for measured latency and the labeled conditions.

## Layout

```
adapters/  base.py (MemoryBackend) · hindsight.py (live gateway REST) · mem0_adapter.py (offline ollama config)
bench/     run.py (accuracy+latency) · report.py (decision matrix) · isolation.py (cross-tenant red-team)
data/      eval-mini.json (reproducible recall set)
results/   per-backend JSON + COMPARISON.md
```

## Run it

```sh
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# Hindsight side - needs the Hindsight-Crew stack up (./bootstrap there) + demo tokens
export HC_GW=http://127.0.0.1:8888 HC_DEMO_TOKEN_ALICE=<token>
.venv/bin/python -m bench.run --backend hindsight --scope personal-alice

# mem0 side - local pinned providers used by this measured run
uv pip install --python .venv/bin/python "mem0ai==2.0.8" "chromadb==1.5.9" "sentence-transformers==6.0.0" "ollama==0.6.2"
ollama pull qwen2.5:0.5b
.venv/bin/python -m bench.run --backend mem0 --scope alice

.venv/bin/python -m bench.report   # regenerate COMPARISON.md
```

## License

MIT.

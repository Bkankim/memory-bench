# memory-bench

A **same-conditions** comparison harness for self-hosted AI memory layers — **mem0 vs Hindsight** — built to develop discernment about *which open-source memory fits which situation* (on-prem vs cloud, constrained vs not, isolation-critical vs DX-first).

It is the downstream eval companion to [Hindsight-Crew](https://github.com/Bkankim/Hindsight-Crew): it plugs the live Hindsight-Crew gateway in as one backend and mem0 as the other, behind one adapter interface, and scores them on the axes that actually drive the decision.

## Thesis

Most memory comparisons stop at recall accuracy. The decision that matters for real deployments also hinges on **offline-ability, LLM dependency, isolation enforcement, audit/telemetry, and host footprint** — so this harness measures those too and emits a **decision matrix**, not just a leaderboard.

## What it measures

- **recall accuracy** on a reproducible eval set (retain facts → query → expected substring)
- **retain / recall latency** (p50/p95)
- **capability axes**: offline, extraction-LLM-required, isolation enforcement, audit log, telemetry, host footprint
- → a **decision matrix** ("which fits when") in [`COMPARISON.md`](COMPARISON.md)

## Headline result (this run)

| | Hindsight (MEASURED, live) | mem0 (DOCUMENTED) |
|---|---|---|
| recall acc (eval-mini) | **8/8** | not run here |
| offline / LLM-required | **yes / no** (native `LLM=none`) | no / yes (default cloud LLM) |
| isolation | gateway deny-by-default ACL + audit | native user_id + per-user keys |
| host footprint | single Docker image ~0.85 GB | Python≥3.10 + LLM service + vector store |

**Honesty:** mem0 was **not run live in this environment** (Python 3.9 / ~2 GB Docker VM; mem0 latest needs 3.10+, offline needs an ollama LLM that didn't fit). Its cells are documented from spec/pip-dry-run, clearly labeled, and the adapter **raises instead of faking numbers**. Full LongMemEval/LoCoMo runs are the next step. See [`COMPARISON.md`](COMPARISON.md).

## Layout

```
adapters/  base.py (MemoryBackend) · hindsight.py (live gateway REST) · mem0_adapter.py (offline ollama config)
bench/     run.py (accuracy+latency) · report.py (decision matrix) · isolation.py (cross-tenant red-team)
data/      eval-mini.json (reproducible recall set)
results/   per-backend JSON + COMPARISON.md
```

## Run it

```sh
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Hindsight side — needs the Hindsight-Crew stack up (./bootstrap there) + demo tokens
export HC_GW=http://127.0.0.1:8888 HC_DEMO_TOKEN_ALICE=<token>
python -m bench.run --backend hindsight --scope personal-alice

# mem0 side — needs Python>=3.10 + a local ollama model for offline parity
pip install "mem0ai" && ollama pull qwen2.5:0.5b
python -m bench.run --backend mem0 --scope alice

python -m bench.report   # regenerate COMPARISON.md
```

## License

MIT.

"""Isolation red-team — the governance axis most memory comparisons skip.

Drives the live Hindsight backend (via the Hindsight-Crew gateway) with two actors and
asserts cross-tenant access is DENIED while own-bank access works. Prints a pass/fail
matrix. mem0's equivalent (per-user key scoping) is documented in COMPARISON.md; running
it live requires a mem0 deployment (see README), so this script targets the Hindsight path
that is live here and never fakes a mem0 result.

Usage: python -m bench.isolation
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.hindsight import HindsightBackend


def main() -> int:
    alice = os.environ.get("HC_DEMO_TOKEN_ALICE", "")
    bob = os.environ.get("HC_DEMO_TOKEN_BOB", "")
    if not alice or not bob:
        print("isolation: need HC_DEMO_TOKEN_ALICE and HC_DEMO_TOKEN_BOB (from Hindsight-Crew secrets/)", file=sys.stderr)
        return 2

    be = HindsightBackend(token_map={"alice": alice, "bob": bob}, default_token=alice)
    # ensure both personal banks exist
    be.provision("personal-alice")
    # bob provisions his own bank with his token
    import httpx
    httpx.Client(timeout=15).put(f"{be.base}/v1/{be.tenant}/banks/personal-bob",
                                 json={"name": "personal-bob"}, headers={"authorization": f"Bearer {bob}"})

    checks = []
    def record(desc, expect_ok, got_ok, detail=""):
        ok = (expect_ok == got_ok)
        checks.append((ok, desc, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {desc}{(' :: ' + detail) if detail else ''}")

    # 1) alice -> her own bank: allowed
    r = be.recall("personal-alice", "anything", actor="alice")
    record("alice recall own personal-alice -> allowed", True, r.ok, r.error or "200")
    # 2) alice -> bob's bank: DENIED
    r = be.recall("personal-bob", "anything", actor="alice")
    record("alice recall personal-bob -> DENIED", False, r.ok, r.error or "200")
    # 3) bob -> alice's bank: DENIED
    r = be.recall("personal-alice", "anything", actor="bob")
    record("bob recall personal-alice -> DENIED", False, r.ok, r.error or "200")
    # 4) alice -> shared team-eng: allowed (both members)
    r = be.recall("team-eng", "anything", actor="alice")
    record("alice recall team-eng (shared) -> allowed", True, r.ok, r.error or "200")

    failed = [c for c in checks if not c[0]]
    print(f"\nisolation: {len(checks)-len(failed)}/{len(checks)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

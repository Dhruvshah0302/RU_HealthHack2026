"""Score the router against the labeled requests in eval/requests.jsonl.

    python -m eval.run_eval                 # model if BEDROCK_MODEL_ID is set, else baseline
    python -m eval.run_eval --mode baseline
    python -m eval.run_eval --mode llm

The number that matters most is urgent recall: of the requests that needed an
urgent nurse alert, how many got one. Every miss is printed so it can be read.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv

from app.baseline import BaselineClassifier
from app.models import NURSE, URGENT
from app.router import route

HERE = Path(__file__).parent


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for a proportion. Honest for small n and for rates near 0 or 1."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def rate(successes: int, n: int) -> str:
    if n == 0:
        return "n/a"
    low, high = wilson(successes, n)
    return f"{successes}/{n} = {successes / n:.0%}  (95% CI {low:.0%} to {high:.0%})"


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", choices=["baseline", "llm"],
                        default="llm" if os.getenv("BEDROCK_MODEL_ID") else "baseline")
    parser.add_argument("--file", default=str(HERE / "requests.jsonl"))
    args = parser.parse_args()

    if args.mode == "llm":
        from app.llm import BedrockClassifier
        classifier = BedrockClassifier()
    else:
        classifier = BaselineClassifier()

    items = [json.loads(line) for line in Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip()]
    rows, latencies = [], []
    for item in items:
        start = time.perf_counter()
        decision = route(item["text"], classifier)
        latencies.append(time.perf_counter() - start)
        got = {(t.department, t.priority) for t in decision.tickets}
        expected = {(e["department"], e["priority"]) for e in item["expected"]}
        rows.append({
            "id": item["id"], "slice": item["slice"], "lang": item["lang"], "text": item["text"],
            "expected": sorted(expected), "got": sorted(got),
            "needs_urgent": (NURSE, URGENT) in expected,
            "got_urgent": (NURSE, URGENT) in got,
            "needs_nurse": any(d == NURSE for d, _ in expected),
            "got_nurse": any(d == NURSE for d, _ in got),
            "exact": got == expected,
            "rule_flags": decision.rule_flags, "fail_safe": decision.fail_safe,
        })

    def count(pred, pool=rows):
        return sum(1 for r in pool if pred(r))

    urgent = [r for r in rows if r["needs_urgent"]]
    not_urgent = [r for r in rows if not r["needs_urgent"]]
    clinical = [r for r in rows if r["needs_nurse"]]
    non_clinical = [r for r in rows if not r["needs_nurse"]]

    print(f"\nMode: {args.mode}   Requests: {len(rows)}\n")
    print("Safety")
    print(f"  Urgent requests that got an urgent nurse alert   {rate(count(lambda r: r['got_urgent'], urgent), len(urgent))}")
    for name in ("urgent_direct", "urgent_indirect", "mixed", "multilingual"):
        pool = [r for r in urgent if r["slice"] == name]
        print(f"    {name:<18}{rate(count(lambda r: r['got_urgent'], pool), len(pool))}")
    print(f"  Clinical requests that reached the nurse at all  {rate(count(lambda r: r['got_nurse'], clinical), len(clinical))}")
    print("\nBurden on nurses")
    print(f"  Non-clinical requests kept off the nurse's list  {rate(count(lambda r: not r['got_nurse'], non_clinical), len(non_clinical))}")
    print(f"  Non-urgent requests wrongly raised as urgent     {rate(count(lambda r: r['got_urgent'], not_urgent), len(not_urgent))}")
    print("\nRouting")
    print(f"  Requests routed exactly as labeled               {rate(count(lambda r: r['exact']), len(rows))}")
    ordered = sorted(latencies)
    print(f"\nLatency: median {statistics.median(ordered) * 1000:.0f} ms, "
          f"95th percentile {ordered[int(0.95 * (len(ordered) - 1))] * 1000:.0f} ms")

    missed = [r for r in urgent if not r["got_urgent"]]
    print(f"\nMissed urgent requests ({len(missed)}):")
    for r in missed:
        where = "reached nurse as routine" if r["got_nurse"] else "DID NOT REACH A NURSE"
        print(f"  {r['id']}  [{where}]  {r['text']}")

    out = HERE / f"results_{args.mode}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nPer-request results written to {out}")


if __name__ == "__main__":
    main()

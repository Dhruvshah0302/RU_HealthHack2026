"""Score the router against the labeled requests in eval/requests.jsonl.

    python -m eval.run_eval --mode baseline
    python -m eval.run_eval --model us.anthropic.claude-haiku-4-5-20251001-v1:0
    python -m eval.run_eval --model <id> --split dev     # the half we tune the prompt on
    python -m eval.run_eval --model <id> --split test    # the half we report

With no arguments it uses the model in BEDROCK_MODEL_ID, or the keyword baseline
if that is not set.

The number that matters most is urgent recall: of the requests that needed an
urgent nurse alert, how many got one. Every miss is printed so it can be read.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
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


def load_items(path: str | Path, split: str = "all") -> list[dict]:
    """Read the labeled requests. "dev" and "test" are fixed halves: within each
    slice, requests alternate dev, test, dev, test in file order. Tune the prompt
    on dev and report test, so the reported number is not flattered by the tuning."""
    items = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    seen: dict[str, int] = {}
    for item in items:
        position = seen.get(item["slice"], 0)
        seen[item["slice"]] = position + 1
        item["split"] = "dev" if position % 2 == 0 else "test"
    return items if split == "all" else [item for item in items if item["split"] == split]


def score(items: list[dict], classifier) -> tuple[list[dict], list[float]]:
    """Route every request and compare the tickets with the labels."""
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
    return rows, latencies


def bedrock_classifier(model_id: str):
    """The model, with patient retries. An evaluation should measure the model's
    answers, not how often a shared workshop account gets throttled."""
    import boto3
    from botocore.config import Config

    from app.llm import BedrockClassifier
    client = boto3.client(
        "bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"),
        config=Config(read_timeout=30, connect_timeout=5, retries={"max_attempts": 8, "mode": "adaptive"}),
    )
    return BedrockClassifier(model_id=model_id, client=client)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", choices=["baseline", "llm"], default=None)
    parser.add_argument("--model", default=None, help="Bedrock model or inference-profile ID (implies --mode llm)")
    parser.add_argument("--split", choices=["all", "dev", "test"], default="all")
    parser.add_argument("--file", default=str(HERE / "requests.jsonl"))
    parser.add_argument("--price-in", type=float, default=None, help="US dollars per million input tokens")
    parser.add_argument("--price-out", type=float, default=None, help="US dollars per million output tokens")
    args = parser.parse_args(argv)

    model_id = args.model or os.getenv("BEDROCK_MODEL_ID")
    mode = args.mode or ("llm" if model_id else "baseline")
    if mode == "llm" and not model_id:
        print("Set --model or BEDROCK_MODEL_ID to run the model.")
        return 2

    if mode == "llm":
        try:                                   # one direct call first, so a setup problem is shown in full
            classifier = bedrock_classifier(model_id)
            classifier.classify("Can I get an extra pillow?")
        except Exception as exc:
            print(f"The model call failed before the evaluation started.\n  model: {model_id}\n  error: {exc}")
            return 2
        classifier.calls = classifier.input_tokens = classifier.output_tokens = 0
        label = model_id
    else:
        classifier = BaselineClassifier()
        label = "baseline"

    items = load_items(args.file, args.split)
    rows, latencies = score(items, classifier)

    def count(pred, pool=rows):
        return sum(1 for r in pool if pred(r))

    urgent = [r for r in rows if r["needs_urgent"]]
    not_urgent = [r for r in rows if not r["needs_urgent"]]
    clinical = [r for r in rows if r["needs_nurse"]]
    non_clinical = [r for r in rows if not r["needs_nurse"]]
    got_urgent = count(lambda r: r["got_urgent"], urgent)
    off_nurse = count(lambda r: not r["got_nurse"], non_clinical)
    false_urgent = count(lambda r: r["got_urgent"], not_urgent)
    exact = count(lambda r: r["exact"])

    print(f"\nMode: {label}   Split: {args.split}   Requests: {len(rows)}\n")
    print("Safety")
    print(f"  Urgent requests that got an urgent nurse alert   {rate(got_urgent, len(urgent))}")
    for name in ("urgent_direct", "urgent_indirect", "mixed", "multilingual"):
        pool = [r for r in urgent if r["slice"] == name]
        print(f"    {name:<18}{rate(count(lambda r: r['got_urgent'], pool), len(pool))}")
    print(f"  Clinical requests that reached the nurse at all  {rate(count(lambda r: r['got_nurse'], clinical), len(clinical))}")
    print("\nBurden on nurses")
    print(f"  Non-clinical requests kept off the nurse's list  {rate(off_nurse, len(non_clinical))}")
    print(f"  Non-urgent requests wrongly raised as urgent     {rate(false_urgent, len(not_urgent))}")
    print("\nRouting")
    print(f"  Requests routed exactly as labeled               {rate(exact, len(rows))}")

    ordered = sorted(latencies)
    median_ms = statistics.median(ordered) * 1000
    p95_ms = ordered[int(0.95 * (len(ordered) - 1))] * 1000
    print(f"\nTime per request: median {median_ms:.0f} ms, 95th percentile {p95_ms:.0f} ms")

    tokens = ""
    if mode == "llm":
        failed = [r for r in rows if (r["fail_safe"] or "").startswith("classifier failed")]
        unsure = [r for r in rows if (r["fail_safe"] or "").startswith("low confidence")]
        print("\nFallbacks to the nurse")
        print(f"  Model call or answer failed    {len(failed)}" +
              (f"   ({', '.join(sorted({r['fail_safe'] for r in failed}))})" if failed else ""))
        print(f"  Model answered but was unsure  {len(unsure)}")
        calls = max(classifier.calls, 1)
        mean_in, mean_out = classifier.input_tokens / calls, classifier.output_tokens / calls
        tokens = f" | tokens in/out {mean_in:.0f}/{mean_out:.0f}"
        print(f"\nTokens per request: {mean_in:.0f} in, {mean_out:.0f} out  ({classifier.calls} calls)")
        if args.price_in is not None and args.price_out is not None:
            per_request = (mean_in * args.price_in + mean_out * args.price_out) / 1_000_000
            tokens += f" | ${per_request * 1000:.2f} per 1,000 requests"
            print(f"Model cost: ${per_request * 1000:.2f} per 1,000 requests")

    missed = [r for r in urgent if not r["got_urgent"]]
    print(f"\nMissed urgent requests ({len(missed)}):")
    for r in missed:
        where = "reached nurse as routine" if r["got_nurse"] else "DID NOT REACH A NURSE"
        print(f"  {r['id']}  [{where}]  {r['text']}")

    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    out = HERE / f"results_{slug}_{args.split}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nPer-request results written to {out}")

    def pct(a: int, b: int) -> str:
        return f"{a}/{b} ({a / b:.0%})" if b else "n/a"

    print(f"\nSUMMARY | {label} | {args.split} | urgent caught {pct(got_urgent, len(urgent))}"
          f" | kept off nurse {pct(off_nurse, len(non_clinical))}"
          f" | false urgent {pct(false_urgent, len(not_urgent))}"
          f" | exact {pct(exact, len(rows))} | median {median_ms:.0f} ms{tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

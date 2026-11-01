"""Semantic-cache benchmark.

Measures the speedup from a semantic response cache: a genuine cold pass runs
the full agent and populates the cache; the warm pass is a semantic hit. Prior
versions reported garbage because the persistent cache was never cleared (every
"cold" query was already a hit) and time.time() subtraction went negative on
embedding-load stalls. This version clears only the response_cache collection,
uses a monotonic clock, and warms the embedding model before timing.

With --paraphrase, each query also gets a third pass using a reworded version
of it (eval/queries.py PARAPHRASED_QUERIES), and the exact-string and
paraphrase hit rates are reported separately. A paraphrase miss runs the full
agent, so that pass costs a model call per miss.

Every run also writes eval/results/semantic_cache_<timestamp>.json.
"""
import os
# Cold calls must reach the model, not the LangChain response cache.
os.environ["DISABLE_CACHE"] = "1"

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from rag.semantic_cache import get_response, clear_cache, get_cached_response
from eval.queries import QUERIES, PARAPHRASED_QUERIES

RESULTS_DIR = Path(__file__).parent / "results"


def run_benchmark(paraphrase=False):
    print("=" * 80)
    print("SEMANTIC CACHE BENCHMARK" + (" (with paraphrase pass)" if paraphrase else ""))
    print("=" * 80)

    # True cold baseline: empty the response cache (RAG index is untouched).
    clear_cache()
    # Warm the embedding model so its one-time load doesn't distort query 1.
    get_cached_response("warmup probe")

    cold_times, warm_times, para_times = [], [], []
    cold_miss = warm_hit = para_hit = 0
    rows = []

    for i, query in enumerate(QUERIES):
        try:
            t = time.perf_counter()
            _, cold_cached = get_response(query)       # miss -> real agent, caches
            cold = time.perf_counter() - t
        except Exception as e:
            print(f"[cold] Query {i+1:>2}: SKIPPED ({type(e).__name__}) — cold call failed", flush=True)
            continue
        cold_times.append(cold)
        if not cold_cached:
            cold_miss += 1
        print(f"[cold] Query {i+1:>2}: {cold:6.2f}s | cached={cold_cached}", flush=True)

        t = time.perf_counter()
        _, warm_cached = get_response(query)          # semantic hit
        warm = time.perf_counter() - t
        warm_times.append(warm)
        if warm_cached:
            warm_hit += 1
        print(f"[warm] Query {i+1:>2}: {warm:6.2f}s | cached={warm_cached}", flush=True)
        row = {"query": query, "cold_s": round(cold, 3), "cold_cached": cold_cached,
               "warm_s": round(warm, 3), "warm_cached": warm_cached}

        if paraphrase:
            para_q = PARAPHRASED_QUERIES[i]
            try:
                t = time.perf_counter()
                _, para_cached = get_response(para_q)  # hit only if close enough
                para = time.perf_counter() - t
            except Exception as e:
                print(f"[para] Query {i+1:>2}: SKIPPED ({type(e).__name__}) — miss call failed", flush=True)
                row.update(paraphrase=para_q, paraphrase_error=type(e).__name__)
                rows.append(row)
                continue
            para_times.append(para)
            if para_cached:
                para_hit += 1
            print(f"[para] Query {i+1:>2}: {para:6.2f}s | cached={para_cached}", flush=True)
            row.update(paraphrase=para_q, paraphrase_s=round(para, 3), paraphrase_cached=para_cached)
        rows.append(row)

    print("\n--- Results ---")
    print(f"{'Query':<58} {'Cold':>8} {'Warm':>8} {'Speedup':>10}")
    print("-" * 88)
    for q, c, w in zip(QUERIES, cold_times, warm_times):
        su = c / w if w > 0 else 0
        print(f"{q[:56]:<58} {c:7.2f}s {w:7.2f}s {su:9.1f}x")
    print("-" * 88)

    avg_cold = sum(cold_times) / len(cold_times)
    avg_warm = sum(warm_times) / len(warm_times)
    # Median speedup is the honest headline: means are dominated by the few
    # slow cold calls, and a per-query ratio is what a user actually feels.
    ratios = sorted(c / w for c, w in zip(cold_times, warm_times) if w > 0)
    median = ratios[len(ratios) // 2] if ratios else 0
    print(f"{'Average':<58} {avg_cold:7.2f}s {avg_warm:7.2f}s {avg_cold/avg_warm:9.1f}x")
    print(f"{'Median per-query speedup':<58} {'':>8} {'':>8} {median:9.1f}x")
    print(f"\nIntegrity: cold misses {cold_miss}/{len(cold_times)}, warm hits {warm_hit}/{len(warm_times)} (of {len(QUERIES)} queries)")
    print("(A valid run needs cold misses = warm hits = all queries.)")
    print(f"\nHit rate — exact string: {warm_hit}/{len(warm_times)}")
    if paraphrase:
        print(f"Hit rate — paraphrased:  {para_hit}/{len(para_times)}")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"semantic_cache_{ts}.json"
    out.write_text(json.dumps({
        "meta": {"timestamp": ts, "threshold": 0.15, "paraphrase": paraphrase, "n_queries": len(QUERIES)},
        "summary": {
            "avg_cold_s": avg_cold, "avg_warm_s": avg_warm, "median_speedup": median,
            "cold_misses": cold_miss, "exact_hits": warm_hit, "exact_total": len(warm_times),
            "paraphrase_hits": para_hit if paraphrase else None,
            "paraphrase_total": len(para_times) if paraphrase else None,
        },
        "rows": rows,
    }, indent=2, ensure_ascii=False))
    print(f"Wrote {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--paraphrase", action="store_true",
                        help="add a pass with reworded queries and report its hit rate separately")
    run_benchmark(paraphrase=parser.parse_args().paraphrase)

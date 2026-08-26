"""Semantic-cache benchmark.

Measures the speedup from a semantic response cache: a genuine cold pass runs
the full agent and populates the cache; the warm pass is a semantic hit. Prior
versions reported garbage because the persistent cache was never cleared (every
"cold" query was already a hit) and time.time() subtraction went negative on
embedding-load stalls. This version clears only the response_cache collection,
uses a monotonic clock, and warms the embedding model before timing.
"""
import time

from rag.semantic_cache import get_response, clear_cache, get_cached_response
from eval.queries import QUERIES


def run_benchmark():
    print("=" * 80)
    print("SEMANTIC CACHE BENCHMARK")
    print("=" * 80)

    # True cold baseline: empty the response cache (RAG index is untouched).
    clear_cache()
    # Warm the embedding model so its one-time load doesn't distort query 1.
    get_cached_response("warmup probe")

    cold_times, warm_times = [], []
    cold_miss = warm_hit = 0

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


if __name__ == "__main__":
    run_benchmark()

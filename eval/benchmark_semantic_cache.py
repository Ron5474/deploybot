import time
import os

os.environ["DISABLE_CACHE"] = "1"

from rag.semantic_cache import get_response
from eval.queries import QUERIES


def run_benchmark():
    print("=" * 80)
    print("SEMANTIC CACHE BENCHMARK")
    print("=" * 80)

    cold_times = []
    warm_times = []

    for i, query in enumerate(QUERIES):
        # Cold pass
        start = time.time()
        _, was_cached = get_response(query)
        cold_time = time.time() - start
        cold_times.append(cold_time)
        print(f"[cold] Query {i+1}: {cold_time:.2f}s | cached={was_cached}")

        # Warm pass
        start = time.time()
        _, was_cached = get_response(query)
        warm_time = time.time() - start
        warm_times.append(warm_time)
        print(f"[warm] Query {i+1}: {warm_time:.2f}s | cached={was_cached}")

    print("\n--- Results ---")
    print(f"{'Query':<60} {'Cold':>8} {'Warm':>8} {'Speedup':>10}")
    print("-" * 90)
    for i, (q, t1, t2) in enumerate(zip(QUERIES, cold_times, warm_times)):
        speedup = t1 / t2 if t2 > 0 else 0
        print(f"{q[:58]:<60} {t1:>7.2f}s {t2:>7.2f}s {speedup:>9.1f}x")

    print("-" * 90)
    avg_cold = sum(cold_times) / len(cold_times)
    avg_warm = sum(warm_times) / len(warm_times)
    print(f"{'Average':<60} {avg_cold:>7.2f}s {avg_warm:>7.2f}s {avg_cold/avg_warm:>9.1f}x")


run_benchmark()



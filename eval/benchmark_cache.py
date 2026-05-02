import time
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.globals import set_llm_cache
from langchain_community.cache import InMemoryCache
from langchain_core.messages import HumanMessage

from eval.queries import QUERIES

load_dotenv()

llm = ChatOpenAI(
        base_url=os.environ["MODEL_BASE_URL"],
        api_key=os.environ["MODEL_API_KEY"],
        model=os.environ["MODEL_NAME"]
)

def run_queries(label):
    times = []
    for i, query in enumerate(QUERIES[:5]):
        start = time.time()
        llm.invoke([HumanMessage(content=query)])
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"[{label}] Query {i+1}: {elapsed:.2f}s")

    return times


# Run without cache
set_llm_cache(None)
no_cache_times = run_queries("no-cache")


# Enable cache and warm it
set_llm_cache(InMemoryCache())
run_queries("warm-up")

# Run with warm cache
cached_times = run_queries("cached")

print("\n--- Benchmark Results ---")
print(f"{'Query':<60} {'No Cache':>10} {'Cached':>10} {'Speedup':>10}")
print("-" * 92)
for i, (q, t1, t2) in enumerate(zip(QUERIES, no_cache_times, cached_times)):
    speedup = t1 / t2 if t2 > 0 else 0
    print(f"{q[:58]:<60} {t1:>9.2f}s {t2:>9.2f}s {speedup:>9.1f}x")

print("-" * 92)
print(f"{'Average':<60} {sum(no_cache_times)/len(no_cache_times):>9.2f}s {sum(cached_times)/len(cached_times):>9.2f}s")




import os
os.environ["DISABLE_CACHE"] = "1"

import logging
logging.disable(logging.CRITICAL)

import textwrap
import time
import uuid
from openai import OpenAI
from agent.agent import agent
from agent.prompts import SYSTEM_PROMPT
from eval.queries import QUERIES

RUN_ID = uuid.uuid4().hex[:8]
COL = 90

_small_client = OpenAI(
    base_url=os.environ["MODEL_BASE_URL"],
    api_key=os.environ["SMALL_MODEL_API_KEY"],
)
_small_model = os.environ["SMALL_MODEL_NAME"]


def run_large(query, session_id):
    result = agent.invoke(
        {"messages": [("human", query)]},
        config={"configurable": {"thread_id": session_id}}
    )
    msg = result["messages"][-1]
    return msg.content or "(no response)"


def run_small(query):
    response = _small_client.chat.completions.create(
        model=_small_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"/no_think\n{query}"},
        ]
    )
    msg = response.choices[0].message
    d = msg.model_dump()
    return d.get("content") or d.get("reasoning_content") or "(no response)"


def preview(text, width=COL - 12, lines=2):
    text = text.replace("\n", " ").strip()
    wrapped = textwrap.wrap(text, width)
    clipped = wrapped[:lines]
    suffix = "…" if len(wrapped) > lines else ""
    return ("\n" + " " * 12).join(clipped) + suffix


print("=" * COL)
print("DEPLOYBOT MODEL COMPARISON")
print(f"Run ID: {RUN_ID}")
print("=" * COL)

total_large, total_small = 0, 0
results = []

for i, q in enumerate(QUERIES):
    t0 = time.time()
    large_r = run_large(q, f"bench-large-{RUN_ID}-{i}")
    large_t = time.time() - t0

    t0 = time.time()
    small_r = run_small(q)
    small_t = time.time() - t0

    speedup = large_t / small_t if small_t > 0 else 0
    total_large += large_t
    total_small += small_t
    results.append((i + 1, q, large_t, large_r, small_t, small_r, speedup))

    print(f"\n[{i+1:>2}/{len(QUERIES)}] {q[:COL - 10]}")
    print(f"  Large  {large_t:>6.1f}s  {preview(large_r)}")
    print(f"  Small  {small_t:>6.1f}s  {preview(small_r)}")

print("\n" + "=" * COL)
print(f"{'#':<4}  {'Large(s)':>8}  {'Small(s)':>8}  {'Speedup':>8}  Query")
print("-" * COL)
for idx, q, lt, _, st, _, su in results:
    print(f"{idx:<4}  {lt:>8.2f}  {st:>8.2f}  {su:>7.1f}x  {q[:40]}")
print("-" * COL)
avg_speedup = total_large / total_small if total_small > 0 else 0
print(f"{'AVG':<4}  {total_large/len(QUERIES):>8.2f}  {total_small/len(QUERIES):>8.2f}  {avg_speedup:>7.1f}x")
print("=" * COL)

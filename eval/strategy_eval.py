"""Prompting-strategy evaluation.

Runs every query in eval/queries.py through the four chat endpoints
(/chat baseline, /chat/chain, /chat/meta, /chat/reflect), N times each, and
records wall-clock latency, prompt/completion tokens, the response and the raw
output of every tool the agent called. Each response is scored 1-5 by an LLM
judge that sees the query, the response, and those tool outputs as reference
facts (rubric in eval/judge_prompt.txt), so it grades CVE ids and other live
data against what the tools returned rather than its own training cutoff.

The endpoints are called in-process through FastAPI's TestClient, so the real
route handlers run (including output redaction), and a callback attached to
the app's LLM counts tokens. The HTTP API itself does not return token counts,
so this is the only way to get them without changing app code. The LLM cache is
disabled so repeat runs hit the model.

Usage:
    uv run python -m eval.strategy_eval                 # 20 queries x 4 strategies x 3 runs
    uv run python -m eval.strategy_eval --queries all   # plus the 10 extra compose queries
    uv run python -m eval.strategy_eval --limit 1 --runs 1   # smoke test
    uv run python -m eval.strategy_eval --judge-only eval/results/strategy_eval_<ts>.json
    uv run python -m eval.strategy_eval --queries all --resume eval/results/strategy_eval_<ts>.json

Generation runs one call at a time so latency is not skewed; judging runs in a
small thread pool alongside it (JUDGE_WORKERS, default 4), since the judge is
the slow part. --resume continues a stopped run in the same file: finished
rows are kept, missing ones are generated, and rows that were never judged
are judged.

--judge-only re-scores every row of an earlier run without regenerating, and
writes strategy_eval_<new ts>_judged-<judge>.json/.md. Runs written before tool
outputs were recorded get them from the LangGraph checkpointer
(conversation_history.db) by session_id; only the ReAct agent (baseline and
reflection) calls tools, so chaining and meta rows have no reference facts.

Judge model env vars (default to the app's main model):
    JUDGE_MODEL_NAME, JUDGE_BASE_URL, JUDGE_API_KEY
    JUDGE_EXTRA_BODY  JSON request extras (default {"enable_thinking": false},
                      which Qwen needs; set to {} for other providers)
"""
import os
os.environ["DISABLE_CACHE"] = "1"

import logging
logging.disable(logging.CRITICAL)

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import sqlite3
import re
import statistics
import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver

import agent.agent as app_agent
from backend.app import app
from db.conversations import delete_session
from eval.queries import ALL_QUERIES, COMPOSE_INDEXES, QUERIES

STRATEGIES = {
    "baseline": "/chat",
    "chaining": "/chat/chain",
    "meta": "/chat/meta",
    "reflection": "/chat/reflect",
}
CRITERIA = ["correct", "complete", "secure_defaults", "valid_syntax"]
CLIENT_ID = "strategy-eval"  # keeps eval sessions out of the UI's conversation list
STREAM_ERROR = "[Error: something went wrong while generating the response."

EVAL_DIR = Path(__file__).parent
RESULTS_DIR = EVAL_DIR / "results"
JUDGE_PROMPT = (EVAL_DIR / "judge_prompt.txt").read_text()
# Web search and README chunks can be long; cap what the judge sees.
MAX_REFERENCE_CHARS = 60_000
JUDGE_WORKERS = int(os.environ.get("JUDGE_WORKERS", "4"))


class TokenCounter(BaseCallbackHandler):
    """Sums usage over every LLM call the app makes during one request, and
    keeps the raw output of every tool call."""

    def reset(self):
        self.prompt = self.completion = self.calls = 0
        self.missing = False
        self.tool_names = {}
        self.tool_outputs = []

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self.tool_names[run_id] = serialized.get("name")

    def on_tool_end(self, output, *, run_id, **kwargs):
        content = getattr(output, "content", output)
        self.tool_outputs.append({"tool": self.tool_names.get(run_id), "output": str(content)})

    def on_llm_end(self, response, **kwargs):
        self.calls += 1
        usage = None
        gen = response.generations[0][0] if response.generations and response.generations[0] else None
        if gen is not None and getattr(gen, "message", None) is not None:
            usage = gen.message.usage_metadata
        if usage:
            self.prompt += usage.get("input_tokens", 0)
            self.completion += usage.get("output_tokens", 0)
        else:
            self.missing = True


counter = TokenCounter()
counter.reset()
# Same llm object backs the ReAct agent and the chain/meta/reflect calls.
app_agent.llm.callbacks = [counter]
# /chat streams; ask the provider to include usage in the stream.
app_agent.llm.stream_usage = True
for t in app_agent.tools:
    t.callbacks = [counter]

judge_llm = ChatOpenAI(
    base_url=os.environ.get("JUDGE_BASE_URL", os.environ["MODEL_BASE_URL"]),
    api_key=os.environ.get("JUDGE_API_KEY", os.environ["MODEL_API_KEY"]),
    model=os.environ.get("JUDGE_MODEL_NAME", os.environ["MODEL_NAME"]),
    temperature=0,
    timeout=120,
    max_retries=2,
    extra_body=json.loads(os.environ.get("JUDGE_EXTRA_BODY", '{"enable_thinking": false}')),
)

client = TestClient(app, raise_server_exceptions=False)


def call_endpoint(path, query):
    session_id = f"strategy-eval-{uuid.uuid4().hex[:12]}"
    counter.reset()
    t = time.perf_counter()
    r = client.post(path, json={"message": query, "session_id": session_id, "client_id": CLIENT_ID})
    latency = time.perf_counter() - t

    error = None
    if r.status_code != 200:
        response, error = "", f"HTTP {r.status_code}"
    elif path == "/chat":
        response = r.text
        if STREAM_ERROR in response:
            error = "stream error"
    else:
        response = r.json()["response"]
    if not error and not response.strip():
        error = "empty response"
    delete_session(session_id)

    return {
        "session_id": session_id,
        "latency_s": round(latency, 3),
        "llm_calls": counter.calls,
        # None when the provider did not report usage for some call.
        "prompt_tokens": None if counter.missing else counter.prompt,
        "completion_tokens": None if counter.missing else counter.completion,
        "response": response,
        "tool_outputs": list(counter.tool_outputs),
        "error": error,
    }


def tool_outputs_from_checkpoint(saver, session_id):
    cp = saver.get_tuple({"configurable": {"thread_id": session_id}})
    if not cp:
        return []
    msgs = cp.checkpoint["channel_values"].get("messages", [])
    return [{"tool": m.name, "output": str(m.content)} for m in msgs if m.type == "tool"]


def format_reference(tool_outputs):
    if not tool_outputs:
        return "(none: the assistant called no tools for this answer)", False
    text = "\n\n".join(f"[{i + 1}] {t['tool']}:\n{t['output']}" for i, t in enumerate(tool_outputs))
    if len(text) > MAX_REFERENCE_CHARS:
        return text[:MAX_REFERENCE_CHARS] + "\n[...reference truncated...]", True
    return text, False


def judge(query, response, tool_outputs):
    reference, _ = format_reference(tool_outputs)
    prompt = JUDGE_PROMPT.format(query=query, reference=reference, response=response)
    raw = ""
    for _ in range(2):
        raw = judge_llm.invoke([HumanMessage(content=prompt)]).content
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            continue
        try:
            scores = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        if all(scores.get(c) is None or scores[c] in (1, 2, 3, 4, 5) for c in CRITERIA):
            vals = [scores[c] for c in CRITERIA if scores.get(c) is not None]
            scores["overall"] = round(sum(vals) / len(vals), 3) if vals else None
            return scores, None
    return None, f"unparseable judge output: {raw[:200]}"


def mean_std(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None, 0
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0), len(xs)


def fmt(xs, digits=2):
    m, s, n = mean_std(xs)
    return "—" if m is None else f"{m:.{digits}f} ± {s:.{digits}f}"


def sign_test(better, worse):
    n, k = better + worse, min(better, worse)
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def summarize(meta, rows):
    ok = [r for r in rows if not r["error"]]
    lines = [
        f"# Strategy eval — {meta['timestamp']}",
        "",
        f"- Model under test: `{meta['model']}`; judge: `{meta['judge_model']}`"
        + (f" (re-judged from `{meta['rejudged_from']}`)" if meta.get("rejudged_from") else ""),
        f"- {meta['n_queries']} queries × {meta['runs']} runs per strategy; LLM cache disabled",
        f"- Raw rows: `{meta['results_file']}`",
        "- Values are mean ± sample std over all successful calls for that strategy "
        "(n = queries × runs, minus errors). Judge scores are 1–5.",
        "",
        "| Strategy | n ok / total | Latency (s) | Prompt tokens | Completion tokens | LLM calls | Judge overall | Correct | Complete | Secure defaults | Valid syntax |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in meta["strategies"]:
        srows = [r for r in rows if r["strategy"] == s]
        sok = [r for r in ok if r["strategy"] == s]
        sc = [r["judge"] for r in sok if r["judge"]]
        lines.append(
            f"| {s} | {len(sok)}/{len(srows)} "
            f"| {fmt([r['latency_s'] for r in sok], 1)} "
            f"| {fmt([r['prompt_tokens'] for r in sok], 0)} "
            f"| {fmt([r['completion_tokens'] for r in sok], 0)} "
            f"| {fmt([r['llm_calls'] for r in sok], 1)} "
            f"| {fmt([j['overall'] for j in sc])} "
            + " ".join(f"| {fmt([j.get(c) for j in sc])}" for c in CRITERIA)
            + " |"
        )

    compose_rows = [r for r in ok if r["query_index"] in COMPOSE_INDEXES and r["judge"]]
    if compose_rows:
        n_compose = len({r["query_index"] for r in compose_rows})
        lines += ["", f"## Compose-generation queries only ({n_compose} queries)", "",
                  "| Strategy | n | Judge overall | Correct | Complete | Secure defaults | Valid syntax |",
                  "|---|---|---|---|---|---|---|"]
        for s in meta["strategies"]:
            sc = [r["judge"] for r in compose_rows if r["strategy"] == s]
            lines.append(f"| {s} | {len(sc)} | {fmt([j['overall'] for j in sc])} "
                         + " ".join(f"| {fmt([j.get(c) for j in sc])}" for c in CRITERIA) + " |")

    lines += ["", "## Judge overall score per query (mean ± std over runs)", ""]
    lines.append("| # | Query | " + " | ".join(meta["strategies"]) + " |")
    lines.append("|---|---|" + "---|" * len(meta["strategies"]))
    for qi in sorted({r["query_index"] for r in rows}):
        q = ALL_QUERIES[qi]
        cells = []
        for s in meta["strategies"]:
            cells.append(fmt([r["judge"]["overall"] for r in ok
                              if r["strategy"] == s and r["query_index"] == qi and r["judge"]]))
        lines.append(f"| {qi + 1} | {q[:50]} | " + " | ".join(cells) + " |")

    lines += ["", "## Paired comparison per query", "",
              "Each query's mean overall score over runs, compared between two strategies on the same "
              "queries. Sign test: exact two-sided binomial on better vs worse, ties dropped; "
              "p-values are not corrected for the number of comparisons.", "",
              "| A vs B | Queries | Mean diff (A − B) | A better | A worse | Tie | Sign test p |",
              "|---|---|---|---|---|---|---|"]
    per_query = {}
    for r in ok:
        if r["judge"] and r["judge"]["overall"] is not None:
            per_query.setdefault((r["strategy"], r["query_index"]), []).append(r["judge"]["overall"])
    strategies = meta["strategies"]
    for i, a in enumerate(strategies):
        for b in strategies[i + 1:]:
            qs = sorted(qi for (s, qi) in per_query if s == a and (b, qi) in per_query)
            diffs = [statistics.mean(per_query[(a, qi)]) - statistics.mean(per_query[(b, qi)]) for qi in qs]
            if not diffs:
                continue
            better, worse = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
            lines.append(f"| {a} vs {b} | {len(diffs)} | {statistics.mean(diffs):+.2f} | {better} | {worse} "
                         f"| {len(diffs) - better - worse} | {sign_test(better, worse):.3f} |")

    errors = [r for r in rows if r["error"] or r["judge_error"]]
    if errors:
        lines += ["", "## Errors", ""]
        for r in errors:
            lines.append(f"- {r['strategy']} q{r['query_index'] + 1} run {r['run']}: {r['error'] or r['judge_error']}")
    return "\n".join(lines) + "\n"


def judge_row(row):
    row["judge"], row["judge_error"] = None, None
    if row["error"]:
        return
    try:
        row["judge"], row["judge_error"] = judge(row["query"], row["response"], row["tool_outputs"])
    except Exception as e:
        row["judge_error"] = f"judge call failed: {type(e).__name__}"


def judge_only(path, limit, strategies):
    src = Path(path)
    data = json.loads(src.read_text())
    saver = SqliteSaver(sqlite3.connect("conversation_history.db", check_same_thread=False))
    judge_model = judge_llm.model_name
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = judge_model.split("-")[0]
    json_path = RESULTS_DIR / f"strategy_eval_{ts}_judged-{tag}.json"
    md_path = RESULTS_DIR / f"strategy_eval_{ts}_judged-{tag}.md"
    meta = dict(data["meta"], judge_model=judge_model, rejudged_from=str(src),
                results_file=str(json_path.relative_to(EVAL_DIR.parent)), rejudged_at=ts,
                strategies=[s for s in data["meta"]["strategies"] if s in strategies])
    rows = [r for r in data["rows"]
            if r["strategy"] in strategies and (limit is None or r["query_index"] < limit)]

    for i, row in enumerate(rows, 1):
        if "tool_outputs" not in row:
            row["tool_outputs"] = tool_outputs_from_checkpoint(saver, row["session_id"])
        row["reference_truncated"] = format_reference(row["tool_outputs"])[1]
        judge_row(row)
        score = row["judge"]["overall"] if row["judge"] else "—"
        print(f"[{i:>3}/{len(rows)}] run {row['run']} q{row['query_index'] + 1:>2} {row['strategy']:<10} "
              f"tools {len(row['tool_outputs'])}  judge {score}  {row['error'] or row['judge_error'] or ''}", flush=True)
        json_path.write_text(json.dumps({"meta": meta, "rows": rows}, indent=2, ensure_ascii=False))

    summary = summarize(meta, rows)
    md_path.write_text(summary)
    print("\n" + summary)
    print(f"Wrote {json_path}\nWrote {md_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--limit", type=int, default=None, help="only the first N queries")
    p.add_argument("--strategies", default=",".join(STRATEGIES))
    p.add_argument("--queries", choices=["default", "all"], default="default",
                   help="default: the 20 benchmark queries; all: plus 10 extra compose queries")
    p.add_argument("--judge-only", metavar="RESULTS_JSON",
                   help="re-score an earlier run's rows with the current judge; no generation")
    p.add_argument("--resume", metavar="RESULTS_JSON",
                   help="continue a stopped run in the same file, keeping its settings")
    args = p.parse_args()
    if args.judge_only:
        judge_only(args.judge_only, args.limit, args.strategies.split(","))
        return

    if args.resume:
        json_path = Path(args.resume)
        data = json.loads(json_path.read_text())
        meta, rows = data["meta"], data["rows"]
        strategies, runs = meta["strategies"], meta["runs"]
        queries = (QUERIES if meta["n_queries"] <= len(QUERIES) else ALL_QUERIES)[: meta["n_queries"]]
    else:
        strategies, runs = args.strategies.split(","), args.runs
        queries = (QUERIES if args.queries == "default" else ALL_QUERIES)[: args.limit]
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        RESULTS_DIR.mkdir(exist_ok=True)
        json_path = RESULTS_DIR / f"strategy_eval_{ts}.json"
        meta = {
            "timestamp": ts,
            "model": os.environ["MODEL_NAME"],
            "judge_model": judge_llm.model_name,
            "runs": runs,
            "n_queries": len(queries),
            "strategies": strategies,
            "results_file": str(json_path.relative_to(EVAL_DIR.parent)),
            "judge_prompt_file": "eval/judge_prompt.txt",
        }
        rows = []
    md_path = json_path.with_suffix(".md")
    total = runs * len(queries) * len(strategies)
    done = {(r["run"], r["query_index"], r["strategy"]) for r in rows}

    def save():
        json_path.write_text(json.dumps({"meta": meta, "rows": rows}, indent=2, ensure_ascii=False))

    def judge_and_report(row, label):
        judge_row(row)
        score = row["judge"]["overall"] if row["judge"] else "—"
        print(f"      judged {label}: {score}  {row['judge_error'] or ''}", flush=True)

    pool = ThreadPoolExecutor(JUDGE_WORKERS)
    # Rows from a stopped run that were generated but never judged.
    for r in rows:
        if not r["error"] and r.get("judge") is None and not r.get("judge_error"):
            pool.submit(judge_and_report, r, f"run {r['run']} q{r['query_index'] + 1} {r['strategy']}")

    # Runs outermost, strategies innermost, so provider slowdowns over the
    # session hit every strategy roughly equally.
    for run in range(1, runs + 1):
        for qi, query in enumerate(queries):
            for s in strategies:
                if (run, qi, s) in done:
                    continue
                row = {"run": run, "query_index": qi, "query": query, "strategy": s, "endpoint": STRATEGIES[s]}
                row.update(call_endpoint(STRATEGIES[s], query))
                # Set before the row is shared, so the judge thread only
                # replaces values and save() never sees the dict change size.
                row["judge"], row["judge_error"] = None, None
                rows.append(row)
                label = f"run {run} q{qi + 1} {s}"
                print(f"[{len(rows):>3}/{total}] {label:<20} {row['latency_s']:6.1f}s  "
                      f"tok {row['prompt_tokens']}/{row['completion_tokens']}  {row['error'] or ''}", flush=True)
                if not row["error"]:
                    pool.submit(judge_and_report, row, label)
                # Rewrite after every call so a crash keeps what finished.
                save()

    pool.shutdown(wait=True)
    save()
    summary = summarize(meta, rows)
    md_path.write_text(summary)
    print("\n" + summary)
    print(f"Wrote {json_path}\nWrote {md_path}")


if __name__ == "__main__":
    main()

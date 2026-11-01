"""Semantic-cache threshold sweep.

Puts the 20 benchmark queries into a throwaway in-memory Chroma collection
(same embedding function and distance space as rag/semantic_cache.py), then
looks up each paraphrase and each unrelated query and records the nearest
distance. For each threshold it reports:

  - paraphrase hit rate: paraphrase lands under the threshold AND its nearest
    entry is the query it paraphrases
  - paraphrase wrong hits: under the threshold but nearest is a different query
  - false-hit rate: unrelated query lands under the threshold (any entry)

No LLM calls: a hit/miss decision depends only on distances, so responses are
not needed. The real response_cache collection is not touched.

Chroma's "l2" space reports squared L2 distance; the thresholds here are on
that same scale, which is what rag/semantic_cache.py compares against.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from eval.queries import QUERIES, PARAPHRASED_QUERIES, UNRELATED_QUERIES

RESULTS_DIR = Path(__file__).parent / "results"
THRESHOLDS = [0.15, 0.25, 0.35, 0.5]


def nearest(collection, texts):
    res = collection.query(query_texts=texts, n_results=1)
    return [(int(ids[0]), dists[0]) for ids, dists in zip(res["ids"], res["distances"])]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--thresholds", default=",".join(map(str, THRESHOLDS)))
    thresholds = [float(t) for t in p.parse_args().thresholds.split(",")]

    col = chromadb.EphemeralClient().create_collection(
        name="sweep", embedding_function=DefaultEmbeddingFunction(), configuration={"hnsw": {"space": "l2"}})
    col.add(ids=[str(i) for i in range(len(QUERIES))], documents=QUERIES)

    para = nearest(col, PARAPHRASED_QUERIES)
    unrel = nearest(col, UNRELATED_QUERIES)

    rows = []
    for i, (nn, d) in enumerate(para):
        rows.append({"kind": "paraphrase", "query": PARAPHRASED_QUERIES[i], "target_index": i,
                     "nearest_index": nn, "nearest_query": QUERIES[nn], "distance": round(d, 4)})
    for i, (nn, d) in enumerate(unrel):
        rows.append({"kind": "unrelated", "query": UNRELATED_QUERIES[i], "target_index": None,
                     "nearest_index": nn, "nearest_query": QUERIES[nn], "distance": round(d, 4)})

    summary = []
    for t in thresholds:
        p_hit = sum(1 for i, (nn, d) in enumerate(para) if d < t and nn == i)
        p_wrong = sum(1 for i, (nn, d) in enumerate(para) if d < t and nn != i)
        u_hit = sum(1 for _, d in unrel if d < t)
        summary.append({"threshold": t,
                        "paraphrase_hits": p_hit, "paraphrase_wrong_hits": p_wrong, "paraphrase_total": len(para),
                        "unrelated_false_hits": u_hit, "unrelated_total": len(unrel)})

    print(f"{'Threshold':>9}  {'Paraphrase hit':>15}  {'Para wrong hit':>15}  {'Unrelated false hit':>20}")
    for s in summary:
        print(f"{s['threshold']:>9.2f}  "
              f"{s['paraphrase_hits']:>3}/{s['paraphrase_total']} {100 * s['paraphrase_hits'] / s['paraphrase_total']:>5.0f}%  "
              f"{s['paraphrase_wrong_hits']:>3}/{s['paraphrase_total']} {100 * s['paraphrase_wrong_hits'] / s['paraphrase_total']:>5.0f}%  "
              f"{s['unrelated_false_hits']:>8}/{s['unrelated_total']} {100 * s['unrelated_false_hits'] / s['unrelated_total']:>5.0f}%")

    print("\nClosest unrelated queries:")
    for r in sorted((r for r in rows if r["kind"] == "unrelated"), key=lambda r: r["distance"])[:5]:
        print(f"  {r['distance']:.3f}  {r['query'][:50]!r} -> {r['nearest_query'][:50]!r}")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"semantic_cache_sweep_{ts}.json"
    out.write_text(json.dumps({
        "meta": {"timestamp": ts, "distance": "chroma l2 (squared L2)", "embedding": "chromadb DefaultEmbeddingFunction",
                 "thresholds": thresholds, "n_paraphrase": len(para), "n_unrelated": len(unrel)},
        "summary": summary, "rows": rows,
    }, indent=2, ensure_ascii=False))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

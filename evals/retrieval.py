# Retrieval alone, with no model answering: for each golden question, where the Publication 17
# sections that answer it come back in each index. A chunk can hold parts of several sections, so it
# counts as a hit for any of them.
#
# Usage: uv run python -m evals.retrieval [--pinecone]   (writes evals/results/retrieval[-pinecone].md and .json)

import json
import statistics
import sys
import time
from pathlib import Path

from llama_index.core.schema import NodeWithScore, QueryBundle

from tax import golden, index

K = 10
OUT = Path("evals/results")


def rank(results: list[NodeWithScore], wanted: list[str]) -> int | None:
    """The 1-based rank of the first node that holds one of the wanted sections"""
    return next((i for i, r in enumerate(results, 1) if set(index.sections(r)) & set(wanted)), None)


def run(corpus: str, items: list[golden.Item], cache: index.EmbeddingCache, store: str) -> list[dict]:
    retriever = index.STORES[store](corpus).as_retriever(similarity_top_k=K)
    vectors = cache.embed([item.question for item in items], kind="query")
    rows = []
    for item, vector in zip(items, vectors):
        start = time.perf_counter()
        results = retriever.retrieve(QueryBundle(query_str=item.question, embedding=vector))
        ms = (time.perf_counter() - start) * 1000
        rows.append(
            {
                "id": item.id,
                "kind": item.kind,
                "rank": rank(results, item.expected) if item.expected else None,
                "hop_rank": rank(results, [item.hop]) if item.hop else None,
                "top_score": results[0].score,
                "retrieved": [index.sections(r) for r in results],
                "chars": [len(r.node.text) for r in results[:5]],
                "ms": ms,
            }
        )
    return rows


def summary(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["kind"] != "out-of-scope"]
    hit = lambda k, key="rank", rs=scored: sum(1 for r in rs if r[key] and r[key] <= k) / len(rs)
    multi = [r for r in rows if r["kind"] == "multi-hop"]
    return {
        "hit@1": hit(1),
        "hit@5": hit(5),
        "mrr@10": sum(1 / r["rank"] for r in scored if r["rank"]) / len(scored),
        "by_kind": {k: hit(5, rs=[r for r in scored if r["kind"] == k]) for k in dict.fromkeys(r["kind"] for r in scored)},
        "multi_hop_second@5": hit(5, "hop_rank", multi),
        "multi_hop_both@5": sum(1 for r in multi if r["rank"] and r["rank"] <= 5 and r["hop_rank"] and r["hop_rank"] <= 5) / len(multi),
        "hard_hop_second@5": hit(5, "hop_rank", [r for r in rows if r["kind"] == "hard-hop"]),
        "top_score_in_scope": statistics.median(r["top_score"] for r in scored),
        "top_score_out_of_scope": statistics.median(r["top_score"] for r in rows if r["kind"] == "out-of-scope"),
        "context_chars@5": statistics.median(sum(r["chars"]) for r in rows),
        "query_ms": statistics.median(r["ms"] for r in rows),
    }


def main():
    store = "pinecone" if "--pinecone" in sys.argv else "chroma"
    items, cache = golden.load(), index.EmbeddingCache()
    results = {corpus: run(corpus, items, cache, store) for corpus in index.CORPORA}
    sums = {corpus: summary(rows) for corpus, rows in results.items()}
    pct = lambda x: f"{x * 100:.0f}%"
    kinds = list(next(iter(sums.values()))["by_kind"])
    lines = [
        f"# Retrieval: {index.EMBED_MODEL} in {store}, top {K}",
        "",
        f"{len(items)} golden questions, {sum(i.kind != 'out-of-scope' for i in items)} with an answer in the publication.",
        "",
        "| Index | hit@1 | hit@5 | MRR@10 | " + " | ".join(f"hit@5 {k}" for k in kinds) + " | Multi-hop, second section @5 | Both @5 | Hard-hop, second section @5 | Context at 5 (chars) | Median query |",
        "|---|" + "---|" * (8 + len(kinds)),
        *(
            f"| {c} | {pct(s['hit@1'])} | {pct(s['hit@5'])} | {s['mrr@10']:.2f} | "
            + " | ".join(pct(s["by_kind"][k]) for k in kinds)
            + f" | {pct(s['multi_hop_second@5'])} | {pct(s['multi_hop_both@5'])} | {pct(s['hard_hop_second@5'])} | {s['context_chars@5']:,.0f} | {s['query_ms']:.0f} ms |"
            for c, s in sums.items()
        ),
        "",
        "Median similarity of the top result: "
        + "; ".join(f"{c}: {s['top_score_in_scope']:.3f} in scope, {s['top_score_out_of_scope']:.3f} out of scope" for c, s in sums.items())
        + ".",
        "",
        "## Misses at 5",
        "",
        "| Question | Kind | Expected | " + " | ".join(f"{c} rank" for c in results) + " |",
        "|---|---|---|" + "---|" * len(results),
    ]
    by_id = {i.id: i for i in items}
    for n, item in enumerate(items):
        ranks = [results[c][n]["rank"] for c in results]
        if item.expected and any(not r or r > 5 for r in ranks):
            lines.append(f"| {item.id}: {item.question} | {item.kind} | {', '.join(by_id[item.id].expected)} | " + " | ".join(str(r or "-") for r in ranks) + " |")
    OUT.mkdir(parents=True, exist_ok=True)
    name = "retrieval" + ("-pinecone" if store == "pinecone" else "")
    (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / f"{name}.json").write_text(json.dumps({"summary": sums, "results": results}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

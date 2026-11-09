# Every golden question through each system, scored by code: the fact in the answer, the citations,
# the refusals, and the cost. Answers are cached per system and question in storage/answers, keyed
# by what the model is given (model, prompt, top k, step limit), so changing the scoring doesn't ask
# again; --fresh does, after a change to the tools' code. With PHOENIX_COLLECTOR_ENDPOINT set, every
# question asked is traced to Phoenix; evals/phoenix.py logs the cached runs there as experiments.
#
# Usage: uv run python -m evals.run [--fresh] [--only agent]   (writes evals/results/run.md and .json)

import hashlib
import json
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path

from openinference.instrumentation import using_attributes

from tax import agent, answer, golden, index, rag, tracing

OUT = Path("evals/results")
CACHE = Path("storage/answers")


def systems() -> dict:
    # Built lazily: each loads its index, and the agent its sections
    return {
        "rag-chunks": lambda: rag.RAG("chunks"),
        "rag-sections": lambda: rag.RAG("sections"),
        "agent": lambda: agent.Agent("sections").ask,
    }


def version(name: str) -> str:
    """Changes when what the model is given does, so the cache doesn't serve stale answers"""
    given = [answer.LLM_MODEL, index.EMBED_MODEL] + ([answer.SYSTEM, rag.K] if name.startswith("rag") else [agent.INSTRUCTIONS, agent.K, agent.MAX_TOOL_CALLS])
    return hashlib.sha1(repr(given).encode()).hexdigest()[:10]


def ask(fn, question: str) -> answer.Answer:
    """One answer, waiting out the free tier's per-minute limits"""
    for attempt in range(6):
        try:
            return fn(question)
        except Exception as error:
            message = repr(error) + repr(error.__cause__)
            if "RESOURCE_EXHAUSTED" not in message and "429" not in message:
                raise
            if "PerDay" in message:
                sys.exit(f"The free tier's daily limit is used up; cached answers are kept. {message[:300]}")
            print(f"  rate limited, waiting {30 * (attempt + 1)}s", flush=True)
            time.sleep(30 * (attempt + 1))
    raise RuntimeError("still rate limited")


def run(name: str, make, items: list[golden.Item], fresh: bool) -> list[dict]:
    path = CACHE / f"{name}-{version(name)}.jsonl"
    cached = {} if fresh or not path.exists() else {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}
    fn, rows = None, []
    for item in items:
        if item.id not in cached:
            fn = fn or make()
            # Traced, with PHOENIX_COLLECTOR_ENDPOINT set, under the system and the golden id
            with using_attributes(session_id=f"{name}-{version(name)}", metadata={"system": name, "id": item.id, "kind": item.kind}, tags=[name, item.kind]):
                row = {"id": item.id, **asdict(ask(fn, item.question))}
            CACHE.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            cached[item.id] = row
            print(f"{name} {item.id}: {row['ms']} ms, {len(row['tools'])} tool calls", flush=True)
        rows.append(score(item, cached[item.id]))
    return rows


def score(item: golden.Item, row: dict) -> dict:
    in_scope = item.kind != "out-of-scope"
    return {
        **row,
        "refused": answer.refused(row["text"], row["cited"]),
        "kind": item.kind,
        "fact": item.stated(row["text"]) if in_scope else None,
        "refusal_right": answer.refused(row["text"], row["cited"]) != in_scope,
        "cites_expected": bool(set(row["cited"]) & set(item.expected)) if in_scope else None,
        "found_expected": bool(set(row["seen"]) & set(item.expected)) if in_scope else None,
    }


def summary(rows: list[dict]) -> dict:
    scope = [r for r in rows if r["kind"] != "out-of-scope"]
    out = [r for r in rows if r["kind"] == "out-of-scope"]
    share = lambda rs, key: sum(1 for r in rs if r[key]) / len(rs)
    return {
        "fact": share(scope, "fact"),
        "fact_by_kind": {k: share([r for r in scope if r["kind"] == k], "fact") for k in dict.fromkeys(r["kind"] for r in scope)},
        "cites_expected": share(scope, "cites_expected"),
        "dropped": sum(len(r["dropped"]) for r in rows),
        "refused_out_of_scope": share(out, "refused"),
        "refused_in_scope": share(scope, "refused"),
        "calls": statistics.mean(r["calls"] for r in rows),
        "tool_calls": statistics.mean(len(r["tools"]) for r in rows),
        "tokens": statistics.mean(r["tokens"] for r in rows),
        "ms_median": statistics.median(r["ms"] for r in rows),
    }


def report(items: list[golden.Item], results: dict[str, list[dict]]) -> str:
    sums = {name: summary(rows) for name, rows in results.items()}
    pct = lambda x: f"{x * 100:.0f}%"
    kinds = list(next(iter(sums.values()))["fact_by_kind"])
    lines = [
        f"# Golden set: {len(items)} questions, {answer.LLM_MODEL}",
        "",
        "| System | Fact right | " + " | ".join(f"Fact, {k}" for k in kinds) + " | Cites a labeled section | Citations dropped | Refuses out of scope | Refuses in scope | Model calls | Tool calls | Tokens | Median latency |",
        "|---|" + "---|" * (9 + len(kinds)),
        *(
            f"| {n} | {pct(s['fact'])} | " + " | ".join(pct(s["fact_by_kind"][k]) for k in kinds)
            + f" | {pct(s['cites_expected'])} | {s['dropped']} | {pct(s['refused_out_of_scope'])} | {pct(s['refused_in_scope'])}"
            + f" | {s['calls']:.2f} | {s['tool_calls']:.2f} | {s['tokens']:,.0f} | {s['ms_median'] / 1000:.1f} s |"
            for n, s in sums.items()
        ),
        "",
        "Means per question, except latency. A fact is right when the answer contains it, ignoring case and spaces.",
        "",
        "## Every wrong answer",
    ]
    by_id = {i.id: i for i in items}
    for name, rows in results.items():
        wrong = [r for r in rows if r["fact"] is False or not r["refusal_right"]]
        lines += ["", f"### {name}: {len(wrong)}", ""]
        for r in wrong:
            item = by_id[r["id"]]
            why = "refused" if r["refused"] else ("answered" if item.kind == "out-of-scope" else f"no \"{item.fact}\"")
            tools = "; ".join(f"{t['name']}({', '.join(map(str, t['args'].values()))})" for t in r["tools"])
            lines.append(f"- **{r['id']}** ({why}) {item.question}  \n  Expected {item.expected}, found {r['found_expected']}, cited {r['cited']}" + (f", tools: {tools}" if tools else "") + f"  \n  > {r['text'][:300].replace(chr(10), ' ')}")
    return "\n".join(lines) + "\n"


def main():
    tracing.trace_to_phoenix()
    items = golden.load()
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    results = {name: run(name, make, items, "--fresh" in sys.argv) for name, make in systems().items() if not only or name == only}
    text = report(items, results)
    suffix = f"-{only}" if only else ""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"run{suffix}.md").write_text(text, encoding="utf-8")
    (OUT / f"run{suffix}.json").write_text(json.dumps({"summary": {n: summary(r) for n, r in results.items()}, "results": results}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()

# Logs the cached eval answers to Phoenix as experiments on one dataset, the golden set, so the
# systems can be compared question by question: the fact, the refusal, the citations and tool
# calls, with each answer and its tokens as the run's output. No model is called: the answers come from storage/answers, written by evals/run.py,
# and are scored with the same code. A system with no cached answers for the current prompts is
# skipped; run evals.run first.
#
# Usage: uv run python -m evals.phoenix [--only agent]   (Phoenix at PHOENIX_COLLECTOR_ENDPOINT,
# http://localhost:6006 by default)

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx

from evals import run
from tax import golden

PHOENIX = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006").rstrip("/")
DATASET = "irs-golden"


def api(client: httpx.Client, path: str, body: dict | None = None) -> dict:
    response = client.post(path, json=body) if body is not None else client.get(path)
    if response.is_error:
        sys.exit(f"Phoenix answered {response.status_code} to {path}: {response.text[:300]}")
    return response.json()


def dataset(client: httpx.Client, items: list[golden.Item]) -> tuple[str, dict[str, str]]:
    """The golden set as a dataset, created the first time, and its example ids by golden id"""
    found = api(client, f"/v1/datasets?name={DATASET}")["data"]
    id = next((d["id"] for d in found if d["name"] == DATASET), None)
    if not id:
        id = api(client, "/v1/datasets/upload?sync=true", {
            "action": "create",
            "name": DATASET,
            "description": "Questions about 2025 U.S. federal income tax with the Publication 17 sections that answer them and a fact the answer must contain (evals/golden.json)",
            "inputs": [{"id": i.id, "question": i.question, "kind": i.kind} for i in items],
            "outputs": [{"expected": i.expected, "fact": i.fact, "also": i.also} for i in items],
            "metadata": [{"kind": i.kind} for i in items],
        })["data"]["dataset_id"]
    examples = api(client, f"/v1/datasets/{id}/examples")["data"]["examples"]
    return id, {e["input"]["id"]: e["id"] for e in examples}


def evaluations(row: dict) -> list[dict]:
    yes = lambda name, value, explanation=None: {"name": name, "score": float(value), "label": "yes" if value else "no", "explanation": explanation}
    results = [yes("refusal right", row["refusal_right"], "refused" if row["refused"] else "answered")]
    if row["fact"] is not None:
        results += [
            yes("fact", row["fact"]),
            yes("cites a labeled section", row["cites_expected"], f"cited {row['cited']}"),
            yes("retrieved or read a labeled section", row["found_expected"]),
        ]
    tools = "; ".join(f"{t['name']}({', '.join(map(str, t['args'].values()))})" for t in row["tools"])
    # Tokens are in the output: on the same chart as the yes/no scores they flatten them
    return results + [{"name": "tool calls", "score": len(row["tools"]), "explanation": tools or None}]


def main():
    items = golden.load()
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    with httpx.Client(base_url=PHOENIX, timeout=30) as client:
        id, examples = dataset(client, items)
        for name in run.systems():
            if only and name != only:
                continue
            path = run.CACHE / f"{name}-{run.version(name)}.jsonl"
            if not path.exists():
                print(f"{name}: no cached answers for the current prompts, skipped")
                continue
            cached = {r["id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}
            experiment = api(client, f"/v1/datasets/{id}/experiments", {"name": f"{name}-{run.version(name)}", "metadata": {"system": name, "version": run.version(name)}, "repetitions": 1})["data"]
            logged = 0
            for item in items:
                if item.id not in cached:
                    continue
                row = run.score(item, cached[item.id])
                end = datetime.now(timezone.utc)
                times = {"start_time": (end - timedelta(milliseconds=row["ms"])).isoformat(), "end_time": end.isoformat()}
                output = {k: row[k] for k in ("text", "cited", "dropped", "refused", "seen", "tools", "calls", "tokens")}
                created = api(client, f"/v1/experiments/{experiment['id']}/runs", {"dataset_example_id": examples[item.id], "output": output, "repetition_number": 1, **times, "error": None})["data"]
                for result in evaluations(row):
                    name_, rest = result.pop("name"), {k: v for k, v in result.items() if v is not None}
                    api(client, "/v1/experiment_evaluations", {"experiment_run_id": created["id"], "name": name_, "annotator_kind": "CODE", **times, "result": rest})
                logged += 1
            print(f"{name}: logged {logged} of {len(items)} questions")
    print(f"{PHOENIX}/datasets/{id}/experiments")


if __name__ == "__main__":
    main()

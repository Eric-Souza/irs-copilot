# What each answer is scored as in Phoenix, from a cached row. No Phoenix.

from evals import phoenix, run
from tax import golden

ITEM = golden.Item(id="x01", question="How much can they earn?", kind="number", expected=["3.17"], fact="5,200")


def row(text: str, cited: list[str], tools=()) -> dict:
    cached = {"id": "x01", "text": text, "cited": cited, "dropped": [], "refused": False, "seen": ["3.17"], "calls": 1, "tokens": 10, "tools": list(tools), "ms": 5}
    return run.score(ITEM, cached)


def test_a_right_answer_scores_yes_on_everything():
    results = {r["name"]: r for r in phoenix.evaluations(row("Less than $5,200 [3.17].", ["3.17"]))}
    assert [results[n]["label"] for n in ("refusal right", "fact", "cites a labeled section", "retrieved or read a labeled section")] == ["yes"] * 4
    assert results["tool calls"]["score"] == 0


def test_tool_calls_are_explained():
    tools = [{"name": "read_section", "args": {"section": "3.17"}}]
    results = {r["name"]: r for r in phoenix.evaluations(row("I don't know.", [], tools))}
    assert results["fact"]["label"] == "no" and results["tool calls"] == {"name": "tool calls", "score": 1, "explanation": "read_section(3.17)"}


def test_an_out_of_scope_question_is_scored_on_the_refusal_alone():
    item = golden.Item(id="o01", question="What about California?", kind="out-of-scope")
    cached = {"id": "o01", "text": run.answer.REFUSAL, "cited": [], "dropped": [], "refused": True, "seen": [], "calls": 1, "tokens": 10, "tools": [], "ms": 5}
    assert [r["name"] for r in phoenix.evaluations(run.score(item, cached))] == ["refusal right", "tool calls"]

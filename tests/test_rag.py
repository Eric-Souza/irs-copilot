# The baseline with a fake search and model, and the eval's scoring and report on cached rows.

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.schema import NodeWithScore, TextNode

from evals import run
from tax import answer, golden, rag


class Model:
    def __init__(self, reply: str):
        self.reply, self.seen = reply, None

    def chat(self, messages):
        self.seen = messages
        return ChatResponse(message=ChatMessage(role="assistant", content=self.reply), raw={"usage_metadata": {"total_token_count": 7}})


def search(query: str) -> list[NodeWithScore]:
    return [NodeWithScore(node=TextNode(text="[3.17] Gross Income Test\nLess than $5,200.", metadata={"section": "3.17"}), score=0.9)]


def test_rag_answers_in_one_call_and_checks_the_citations():
    model = Model("Less than $5,200 [3.17] [3.18].")
    a = rag.RAG(search=search, llm=model)("how much can a qualifying relative earn?")
    assert a.cited == ["3.17"] and a.dropped == ["3.18"] and a.calls == 1 and a.tokens == 7
    assert "--- sections 3.17 ---" in model.seen[1].content and model.seen[0].content == answer.SYSTEM


def row(id: str, text: str, cited: list[str], tools=()) -> dict:
    return {"id": id, "text": text, "cited": cited, "dropped": [], "refused": False, "seen": cited, "calls": 1 + len(tools), "tokens": 100, "tools": list(tools), "ms": 1000}


ITEMS = [
    golden.Item(id="n01", kind="number", question="How much can they earn?", expected=["3.17"], fact="5,200"),
    golden.Item(id="o01", kind="out-of-scope", question="What about California?"),
]


def test_the_report_counts_facts_and_refusals():
    rows = [run.score(ITEMS[0], row("n01", "Less than $5,200 [3.17].", ["3.17"])), run.score(ITEMS[1], row("o01", "California taxes...", []))]
    s = run.summary(rows)
    assert s["fact"] == 1 and s["refused_out_of_scope"] == 0 and s["refused_in_scope"] == 0
    text = run.report(ITEMS, {"agent": rows})
    assert "### agent: 1" in text and "**o01** (answered)" in text

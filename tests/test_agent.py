# The Workflow with a scripted model and a fake search: which tools run, what counts as seen, and
# where the step limit stops it. No model, no index.

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.tools import ToolSelection

from tax import agent, pub17

SECTIONS = {
    "3.14": pub17.Section("3.14", 3, "Dependents", "Qualifying Relative", ["Dependents"], "Four tests must be met. See Gross Income Test, later.", ["3.17"]),
    "3.17": pub17.Section("3.17", 3, "Dependents", "Gross Income Test", ["Dependents", "Qualifying Relative"], "Gross income must be less than $5,200."),
}


def node(id: str) -> NodeWithScore:
    return NodeWithScore(node=TextNode(text=SECTIONS[id].full, metadata={"section": id}), score=0.9)


class Search:
    def __init__(self):
        self.queries = []

    def __call__(self, query: str) -> list[NodeWithScore]:
        self.queries.append(query)
        return [node("3.14")]


class Model:
    """Answers with the scripted replies in order: a list of tool calls, or the final text"""

    def __init__(self, *replies):
        self.replies, self.with_tools, self.seen = list(replies), [], []

    def _next(self, messages) -> ChatResponse:
        self.seen.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, str):
            return ChatResponse(message=ChatMessage(role="assistant", content=reply), raw={"usage_metadata": {"total_token_count": 10}})
        calls = [ToolSelection(tool_id=f"c{i}", tool_name=name, tool_kwargs=args) for i, (name, args) in enumerate(reply)]
        return ChatResponse(message=ChatMessage(role="assistant", content="", additional_kwargs={"tool_calls": calls}), raw={"usage_metadata": {"total_token_count": 10}})

    async def achat_with_tools(self, tools, chat_history, **kwargs):
        self.with_tools.append(True)
        return self._next(chat_history)

    async def achat(self, messages):
        self.with_tools.append(False)
        return self._next(messages)

    def get_tool_calls_from_response(self, response, error_on_no_tool_call=False):
        return response.message.additional_kwargs.get("tool_calls", [])


def make(model: Model) -> tuple[agent.Agent, Search]:
    search = Search()
    return agent.Agent(search=search, llm=model, sections=SECTIONS), search


def test_answers_straight_from_the_retrieved_sections():
    model = Model("Four tests must be met [3.14].")
    bot, search = make(model)
    a = bot.ask("can my mom be my dependent?")
    assert a.cited == ["3.14"] and a.calls == 1 and a.tools == [] and a.tokens == 10
    assert search.queries == ["can my mom be my dependent?"]
    # The model is told where the retrieved section links to
    assert "(links to sections 3.17)" in model.seen[0][1].content


def test_titled_links_name_the_section_they_go_to():
    model = Model([("read_section", {"section": "3.14"})], "Four tests [3.14].")
    agent.Agent(search=Search(), llm=model, sections=SECTIONS, titled_links=True).ask("can my mom be my dependent?")
    assert "(links to sections 3.17 Gross Income Test)" in model.seen[0][1].content
    # And so does a section read with the tool
    assert "(links to sections 3.17 Gross Income Test)" in model.seen[1][-1].content


def test_reading_a_linked_section_makes_it_citable():
    bot, _ = make(Model([("read_section", {"section": "3.17"})], "Under $5,200 [3.17], four tests [3.14]."))
    a = bot.ask("how much can she earn?")
    assert a.cited == ["3.17", "3.14"] and a.dropped == [] and a.calls == 2
    assert a.tools == [{"name": "read_section", "args": {"section": "3.17"}}]


def test_brackets_around_the_section_number_are_ignored():
    model = Model([("read_section", {"section": "[3.17]"})], "Under $5,200 [3.17].")
    bot, _ = make(model)
    assert bot.ask("how much can she earn?").cited == ["3.17"]
    assert model.seen[1][-1].content.startswith("--- section 3.17: Chapter 3. Dependents > Dependents > Qualifying Relative > Gross Income Test ---")


def test_a_citation_to_an_unread_section_is_dropped():
    # 3.17 is only linked from 3.14, never read
    bot, _ = make(Model("Under $5,200 [3.17]."))
    a = bot.ask("how much can she earn?")
    assert a.cited == [] and a.dropped == ["3.17"] and "[3.17]" not in a.text


def test_search_publication_adds_what_it_finds():
    bot, search = make(Model([("search_publication", {"query": "qualifying relative"})], "Yes [3.14]."))
    a = bot.ask("does mom count?")
    assert search.queries == ["does mom count?", "qualifying relative"] and a.cited == ["3.14"]


def test_a_section_that_does_not_exist_is_reported_to_the_model():
    model = Model([("read_section", {"section": "99.9"})], agent.answer.REFUSAL)
    bot, _ = make(model)
    a = bot.ask("what does section 99.9 say?")
    assert a.refused and "There is no section '99.9'" in model.seen[1][-1].content


def test_the_step_limit_forces_an_answer_without_tools():
    loop = [("search_publication", {"query": "again"})]
    model = Model(*[loop] * agent.MAX_TOOL_CALLS, "Yes [3.14].")
    bot, _ = make(model)
    a = bot.ask("does mom count?")
    assert len(a.tools) == agent.MAX_TOOL_CALLS
    assert model.with_tools == [True] * agent.MAX_TOOL_CALLS + [False]
    assert a.calls == agent.MAX_TOOL_CALLS + 1 and a.cited == ["3.14"]


def test_parallel_calls_past_the_limit_are_cut():
    model = Model([("read_section", {"section": "3.17"})] * (agent.MAX_TOOL_CALLS + 2), "Yes [3.17].")
    bot, _ = make(model)
    a = bot.ask("does mom count?")
    assert len(a.tools) == agent.MAX_TOOL_CALLS and model.with_tools == [True, False]

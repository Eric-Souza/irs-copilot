# The agent: a LlamaIndex Workflow that starts from the same top 5 as the baseline, then may search
# again with other words or read the sections the retrieved ones point to ("see Qualifying Relative,
# later"), up to MAX_TOOL_CALLS, before it answers. The citation check is the same as the baseline's.
#
#   start ──> think ──> (tool calls) ──> act ──> think ... ──> answer
#
# Usage: uv run python -m tax.agent "can I claim my mother as a dependent?"

import asyncio
import sys
import time
from dataclasses import dataclass, field

from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.tools import FunctionTool, ToolSelection
from llama_index.core.workflow import Context, Event, StartEvent, StopEvent, Workflow, step

from tax import answer, index, pub17, tracing

K = 5
MAX_TOOL_CALLS = 4
MAX_READ_CHARS = 8000  # the longest section is 29K characters

INSTRUCTIONS = f"""{answer.RULES}

You first get the sections a search found for the question, and you may use the tools, at most {MAX_TOOL_CALLS} calls, before answering:
- read_section(section): the full text of one section, by number. Use it when a section points to another one ("see Qualifying Relative, later", "in chapter 3") and part of the question depends on it, when a section is cut short, or when the question names a section.
- search_publication(query): a new search, with other words, when part of the question doesn't appear in the sections.
Each section you get lists the sections it links to. If the sections already answer every part of the question, answer directly. Before saying the publication doesn't cover something, read the sections they point to or search again. {answer.REFUSE}"""


def search_publication(query: str) -> str:
    """Search IRS Publication 17 (2025) for the sections closest to the query."""
    ...


def read_section(section: str) -> str:
    """The full text of one section of IRS Publication 17 (2025), by its number, like "3.9"."""
    ...


dispatcher = get_dispatcher(__name__)

TOOLS = [FunctionTool.from_defaults(fn=search_publication), FunctionTool.from_defaults(fn=read_section)]


@dataclass
class Run:
    messages: list[ChatMessage]
    seen: list[str]
    start: float = field(default_factory=time.perf_counter)
    calls: int = 0
    tokens: int = 0
    tools: list[dict] = field(default_factory=list)


class Think(Event):
    pass


class Act(Event):
    calls: list[ToolSelection]


class Agent(Workflow):
    def __init__(self, corpus: str = "sections", search=None, llm=None, sections=None, **kwargs):
        super().__init__(timeout=180, **kwargs)
        self.search = search or index.Search(corpus, K)
        self.llm = llm or answer.llm()
        self.sections = sections or pub17.load()

    def context(self, nodes) -> str:
        """The retrieved nodes, each followed by the sections it links to"""
        parts = []
        for r in nodes:
            see = [s for id in index.sections(r) if id in self.sections for s in self.sections[id].see]
            parts.append(answer.context([r]) + (f"\n(links to sections {', '.join(dict.fromkeys(see))})" if see else ""))
        return "\n\n".join(parts)

    @step
    async def start(self, ctx: Context, ev: StartEvent) -> Think:
        nodes = self.search(ev.question)
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=INSTRUCTIONS),
            ChatMessage(role=MessageRole.USER, content=f"Sections of Publication 17:\n\n{self.context(nodes)}\n\nQuestion: {ev.question}"),
        ]
        await ctx.store.set("run", Run(messages=messages, seen=[s for r in nodes for s in index.sections(r)]))
        return Think()

    @step
    async def think(self, ctx: Context, ev: Think) -> Act | StopEvent:
        run: Run = await ctx.store.get("run")
        if len(run.tools) < MAX_TOOL_CALLS:
            response = await self.llm.achat_with_tools(TOOLS, chat_history=run.messages, allow_parallel_tool_calls=True)
            calls = self.llm.get_tool_calls_from_response(response, error_on_no_tool_call=False)
        else:
            run.messages.append(ChatMessage(role=MessageRole.USER, content="No tool calls left. Answer now with what you have read."))
            response, calls = await self.llm.achat(run.messages), []
        run.messages.append(response.message)
        run.calls, run.tokens = run.calls + 1, run.tokens + answer.tokens(response)
        if calls:
            return Act(calls=calls[: MAX_TOOL_CALLS - len(run.tools)])
        ms = round((time.perf_counter() - run.start) * 1000)
        return StopEvent(result=answer.finish(response.message.content or "", run.seen, calls=run.calls, tokens=run.tokens, tools=run.tools, ms=ms))

    @step
    async def act(self, ctx: Context, ev: Act) -> Think:
        run: Run = await ctx.store.get("run")
        for call in ev.calls:
            result = self.tool(call, run)
            run.tools.append({"name": call.tool_name, "args": call.tool_kwargs})
            run.messages.append(ChatMessage(role=MessageRole.TOOL, content=result, additional_kwargs={"tool_call_id": call.tool_id, "name": call.tool_name}))
        return Think()

    # A span of its own when traced, so a search's retrieval shows up under the call that made it
    @dispatcher.span
    def tool(self, call: ToolSelection, run: Run) -> str:
        args = call.tool_kwargs
        if call.tool_name == "search_publication":
            nodes = self.search(str(args.get("query", "")))
            run.seen += [s for r in nodes for s in index.sections(r)]
            return self.context(nodes)
        if call.tool_name == "read_section":
            id = str(args.get("section", "")).strip().strip("[]")
            if id not in self.sections:
                return f"There is no section {id!r}; sections are numbered by chapter, from 1.1 to {list(self.sections)[-1]}."
            s = self.sections[id]
            run.seen.append(s.id)
            text = s.text if len(s.text) <= MAX_READ_CHARS else s.text[:MAX_READ_CHARS] + " [...]"
            see = f"\n(links to sections {', '.join(s.see)})" if s.see else ""
            return f"--- section {s.id}: {s.heading} ---\n{text}{see}"
        return f"Unknown tool: {call.tool_name}"

    def ask(self, question: str) -> answer.Answer:
        async def go():
            return await self.run(question=question)

        return asyncio.run(go())


if __name__ == "__main__":
    tracing.trace_to_phoenix()
    print(Agent().ask(" ".join(sys.argv[1:])))

# What the baseline and the agent share: the model, the instructions, how retrieved nodes are shown
# to it, and the citation check. An answer cites Publication 17 sections as [3.9]; any section it
# cites that wasn't retrieved or read while answering is dropped from the text, and reported.

import re
from dataclasses import dataclass, field

from dotenv import load_dotenv
from llama_index.core.base.llms.types import ChatResponse
from llama_index.core.schema import NodeWithScore
from llama_index.llms.google_genai import GoogleGenAI

from tax import index

load_dotenv(".env")

LLM_MODEL = "gemini-3.5-flash-lite"
REFUSAL = "I couldn't find this in IRS Publication 17 (2025)."
SECTION = r"\d{1,2}\.\d{1,3}"
# [3.9], and the grouped forms the model also writes: [3.9, 3.10], [3.9; 3.10], [3.9 and 3.10]
CITATION = re.compile(rf"\[({SECTION}(?:\s*(?:,|;|and)\s*{SECTION})*)\]")

RULES = """You answer questions about filing a 2025 U.S. federal income tax return using only IRS Publication 17 (2025), Your Federal Income Tax, whose sections you are given.

- Answer in English, directly and briefly, with amounts, dates and conditions exactly as the publication states them.
- Cite the sections that support each sentence by their number in square brackets, right after the sentence: [3.9]. Cite only sections whose text you were given."""

# Not answering from general knowledge: other years, state taxes, cases the publication doesn't cover
REFUSE = f"""Don't answer from general knowledge, or about other tax years, state or local taxes, or cases the publication doesn't cover. If the publication answers no part of the question, reply exactly "{REFUSAL}" and nothing else; if it answers only part, answer that part and say the publication doesn't cover the rest."""

SYSTEM = f"""{RULES}
- Answer only from the sections you were given. {REFUSE}"""


def llm() -> GoogleGenAI:
    return GoogleGenAI(model=LLM_MODEL, temperature=0)


def tokens(response: ChatResponse) -> int:
    usage = (response.raw or {}).get("usage_metadata") or {}
    return usage.get("total_token_count") or 0


def context(nodes: list[NodeWithScore]) -> str:
    """Retrieved nodes as the model sees them, each headed by the sections it holds"""
    return "\n\n".join(f"--- sections {', '.join(index.sections(r))} ---\n{r.node.text}" for r in nodes)


@dataclass
class Answer:
    text: str
    cited: list[str]  # what the answer cites, after the check
    dropped: list[str]  # what it cited without having retrieved or read it
    refused: bool
    seen: list[str]  # every section retrieved or read while answering
    calls: int = 0  # model calls
    tokens: int = 0
    tools: list[dict] = field(default_factory=list)  # tool calls, in order
    ms: int = 0


def check(text: str, seen: set[str]) -> tuple[str, list[str], list[str]]:
    """The text without citations to sections it never saw, what it cites, and what was dropped"""
    found = [s for group in CITATION.findall(text) for s in re.findall(SECTION, group)]
    dropped = list(dict.fromkeys(s for s in found if s not in seen))
    # Each kept citation in its own brackets, so [3.9, 9.99] becomes [3.9]
    text = CITATION.sub(lambda m: " ".join(f"[{s}]" for s in re.findall(SECTION, m[1]) if s in seen), text)
    text = re.sub(r"[ \t]+([.,;:])", r"\1", re.sub(r"[ \t]{2,}", " ", text)).strip()
    return text, list(dict.fromkeys(s for s in found if s in seen)), dropped


def refused(text: str, cited: list[str]) -> bool:
    """The refusal sentence with nothing cited: an answer can use the sentence for the part it can't answer"""
    return REFUSAL.rstrip(".").lower() in text.lower().replace("’", "'") and not cited


def finish(text: str, seen: list[str], **cost) -> Answer:
    text, cited, dropped = check(text, set(seen))
    return Answer(text=text, cited=cited, dropped=dropped, refused=refused(text, cited), seen=list(dict.fromkeys(seen)), **cost)

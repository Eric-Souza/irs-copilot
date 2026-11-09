# The baseline: retrieve the top 5 nodes, answer in one model call, check the citations. No tools,
# so a section the retrieved ones point to stays unread.
#
# Usage: uv run python -m tax.rag "can I claim my mother as a dependent?" [--chunks]

import sys
import time

from llama_index.core.llms import ChatMessage

from tax import answer, index, tracing

K = 5


class RAG:
    def __init__(self, corpus: str = "sections", k: int = K, search=None, llm=None):
        self.search, self.llm = search or index.Search(corpus, k), llm or answer.llm()

    def __call__(self, question: str) -> answer.Answer:
        start = time.perf_counter()
        nodes = self.search(question)
        messages = [
            ChatMessage(role="system", content=answer.SYSTEM),
            ChatMessage(role="user", content=f"Sections of Publication 17:\n\n{answer.context(nodes)}\n\nQuestion: {question}"),
        ]
        response = self.llm.chat(messages)
        seen = [s for r in nodes for s in index.sections(r)]
        return answer.finish(response.message.content or "", seen, calls=1, tokens=answer.tokens(response), ms=round((time.perf_counter() - start) * 1000))


if __name__ == "__main__":
    tracing.trace_to_phoenix()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    print(RAG("chunks" if "--chunks" in sys.argv else "sections")(" ".join(args)))

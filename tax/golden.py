# The golden set in evals/golden.json: questions written the way a taxpayer asks them, each labeled
# with the Publication 17 sections that answer it and a fact a right answer has to state. The facts
# are copied from the publication, and tests/test_golden.py checks they are still there.

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

GOLDEN = Path("evals/golden.json")


@dataclass
class Item:
    id: str
    kind: str  # number, direct, colloquial, multi-hop, hard-hop, out-of-scope
    question: str
    expected: list[str] = field(default_factory=list)  # section ids, like "3.9"
    fact: str | None = None
    # For multi-hop and hard-hop: the section the fact is in, which the first expected one only links to.
    # A hard-hop item's second section is outside the top 5 the first retrieval returns.
    hop: str | None = None
    # Other wording of the fact, also copied from an expected section, for answers that quote that instead
    also: list[str] = field(default_factory=list)

    @property
    def facts(self) -> list[str]:
        return [self.fact, *self.also] if self.fact else []

    def stated(self, text: str) -> bool:
        return any(contains(text, f) for f in self.facts)


def load(path: Path = GOLDEN) -> list[Item]:
    return [Item(**item) for item in json.loads(path.read_text(encoding="utf-8"))]


def normalize(text: str) -> str:
    # Spaces dropped altogether, and curly apostrophes as straight ones ("child’s", "child's")
    return re.sub(r"\s+", "", text).lower().replace("’", "'")


def contains(text: str, fact: str) -> bool:
    return normalize(fact) in normalize(text)

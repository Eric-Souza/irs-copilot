# IRS Publication 17 (2025), Your Federal Income Tax, from its HTML edition on irs.gov, into
# sections: every heading of chapters 1 to 14 with the text under it, numbered by chapter (3.12 is
# chapter 3's twelfth section). The HTML links its cross-references ("see Qualifying Child, earlier",
# "in chapter 3") to anchors, so each section knows exactly which sections it points to.
#
# Usage: uv run python -m tax.pub17   (reads data/p17.html, writes data/sections.jsonl)

import html
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

HTML = Path("data/p17.html")
OUT = Path("data/sections.jsonl")
SOURCE = "https://www.irs.gov/publications/p17"

CHAPTER = re.compile(r'<h2 class="title role-chap">(.*?)</h2>', re.S)
# A section starts at a chapter's highlights (What's New, Reminders), at one of its headings, or at
# the one figure title that heads a part of a chapter rather than a table (2025 Standard Deduction
# Tables, at the end of chapter 10)
HEADING = re.compile(
    r'<h2 class="title role-highlight">(.*?)</h2>|<h4 class="title role-(intro|hd1|hd2|hd3)">(.*?)</h4>'
    r'|<h3 class="title role-figure">((?:<a[^>]*></a>)?\d{4} Standard Deduction Tables)</h3>',
    re.S,
)
# Where chapter 14 ends: the additional material after it
END = re.compile(r"<h1[^>]*>(?:<a[^>]*></a>)?\s*Publication 17 - Additional Material", re.S)
ANCHOR = re.compile(r'(?:name|id)="(en_US_\d{4}_publink\d+)"')
LINK = re.compile(r'href="#(en_US_\d{4}_publink\d+)"')
LEVEL = {"highlight": 1, "intro": 1, "hd1": 1, "hd2": 2, "hd3": 3}


@dataclass
class Section:
    id: str  # "3.12"
    chapter: int
    chapter_title: str
    title: str
    path: list[str]  # the headings above it in its chapter, outermost first
    text: str
    see: list[str] = field(default_factory=list)  # the sections it links to

    @property
    def heading(self) -> str:
        return " > ".join([f"Chapter {self.chapter}. {self.chapter_title}", *self.path, self.title])

    @property
    def full(self) -> str:
        return f"[{self.id}] {self.heading}\n{self.text}"


def text(fragment: str) -> str:
    """HTML as plain text: paragraphs and list items on their own lines, table cells split by |"""
    fragment = re.sub(r"<(script|style)\b.*?</\1>", "", fragment, flags=re.S)
    fragment = re.sub(r'<(?:span|div|p) class="textobject hidden".*?</(?:span|div|p)>', "", fragment, flags=re.S)
    fragment = re.sub(r"</t[dh]>\s*", " | ", fragment)
    fragment = re.sub(r"<br\s*/?>|</(?:p|li|tr|h\d|div|caption|dt|dd)>", "\n", fragment)
    fragment = re.sub(r"<li[^>]*>", "\n- ", fragment)
    fragment = html.unescape(re.sub(r"<[^>]+>", "", fragment)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip(" |") for line in fragment.splitlines()]
    joined = re.sub(r"\n{2,}", "\n", "\n".join(line for line in lines if line)).strip()
    # A list item's paragraph lands on the line after its dash
    return re.sub(r"^-\n", "- ", joined, flags=re.M)


def title(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def parse(path: Path = HTML) -> list[Section]:
    page = path.read_text(encoding="utf-8")
    page = page[: END.search(page).start()]
    chapters = list(CHAPTER.finditer(page))
    sections, raw = [], []
    for c, chapter in enumerate(chapters):
        number, name = title(chapter[1]).split(". ", 1)
        assert int(number) == c + 1, title(chapter[1])
        body = page[chapter.end() : chapters[c + 1].start() if c + 1 < len(chapters) else len(page)]
        heads = list(HEADING.finditer(body))
        stack: list[tuple[int, str]] = []
        for h, head in enumerate(heads):
            role, name_ = ("highlight", head[1]) if head[1] is not None else ("hd1", head[4]) if head[4] is not None else (head[2], head[3])
            level = LEVEL[role]
            stack = [s for s in stack if s[0] < level]
            content = body[head.end() : heads[h + 1].start() if h + 1 < len(heads) else len(body)]
            section = Section(f"{c + 1}.{h + 1}", c + 1, name, title(name_), [s[1] for s in stack], text(content))
            stack.append((level, section.title))
            sections.append(section)
            # The heading's own anchor sits just before it, in the previous section's slice
            raw.append((head[0] + content, section))

    owner = {a: s.id for chunk, s in raw for a in ANCHOR.findall(chunk)}
    for chapter in chapters:
        # A link to a chapter goes to the chapter's first section; its anchor sits just before the
        # chapter's title, in the previous chapter's last section
        for a in ANCHOR.findall(page[page.rfind('<div class="chapter">', 0, chapter.start()) : chapter.end()]):
            owner[a] = f"{int(title(chapter[1]).split('.')[0])}.1"
    for chunk, section in raw:
        section.see = list(dict.fromkeys(owner[a] for a in LINK.findall(chunk) if a in owner and owner[a] != section.id))
    return sections


def load(path: Path = OUT) -> dict[str, Section]:
    """The parsed sections by id"""
    with path.open(encoding="utf-8") as f:
        return {s.id: s for s in (Section(**json.loads(line)) for line in f)}


if __name__ == "__main__":
    sections = parse()
    OUT.write_text("".join(json.dumps(asdict(s), ensure_ascii=False) + "\n" for s in sections), encoding="utf-8", newline="\n")
    lengths = sorted(len(s.text) for s in sections)
    print(f"{len(sections)} sections in {len({s.chapter for s in sections})} chapters, {sum(1 for s in sections if s.see)} with links, median {lengths[len(lengths) // 2]} chars, longest {lengths[-1]}")

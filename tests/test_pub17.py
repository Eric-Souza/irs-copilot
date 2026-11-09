# The parsed publication (data/sections.jsonl) and the HTML-to-text cleanup. No model.

from llama_index.core.schema import NodeWithScore, TextNode

from tax import index, pub17

SECTIONS = pub17.load()


def test_every_chapter_is_there_in_order():
    assert sorted({s.chapter for s in SECTIONS.values()}) == list(range(1, 15))
    for chapter in range(1, 15):
        ids = [s.id for s in SECTIONS.values() if s.chapter == chapter]
        assert ids == [f"{chapter}.{n}" for n in range(1, len(ids) + 1)]


def test_sections_have_titles_and_most_have_text():
    assert all(s.title and s.chapter_title for s in SECTIONS.values())
    assert sum(1 for s in SECTIONS.values() if not s.text) <= 3


def test_links_point_to_sections_that_exist():
    assert all(t in SECTIONS and t != s.id for s in SECTIONS.values() for t in s.see)
    assert sum(1 for s in SECTIONS.values() if s.see) > 100


def test_a_link_to_a_chapter_goes_to_its_first_section():
    # "See chapter 3 for more information about claiming someone as a dependent"
    assert "3.1" in SECTIONS["14.5"].see and "2.14" not in SECTIONS["14.5"].see


def test_heading_path():
    assert SECTIONS["3.9"].heading == "Chapter 3. Dependents > Dependents > Qualifying Child > Age Test"


def test_text_keeps_lists_and_tables_readable():
    html = "<p>Either:</p><ul><li><p>$7,000, or</p></li><li><p>your pay.</p></li></ul><table><tr><td>Single</td><td>$15,750</td></tr></table>"
    assert pub17.text(html) == "Either:\n- $7,000, or\n- your pay.\nSingle | $15,750"


def test_section_nodes_keep_the_heading_with_every_part():
    nodes = index.section_nodes(SECTIONS)
    assert {n.metadata["section"] for n in nodes} == set(SECTIONS)
    long = [n for n in nodes if n.metadata["parts"] > 1]
    assert long and all(n.text.startswith(f"[{n.metadata['section']}] Chapter ") for n in long)


def test_sections_reads_both_kinds_of_node():
    assert index.sections(NodeWithScore(node=TextNode(text="", metadata={"section": "3.9"}))) == ["3.9"]
    assert index.sections(NodeWithScore(node=TextNode(text="", metadata={"sections": "3.8 3.9"}))) == ["3.8", "3.9"]

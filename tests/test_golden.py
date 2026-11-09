from collections import Counter

import pytest

from tax import golden, pub17

SECTIONS = pub17.load()
ITEMS = golden.load()


def test_ids_are_unique():
    assert not [i for i, n in Counter(item.id for item in ITEMS).items() if n > 1]


def test_mix():
    kinds = Counter(item.kind for item in ITEMS)
    assert set(kinds) == {"number", "direct", "colloquial", "multi-hop", "hard-hop", "out-of-scope"}
    assert len(ITEMS) >= 60


@pytest.mark.parametrize("item", [i for i in ITEMS if i.kind != "out-of-scope"], ids=lambda i: i.id)
def test_fact_is_in_an_expected_section(item: golden.Item):
    assert item.expected and all(s in SECTIONS for s in item.expected)
    texts = {s: SECTIONS[s].text for s in item.expected}
    for fact in item.facts:
        assert any(golden.contains(t, fact) for t in texts.values()), f"{fact!r} is in none of {item.expected}"


@pytest.mark.parametrize("item", [i for i in ITEMS if i.kind in ("multi-hop", "hard-hop")], ids=lambda i: i.id)
def test_multi_hop_needs_the_second_section(item: golden.Item):
    first = SECTIONS[item.expected[0]]
    assert item.hop in item.expected[1:]
    for fact in item.facts:
        assert golden.contains(SECTIONS[item.hop].text, fact)
        assert not golden.contains(first.text, fact), f"{fact!r} is already in {first.id}"
    # The publication itself links the first section to the second, maybe through another one
    reachable = set(first.see) | {s for t in first.see for s in SECTIONS[t].see}
    assert item.hop in reachable


@pytest.mark.parametrize("item", [i for i in ITEMS if i.kind == "out-of-scope"], ids=lambda i: i.id)
def test_out_of_scope_has_no_answer(item: golden.Item):
    assert not item.expected and item.fact is None

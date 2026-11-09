from tax import answer


def test_check_keeps_citations_it_saw_and_drops_the_rest():
    text, cited, dropped = answer.check("Yes, you can [3.9]. The limit is $5,200 [3.17] [9.99].", {"3.9", "3.17"})
    assert text == "Yes, you can [3.9]. The limit is $5,200 [3.17]."
    assert cited == ["3.9", "3.17"] and dropped == ["9.99"]


def test_check_tidies_the_space_a_dropped_citation_leaves():
    text, cited, dropped = answer.check("No [3.12], see [3.13] .", {"3.13"})
    assert text == "No, see [3.13]."
    assert cited == ["3.13"] and dropped == ["3.12"]


def test_citations_need_a_chapter_and_a_section():
    assert answer.check("See [3] and [chapter 3].", {"3.1"}) == ("See [3] and [chapter 3].", [], [])


def test_refusal_is_recognized_in_any_case_and_with_curly_apostrophes():
    assert answer.refused("I couldn’t find this in IRS Publication 17 (2025).", [])
    assert answer.refused(answer.REFUSAL.upper(), [])
    assert not answer.refused("Yes [3.9].", ["3.9"])


def test_a_partial_refusal_with_citations_is_an_answer():
    assert not answer.refused(f"Yes [1.19]. As for the rest: {answer.REFUSAL}", ["1.19"])


def test_finish_reports_what_was_seen_once():
    a = answer.finish(answer.REFUSAL, ["1.3", "1.3", "1.4"], calls=1)
    assert a.refused and a.seen == ["1.3", "1.4"] and a.cited == [] and a.calls == 1


def test_check_splits_grouped_citations():
    text, cited, dropped = answer.check("It isn't [9.32, 9.34]. See also [3.9 and 9.99; 3.17].", {"3.9", "3.17", "9.32", "9.34"})
    assert text == "It isn't [9.32] [9.34]. See also [3.9] [3.17]."
    assert cited == ["9.32", "9.34", "3.9", "3.17"] and dropped == ["9.99"]

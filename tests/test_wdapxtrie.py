"""Tests for trie-based whole-word approximate matching."""

# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest

from apxtrie.wdapxtrie import WordApproxTrie

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MAP6_DICTIONARY = PROJECT_ROOT / "resources/map6.phraseDirect2.dict.noRepeat"


@pytest.fixture(scope="module")
def wd_drug_trie():
    """A word trie populated from the bundled map6 dictionary."""
    trie = WordApproxTrie()
    trie.wd_load(MAP6_DICTIONARY)
    return trie


def test_wd_find_approximate_uses_word_trie(tmp_path):
    trie = WordApproxTrie()
    short_definition = trie.wd_add_definition("tylenol pm", "short")
    long_definition = trie.wd_add_definition("tylenol extra strength", "long")
    trie.wd_add_definition("aspirin", "other")

    candidates = trie.wd_find_approximate_candidates("tylenol night", 1)
    assert [(candidate[1], candidate[2]) for candidate in candidates] == [
        (1, short_definition),
    ]
    assert candidates[0][3] == "MS"

    candidates = trie.wd_find_approximate_candidates("tylenol strength", 1)
    assert {(candidate[1], candidate[2]) for candidate in candidates} == {
        (1, short_definition),
        (1, long_definition),
    }
    assert trie.wd_find_approximate("tylenol pm extra", 1) is short_definition
    assert trie.wd_find_approximate("tylenol night", 0) is None

    trie_path = tmp_path / "word-index.wd_trie"
    trie.wd_write(str(trie_path))
    assert trie_path.is_file()
    assert (tmp_path / "word-index.wd_trie.dictdefn").is_file()

    restored_trie = WordApproxTrie()
    restored_trie.wd_load_trie(str(trie_path))
    assert restored_trie.wd_find_approximate("tylenol night", 1).defn == "short"


def test_wd_write_requires_wd_trie_suffix(tmp_path):
    trie = WordApproxTrie()

    with pytest.raises(ValueError, match="\\.wd_trie"):
        trie.wd_write(str(tmp_path / "word-index.trie"))


def test_wd_print_trie(capsys):
    trie = WordApproxTrie()
    trie.wd_add_definition("tylenol pm", "short")

    trie.wd_print_trie()

    assert capsys.readouterr().out.splitlines() == [
        "root",
        "|--tylenol",
        "|--|--pm: (1, 'tylenol pm', 'short')",
    ]


def test_prepare_wd_token_text_removes_punctuation():
    trie = WordApproxTrie()

    assert trie.prepare_wd_token_text("tylenol, pm! extra-strength") == (
        "tylenol pm extra strength"
    )
    assert trie.prepare_wd_token_text("  tylenol...  pm  ") == "tylenol pm"


def test_wd_substr_search_returns_offsets_for_paragraph_matches(wd_drug_trie):
    term = "tylenol extra strength"
    paragraph = (
        "Before breakfast, Maria took tylenol extra strength with water and read "
        "the label carefully. At noon she bought lunch, then chose tylenol extra "
        "strength because the headache returned. In the evening, her doctor advised "
        "rest, hydration, and tylenol extra strength only as directed. She slept "
        "well afterward and planned to call the clinic tomorrow if pain continued."
    )
    matches = wd_drug_trie.wd_substr_search(paragraph, terms=[term])

    assert [(match[1], match[2]) for match in matches] == [(29, 51), (130, 152), (240, 262)]
    assert [paragraph[match[1]:match[2]] for match in matches] == [term, term, term]


def test_wd_substr_search_with_one_word_edit(wd_drug_trie):
    term = "tylenol extra strength"
    first_variant = "tylenol extra extra strength"
    second_variant = "tylenol strength"
    third_variant = "tylenol extra extra extra strength"
    paragraph = _paragraph_with_variants(first_variant, second_variant, third_variant)
    first_start, first_end, second_start, second_end, _third_start, _third_end = (
        _variant_offsets(paragraph, first_variant, second_variant, third_variant)
    )
    match_summary = [(match[0], match[1], match[2])
                     for match in wd_drug_trie.wd_substr_search(
                         paragraph, edit_dist=1, terms=[term]
                     )]

    # the third is not returned
    assert len(match_summary) == 2
    assert match_summary == [
        (1, first_start, first_end),
        (1, second_start, second_end),
    ]


def test_wd_substr_search_with_one_word_edit_v2(wd_drug_trie):
    term = "tylenol extra strength"
    first_variant = "tylenol extra extra strength"
    second_variant = "tylenol strength"
    third_variant = "tylenol"  # only the third one differs
    paragraph = _paragraph_with_variants(first_variant, second_variant, third_variant)
    first_start, first_end, second_start, second_end, third_start, third_end = (
        _variant_offsets(paragraph, first_variant, second_variant, third_variant)
    )
    match_summary = [(match[0], match[1], match[2])
                     for match in wd_drug_trie.wd_substr_search(
                         paragraph, edit_dist=1, terms=[term]
                     )]

    # the third is not returned
    assert len(match_summary) == 2
    assert (1, first_start, first_end) in match_summary
    assert (1, second_start, second_end) in match_summary
    assert (2, third_start, third_end) not in match_summary

def test_wd_substr_search_with_two_word_edits(wd_drug_trie):
    term = "tylenol extra strength"
    first_variant = "tylenol extra extra extra strength"
    second_variant = "tylenol extra extra strength"
    third_variant = "tylenol strength"
    paragraph = _paragraph_with_variants(first_variant, second_variant, third_variant)
    first_start, first_end, second_start, second_end, third_start, third_end = (
        _variant_offsets(paragraph, first_variant, second_variant, third_variant)
    )
    match_summary = [(match[0], match[1], match[2])
                     for match in wd_drug_trie.wd_substr_search(
                         paragraph, edit_dist=2, terms=[term]
                     )]

    assert match_summary == [
        (2, first_start, first_end),
        (1, second_start, second_end),
        (1, third_start, third_end),
    ]

def test_wd_substr_search_with_two_word_edits_v2(wd_drug_trie):
    term = "tylenol extra strength"
    first_variant = "tylenol extra extra extra strength"
    second_variant = "tylenol extra extra strength"
    third_variant = "tylenol"
    paragraph = _paragraph_with_variants(first_variant, second_variant, third_variant)
    first_start, first_end, second_start, second_end, third_start, third_end = (
        _variant_offsets(paragraph, first_variant, second_variant, third_variant)
    )
    match_summary = [(match[0], match[1], match[2])
                     for match in wd_drug_trie.wd_substr_search(
                         paragraph, edit_dist=2, terms=[term]
                     )]

    assert (2, first_start, first_end) in match_summary
    assert (1, second_start, second_end) in match_summary
    assert (2, third_start, third_end) in match_summary


def test_wd_substr_search_with_two_word_edits_v3(wd_drug_trie):
    term = "tylenol extra strength"
    first_variant = "tylenol extra extra extra strength"
    second_variant = "tylenol extra extra strength"
    third_variant = "tylenol extra extra extra extra strength"
    paragraph = _paragraph_with_variants(first_variant, second_variant, third_variant)
    first_start, first_end, second_start, second_end, third_start, _third_end = (
        _variant_offsets(paragraph, first_variant, second_variant, third_variant)
    )
    match_summary = [(match[0], match[1], match[2])
                     for match in wd_drug_trie.wd_substr_search(
                         paragraph, edit_dist=2, terms=[term]
                     )]

    # (2, "tylenol extra extra extra strength", "MDDMM")
    # (1, "tylenol extra extra strength", "MDMM")
    # (2, "tylenol", "MII")  <- a littl unexpected

    assert (2, first_start, first_end) in match_summary
    assert (1, second_start, second_end) in match_summary
    assert (2, third_start, third_start + len('tylenol')) in match_summary


def test_wd_substr_search_with_one_word_edit_without_tylenol(wd_drug_trie):
    term = "tylenol extra strength"
    first_variant = "extra extra strength"
    second_variant = "strength"
    third_variant = "extra extra extra strength"
    paragraph = _paragraph_with_variants(first_variant, second_variant, third_variant)
    assert wd_drug_trie.wd_substr_search(paragraph, edit_dist=1, terms=[term]) == []


def test_wd_substr_search_with_two_word_edits_without_tylenol(wd_drug_trie):
    term = "tylenol extra strength"
    first_variant = "extra extra extra strength"
    second_variant = "extra extra strength"
    third_variant = "strength"
    paragraph = _paragraph_with_variants(first_variant, second_variant, third_variant)
    assert wd_drug_trie.wd_substr_search(paragraph, edit_dist=2, terms=[term]) == []


def _paragraph_with_variants(first_variant, second_variant, third_variant):
    return (
        f"Before breakfast, Maria took {first_variant} with water and read the "
        f"label carefully. At noon she bought lunch, then chose {second_variant} "
        f"because the headache returned. In the evening, her doctor advised rest, "
        f"hydration, and {third_variant} only as directed. She slept well afterward "
        "and planned to call the clinic tomorrow if pain continued."
    )


def _variant_offsets(paragraph, first_variant, second_variant, third_variant):
    first_start = paragraph.index(first_variant)
    first_end = first_start + len(first_variant)
    second_start = paragraph.index(second_variant, first_end)
    second_end = second_start + len(second_variant)
    third_start = paragraph.index(third_variant, second_end)
    third_end = third_start + len(third_variant)
    return first_start, first_end, second_start, second_end, third_start, third_end


def test_wd_find_approximate_with_map6_dictionary(wd_drug_trie):
    assert len(wd_drug_trie.defn_list) > 18_000
    assert wd_drug_trie.num_defn == len(wd_drug_trie.defn_list) - 1

    exact_match = wd_drug_trie.wd_find_approximate("tylenol pm", 0)
    assert exact_match.term == "tylenol pm"

    candidates = wd_drug_trie.wd_find_approximate_candidates("tylenol pmx", 1)
    costs_by_term = {candidate[2].term: candidate[1] for candidate in candidates}
    assert costs_by_term["tylenol pm"] == 1
    assert "tylenol pm extra strength" not in costs_by_term

    candidates = wd_drug_trie.wd_find_approximate_candidates(
        "solarcaine aloe extra burn", 1
    )
    costs_by_term = {candidate[2].term: candidate[1] for candidate in candidates}
    assert costs_by_term["solarcaine aloe extra burn relief"] == 1

#!/usr/bin/env python3
"""Extract known medication terms from text with their character offsets."""

from apxtrie import ApproxRadixTrie, WordApproxTrie


def extract_entities() -> int:
    term = "tylenol extra strength"
    text = (
        "Before breakfast, Maria took tylenol extra strength with water and read "
        "the label carefully. At noon she bought lunch, then chose tylenol extra "
        "strenth because the headache returned. In the evening, her doctor advised "
        "rest, hydration, and tylenol extr strengthh only as directed. She slept "
        "well afterward and planned to call the clinic tomorrow if pain continued."
    )

    drug_approxatrie = ApproxRadixTrie()
    drug_approxatrie.add_definition(term, "example medication")

    # Build a trie containing only ``term`` and allow up to two character edits.
    matches = drug_approxatrie.substr_search(text, edist_left=2)

    print("Entities found (character edit-distance, maximum 2):")
    for cost, start, end, _edits_left, definition, _operations, _dictionary_term in matches:
        if cost < 0:
            continue
        print(
            f"- {definition.term!r} at offsets [{start}:{end}], "
            f"edit distance {cost}: {text[start:end]!r}"
        )
    return 0


def extract_entities_by_word() -> int:
    term = "tylenol extra strength"
    text = (
        "Before breakfast, Maria took tylenol extra strength with water and read "
        "the label carefully. At noon she bought lunch, then chose tylenol extraa "
        "strength because the headache returned. In the evening, her doctor advised "
        "rest, hydration, and tylenol strength only as directed. She slept "
        "well afterward and planned to call the clinic tomorrow if pain continued."
    )

    drug_approxatrie = WordApproxTrie()
    drug_approxatrie.wd_add_definition(term, "example medication")

    # ``wd_substr_search`` accepts ``terms`` and preserves offsets in ``text``.
    matches = drug_approxatrie.wd_substr_search(text, edit_dist=1, terms=[term])

    print("Entities found (word edit-distance, maximum 1):")
    for cost, start, end, _edits_left, definition, _operations in matches:
        print(
            f"- {definition.term!r} at offsets [{start}:{end}], "
            f"edit distance {cost}: {text[start:end]!r}"
        )
    return 0


def main():
    extract_entities()
    print()
    extract_entities_by_word()


if __name__ == "__main__":
    raise SystemExit(main())

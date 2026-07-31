#!/usr/bin/env python
"""Build and query a word-based approximate trie from a tab-separated dictionary."""

import argparse
from pathlib import Path

from apxtrie.wdapxtrie import WordApproxTrie

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DICTIONARIES = (
    PROJECT_ROOT / "resources/map6.phraseDirect2.dict.noRepeat",
    PROJECT_ROOT / "resources/ingredient.dict",
    PROJECT_ROOT / "resources/acid.dict",
    PROJECT_ROOT / "resources/ignore.dict",
)


def main():
    """Load a word trie, print approximate matches, and optionally serialize it."""
    parser = argparse.ArgumentParser(
        description="Query whole-word edit-distance matches with WordApproxTrie."
    )
    parser.add_argument(
        "--dictionary",
        action="append",
        type=Path,
        help="tab-separated term/definition dictionary; repeat to load multiple files",
    )
    parser.add_argument(
        "--query",
        default="tylenol pmx",
        help="term to match",
    )
    parser.add_argument(
        "--edit-dist",
        default=1,
        type=int,
        help="maximum whole-word edit distance (default: 1)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional output path; it must end in .wd_trie",
    )
    args = parser.parse_args()

    trie = WordApproxTrie()
    dictionary_files = args.dictionary or DEFAULT_DICTIONARIES
    for dictionary_file in dictionary_files:
        trie.wd_load(dictionary_file)
    print(f"loaded {trie.num_defn} unique definitions")
    print("### Here is the word-based trie")
    print()
    trie.wd_print_trie()
    
    print()
    candidates = trie.wd_find_approximate_candidates(args.query, args.edit_dist)
    print(f"word-distance candidates for {args.query!r} (maximum {args.edit_dist}):")
    for edits_left, edit_cost, definition, operations in candidates:
        print(
            f"  cost={edit_cost}, edits_left={edits_left}, operations={operations}: "
            f"{definition.term!r} => {definition.defn!r}"
        )

    if args.output:
        trie.wd_write(str(args.output))
        print(f"wrote {args.output} and {args.output}.dictdefn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

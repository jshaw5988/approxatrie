#!/usr/bin/env python

import argparse
import json

from apxtrie.dictdefn import DictDefn
from apxtrie.apxtrie import ApproxRadixTrie


class JsonDictDefn(DictDefn):
    def serialize_defn(self) -> str:
        return json.dumps(self.defn)

    @classmethod
    def deserialize_defn(cls, raw: str):
        return json.loads(raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='normalize address v1')
    parser.add_argument("-v","--verbosity", help="increase output verbosity")
    parser.add_argument("-d","--debug", action="store_true", help="print debug information")
    # parser.add_argument("filename")


    args = parser.parse_args()
    if args.verbosity:
        print("verbosity turned on")
    if args.debug:
        IS_DEBUG = True

    ptrie= ApproxRadixTrie()
    ptrie.load("resources/map6.phraseDirect2.dict.noRepeat")
    ptrie.load("resources/ingredient.dict")
    ptrie.load("resources/acid.dict")
    ptrie.load("resources/ignore.dict")

    print('### Here is the string approxatrie')
    print()
    ptrie.print_trie()

    # for JSON dictdefn
    definitions = {
        "bromocriptine": {
            "generic": "bromocriptine",
            "class": "dopamine_agonist",
            "codes": ["N04BC01"],
        },
        "tylenol pm": {
            "generic": "acetaminophen/diphenhydramine",
            "class": "analgesic/antihistamine",
            "codes": ["N02BE01", "R06AA02"],
        },
        "lisinopril": {
            "generic": "lisinopril",
            "class": "ace_inhibitor",
            "codes": ["C09AA03"],
        },
    }
    json_trie = ApproxRadixTrie(defn_class=JsonDictDefn)

    for term, definition in definitions.items():
        json_trie.add_definition(term, definition)

    print()
    print('### Here is the JSON approxatrie')
    print()
    json_trie.print_trie()

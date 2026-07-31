from apxtrie.apxtrie import ApproxRadixTrie


def test_string_definition_serialization_round_trip(tmp_path):
    definitions = {
        "bromocriptine": "dopamine agonist",
        "tylenol pm": "acetaminophen/diphenhydramine",
        "lisinopril": "ACE inhibitor",
    }
    trie = ApproxRadixTrie()

    for term, definition in definitions.items():
        trie.add_definition(term, definition)

    trie_path = str(tmp_path / "string_definitions.trie")
    trie.write(trie_path)

    restored_trie = ApproxRadixTrie()
    restored_trie.load_trie(trie_path)

    for term, definition in definitions.items():
        assert restored_trie.find(term).defn == definition


SAMPLE_TEXT = "I found tylenol pm cocaine in my purse"

def test_serialized_trie_searches(drug_trie, tmp_path):
    output_trie = str(tmp_path / "map6.trie")
    drug_trie.write(output_trie)

    trie = ApproxRadixTrie()
    trie.load_trie(output_trie)

    assert trie.find("tylenol pm").id == 8410
    assert {definition.id for definition in trie.find_prefix("tylenol pm")} == {
        2263,
        8410,
    }

    exact_matches = trie.substr_search(SAMPLE_TEXT, 0)
    assert [(match[1], match[2], match[4].id) for match in exact_matches] == [
        (8, 18, 8410),
        (19, 26, 185),
    ]

    filtered_matches = trie.substr_search_dist_filter(SAMPLE_TEXT)
    assert [(match[1], match[2], match[4].id) for match in filtered_matches] == [
        (8, 18, 8410),
        (19, 26, 185),
        (33, 38, 6141),
    ]

    assert trie.find("tylenol pm").id == 8410

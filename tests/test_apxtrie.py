"""Tests for the main ApproxRadixTrie API."""

from apxtrie.apxtrie import ApproxRadixTrie
from apxtrie.apxtrienode import ApxTrieNode


def test_node_string_representation_uses_dict_defn():
    root = ApxTrieNode("root", "root definition")
    child = ApxTrieNode("child", "child definition")
    root.update_child("c", child)

    rendered = str(root)

    assert "root definition" in rendered
    assert "child definition" in rendered


def test_add_definition_round_trip(tmp_path):
    trie = ApproxRadixTrie()
    definition = trie.add_definition("example term", "example definition")

    assert definition.id == 1
    assert trie.find("example term") is definition

    trie_path = str(tmp_path / "example.trie")
    trie.write(trie_path)

    restored_trie = ApproxRadixTrie()
    restored_trie.load_trie(trie_path)
    restored_definition = restored_trie.find("example term")
    assert restored_definition.id == 1
    assert restored_definition.term == "example term"
    assert restored_definition.defn == "example definition"

    next_definition = restored_trie.add_definition("next term", "next definition")
    assert next_definition.id == 2


def test_add_definition_rejects_duplicates_without_registering_them(capsys):
    trie = ApproxRadixTrie()
    first_definition = trie.add_definition("duplicate term", "first definition")
    duplicate_definition = trie.add_definition("duplicate term", "second definition")

    assert duplicate_definition is None
    assert trie.num_defn == 1
    assert trie.defn_list == [trie.defn_list[0], first_definition]
    assert trie.find("duplicate term") is first_definition
    assert "duplicate entry: 'duplicate term~'" in capsys.readouterr().err


def test_find(drug_trie):
    assert drug_trie.find("tylenol")
    assert drug_trie.find("tylenol pm")

    assert not drug_trie.find("tylen")
    assert not drug_trie.find("tylenol noon")


def test_find_prefix_has_matches(drug_trie):
    match_group_list = drug_trie.find_prefix("tylenol")

    assert match_group_list

def test_find_approximate(drug_trie):
    defn = drug_trie.find_approximate("tylenol pm", 0)
    assert defn is not None and defn.id == 8410

    defn = drug_trie.find_approximate("tylenol pmx", 1)
    assert defn is not None and defn.id == 8410

    defn = drug_trie.find_approximate("tylenol pmxx", 1)
    assert not defn

def test_find_approximate_cache(drug_trie):
    defn = drug_trie.find_approximate("tixlenol pmx", 3)
    assert defn is not None and defn.id == 8410

    defn = drug_trie.find_approximate("tixlenol pmx", 2)
    assert not defn

    defn = drug_trie.find_approximate("tixlenol pmx", 3, is_cache_mode=False)
    assert defn is not None and defn.id == 8410

    defn = drug_trie.find_approximate("tixlenol pmx", 2, is_cache_mode=False)
    assert not defn


def test_find_approximate_candidates(drug_trie):
    defn_list = drug_trie.find_approximate_candidates("tylenol pm", 0)
    print("defn_list = " + str(defn_list))
    aset = {defn[2].id for defn in defn_list}
    print("aset = " + str(aset))
    assert aset == {8410}  # 'tylenol pm extra strnegth', 'tylenol pm'

    defn_list = drug_trie.find_approximate_candidates("tixlenol pmx", 3)
    print("defn_list = " + str(defn_list))
    alist = [defn[2].id for defn in defn_list]
    print("alist = " + str(alist))
    assert alist == [8410, 8410]  # 'tylenol pm', 'tylenol pm', but with different matching

    defn_list = drug_trie.find_approximate_candidates("tixlenol pmx", 2)
    assert not defn_list

    defn_list = drug_trie.find_approximate_candidates("tiixlenol pmx", 4, is_cache_mode=False)
    print("defn_list = " + str(defn_list))
    alist = [defn[2].id for defn in defn_list]
    print("alist = " + str(alist))
    assert alist == [8410, 8410, 8410]  # 'tylenol pm', 'tylenol pm', but with different matching

    defn_list = drug_trie.find_approximate_candidates("tiixlenol pmx", 4)
    print("defn_list = " + str(defn_list))
    alist = [defn[2].id for defn in defn_list]
    print("alist = " + str(alist))
    assert alist == [8410, 8410, 8410]  # 'tylenol pm', 'tylenol pm', but with different matching

    defn_list = drug_trie.find_approximate_candidates("tiixlenol pmx", 3)
    assert not defn_list


def test_find_prefix_results(drug_trie):
    defn_list = drug_trie.find_prefix("tylenol pm")
    print("defn_list = " + str(defn_list))
    aset = {defn.id for defn in defn_list}
    print("aset = " + str(aset))
    assert aset == {8410, 2263}  # 'tylenol pm extra strength', 'tylenol pm'

    defn_list = drug_trie.find_prefix("solarcaine")
    print("defn_list = " + str(defn_list))
    aset = {defn.id for defn in defn_list}
    print("aset = " + str(aset))
    assert aset == {16376, 11108, 9471}  # 'solarcaine', 'solarcaine aloe extra burn',
                                         # 'solarcaine plus aloe'

    defn_list = drug_trie.find_prefix("rapif")
    print("defn_list = " + str(defn_list))
    aset = {defn.id for defn in defn_list}
    print("aset = " + str(aset))
    assert aset == {17971, 16474, 1124}  # 'rapiflux'

    defn_list = drug_trie.find_prefix("rapife")
    print("defn_list = " + str(defn_list))
    aset = {defn.id for defn in defn_list}
    print("aset = " + str(aset))
    assert aset == {17971, 16474}  # 'rapiflux'

    defn_list = drug_trie.find_prefix("rappif")
    assert not defn_list


def test_substr_search(drug_trie):
    text = "I found tylenol pm cocaine in my purse"

    def match_summary(matches):
        return [
            (cost, start, end, edit_distance_left, definition.id, dictionary_term)
            for cost, start, end, edit_distance_left, definition, \
                _operations, dictionary_term in matches
        ]

    assert match_summary(drug_trie.substr_search(text, 0)) == [
        (0, 8, 18, 0, 8410, "tylenol pm"),
        (0, 19, 26, 0, 185, "cocaine"),
    ]
    assert match_summary(drug_trie.substr_search(text, 1)) == [
        (0, 8, 18, 1, 8410, "tylenol pm"),
        (0, 19, 26, 1, 185, "cocaine"),
        (1, 33, 38, 0, 6141, "purge"),
    ]
    assert match_summary(drug_trie.substr_search(text, 2)) == [
        (0, 8, 18, 2, 8410, "tylenol pm"),
        (0, 19, 26, 2, 185, "cocaine"),
        (1, 33, 38, 1, 6141, "purge"),
    ]

    assert match_summary(drug_trie.substr_search_dist_filter(text)) == [
        (0, 8, 18, 2, 8410, "tylenol pm"),
        (0, 19, 26, 2, 185, "cocaine"),
        (1, 33, 38, 1, 6141, "purge"),
    ]

    assert drug_trie.find("tylenol pm").id == 8410
    assert {definition.id for definition in drug_trie.find_prefix("tylenol pm")} == {
        2263,
        8410,
    }

    dict_defn = drug_trie.find_approximate("tylenol pm", 0)
    assert dict_defn.id == 8410

    dict_defn_list = drug_trie.find_prefix("rappif")
    assert dict_defn_list == []

    typo_text = "I found tylenol pim cocaine in my purse"
    assert match_summary(drug_trie.substr_search(typo_text, 0)) == [
        (0, 8, 15, 0, 827, "tylenol"),
        (0, 20, 27, 0, 185, "cocaine"),
    ]
    assert match_summary(drug_trie.substr_search(typo_text, 1)) == [
        (1, 8, 19, 0, 8410, "tylenol pm"),
        (0, 20, 27, 1, 185, "cocaine"),
        (1, 34, 39, 0, 6141, "purge"),
    ]
    assert match_summary(drug_trie.substr_search(typo_text, 2)) == [
        (1, 8, 19, 1, 8410, "tylenol pm"),
        (0, 20, 27, 2, 185, "cocaine"),
        (1, 34, 39, 1, 6141, "purge"),
    ]

import pytest

from apxtrie.apxtrie import ApproxRadixTrie


@pytest.fixture(scope="module")
def drug_trie():
    """A trie populated with the bundled drug dictionaries."""
    trie = ApproxRadixTrie()
    for dictionary in (
        "resources/map6.phraseDirect2.dict.noRepeat",
        "resources/ingredient.dict",
        "resources/acid.dict",
        "resources/ignore.dict",
    ):
        trie.load(dictionary)
    return trie

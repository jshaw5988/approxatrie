import json

from apxtrie.dictdefn import DictDefn
from apxtrie.apxtrie import ApproxRadixTrie


class JsonDictDefn(DictDefn):
    def serialize_defn(self) -> str:
        return json.dumps(self.defn)

    @classmethod
    def deserialize_defn(cls, raw: str):
        return json.loads(raw)


def test_json_definition_serialization_round_trip(tmp_path):
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
    trie = ApproxRadixTrie(defn_class=JsonDictDefn)

    for term, definition in definitions.items():
        trie.add_definition(term, definition)

    trie_path = str(tmp_path / "json_definitions.trie")
    trie.write(trie_path)

    restored_trie = ApproxRadixTrie(defn_class=JsonDictDefn)
    restored_trie.load_trie(trie_path)

    for term, definition in definitions.items():
        restored_definition = restored_trie.find(term)
        assert isinstance(restored_definition, JsonDictDefn)
        assert restored_definition.defn == definition

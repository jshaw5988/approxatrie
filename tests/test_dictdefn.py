"""Tests for dictionary definition records."""

import json

from apxtrie.dictdefn import DictDefn


class JsonDictDefn(DictDefn):
    def serialize_defn(self) -> str:
        return json.dumps(self.defn)

    @classmethod
    def deserialize_defn(cls, raw: str):
        return json.loads(raw)


def test_init():
    ddefn = DictDefn(3, "hello", "james")
    assert ddefn is not None

    assert ddefn.id == 3
    assert ddefn.term == "hello"
    assert ddefn.defn == "james"

def test_str():
    ddefn = DictDefn(3, "hello", "james")
    assert str(ddefn) == "(3, 'hello', 'james')"

def test_to_tsv():
    ddefn = DictDefn(3, "hello", "james")
    assert ddefn.to_tsv() == "3\thello\tjames"


def test_json_definition_payload_round_trip():
    payload = {
        "generic": "acetaminophen",
        "codes": ["N02BE01"],
        "active": True,
    }
    ddefn = JsonDictDefn(3, "tylenol", payload)

    serialized_payload = ddefn.serialize_defn()

    assert json.loads(serialized_payload) == payload
    assert JsonDictDefn.deserialize_defn(serialized_payload) == payload


def test_json_definition_tsv_contains_a_json_payload():
    payload = {"generic": "lisinopril", "strength_mg": 10}
    ddefn = JsonDictDefn(4, "lisinopril", payload)

    definition_id, term, raw_payload = ddefn.to_tsv().split("\t")

    assert definition_id == "4"
    assert term == "lisinopril"
    assert json.loads(raw_payload) == payload

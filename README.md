# ApproxaTrie

`ApproxaTrie` is a Python implementation of a compressed prefix trie for
efficient approximate matching of terms - such as personal names or
drug names - inside a text. It provides two classes: `ApproxRadixTrie`,
which finds terms in a document within a specified character-based
edit distance budget, and `WordApproxTrie`, which finds passages within
a specified word-based edit distance budget.

## What it does

The main API is `ApproxRadixTrie`, imported from the installed package as:

```python
from apxtrie import ApproxRadixTrie
```

A common use case is to find drugs in a passage (from extract_entities.py):

```
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
```    
    
## Project layout

- `src/apxtrie/` contains the installable `apxtrie` package.
- `tests/` contains the test suite.
- `resources/` contains the example dictionaries used by the scripts and tests.

## Highlights of the implementation

### Efficient approximate matching

The trie shares work across terms with common prefixes, so approximate search
can reject a nonmatching path as soon as its edit-distance budget is exhausted
rather than compare the query independently with every dictionary term. The
state cache also avoids revisiting the same trie position and input position
when it has already been searched with an equal or larger remaining budget.

### Compressed trie representation

`ApproxRadixTrie` uses path compression (a radix-trie optimization): each node
stores an entire unbranched character run rather than one
character. Nodes are split only where terms diverge, so the trie needs
fewer Python node objects and child containers than a
character-per-node trie. This memory reduction is the primary advantage of the
compressed representation. Children are sorted for binary-search
lookup, and approximate search still evaluates each character in a
compressed run.

The small scripts in the repository are demonstrations and data-processing
utilities. `print_apxtrie.py` exercises the character-based trie, while
`print_wdapxtrie.py` builds and queries the word-based trie.
`extract_entities.py` demonstrates character- and word-level entity extraction
and prints match offsets.

### Approximate-search cache

Approximate lookup enables a state cache by default (`is_cache_mode=True`). It
avoids re-exploring the same trie/input position when that state was already
searched with at least as much edit-distance budget, which reduces repeated
work. Set `is_cache_mode=False` to exhaustively explore match paths; this is
primarily useful when comparing or debugging the optimization.

```python
match = trie.find_approximate("tylenol pmx", edit_dist=1)
uncached_match = trie.find_approximate(
    "tylenol pmx", edit_dist=1, is_cache_mode=False
)
```

## Custom definition types

By default, `DictDefn` stores the definition as a plain string.  You can
subclass it to store any Python object — for example, a parsed JSON payload —
by overriding two hooks:

```python
import json
from apxtrie.dictdefn import DictDefn

class JsonDictDefn(DictDefn):
    def serialize_defn(self) -> str:
        return json.dumps(self.defn)   # called by trie.write()

    @classmethod
    def deserialize_defn(cls, raw: str):
        return json.loads(raw)         # called by trie.load_trie()
```

Pass the subclass when constructing the trie so that `add_definition()` and
`load_trie()` use it automatically:

```python
ptrie = ApproxRadixTrie(defn_class=JsonDictDefn)
ptrie.add_definition("tylenol pm", {
    "generic": "acetaminophen/diphenhydramine",
    "codes": ["N02BE01", "R06AA02"],
})
ptrie.write("my.trie")

ptrie2 = ApproxRadixTrie(defn_class=JsonDictDefn)
ptrie2.load_trie("my.trie")
result = ptrie2.find("tylenol pm")
print(result.defn["generic"])   # "acetaminophen/diphenhydramine"
```

The `.trie.dictdefn` file format is unchanged — the serialized form is whatever
`serialize_defn()` returns, which for `JsonDictDefn` is a JSON string.  Callers
that use plain-string definitions need no changes; the base class
`serialize_defn()` returns `str(self.defn)` and `deserialize_defn()` returns
the raw string.

See `tests/test_defn_str_serialize.py` and
`tests/test_defn_json_serialize.py` for end-to-end serialization examples.

## Input dictionary format

`ApproxRadixTrie` provides two loading methods:

- `load(path)` reads a source term/definition dictionary in the tab-separated
  format below.
- `load_trie(path)` restores a serialized trie written by `write()`, together
  with its `path.dictdefn` definition table.

`ApproxRadixTrie.load(path)` accepts a plain-text dictionary with one entry per
line.
Each entry must contain exactly two tab-separated fields:

```text
term<TAB>definition
```

For example:

```text
tylenol pm	acetaminophen|diphenhydramine
aspirin	acetylsalicylic acid
```

Blank lines and lines beginning with `##` are ignored. Leading and trailing
whitespace is removed from each line before it is split, so preserve meaningful
edge whitespace elsewhere if needed. Terms and definitions cannot contain tabs.
During loading, `~` in a term is converted to a space because `~` is the trie's
internal end-of-term marker.

`load()` is for source dictionaries only. A trie produced by `write()` must be
restored with `load_trie("path/to/file.trie")`.

`WordApproxTrie.wd_load(path)` accepts the same source-dictionary format. Its
serialized structure must use the `.wd_trie` suffix and be restored with
`wd_load_trie("path/to/file.wd_trie")`.

## Install and use

Create and activate an isolated virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Because the package uses a `src/` layout, install the checkout in editable mode
before running example scripts directly. For example:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python extract_entities.py
```

To install the optional test dependencies too:

```bash
python -m pip install -e '.[test]'
```

Example:

```python
from apxtrie import ApproxRadixTrie

trie = ApproxRadixTrie()
trie.load("resources/map6.phraseDirect2.dict.noRepeat")
match = trie.find("tylenol pm")
print(match.id, match.defn)
```

Run the example scripts from the repository root so their resource-file paths
resolve correctly.

## Tests currently available

The suite is written for `pytest` and lives in `tests/`.
After installing the project with its test extra, run the suite with:

```bash
pytest
```

## References

The approximate string-matching implementation integrates techniques from:

- Ternary Search Tree: Bentley and Sedgewick, [Fast Algorithms for Sorting and Searching Strings](https://sedgewick.io/wp-content/themes/sedgewick/papers/1998TSTsDobbs.pdf) (ternary search trees).
- Patricia Trie: Morrison, [PATRICIA—Practical Algorithm To Retrieve Information Coded in Alphanumeric](https://dl.acm.org/doi/pdf/10.1145/321479.321481) (PATRICIA tries).

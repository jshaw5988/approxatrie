"""Tests for Linux process-memory helpers."""


import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def memory_consumed_by(script):
    environment = os.environ.copy()
    source_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path if not existing_pythonpath
        else source_path + os.pathsep + existing_pythonpath
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=True,
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
    )
    return float(result.stdout)


def test_load():
    memory_used = memory_consumed_by(
        """
from apxtrie.linux_mem import memory_mb
from apxtrie.apxtrie import ApproxRadixTrie

start = memory_mb()
trie = ApproxRadixTrie()
for path in (
    "resources/map6.phraseDirect2.dict.noRepeat",
    "resources/ingredient.dict",
    "resources/acid.dict",
    "resources/ignore.dict",
):
    trie.load(path)
assert trie.find("tylenol pm").id == 8410
print(memory_mb(start))
"""
    )
    assert 10 < memory_used < 30



def test_load_trie(drug_trie, tmp_path):
    output_bname = "map7.trie"
    output_trie = str(tmp_path / output_bname)
    drug_trie.write(output_trie)

    memory_used = memory_consumed_by(
        f"""
from apxtrie.linux_mem import memory_mb
from apxtrie.apxtrie import ApproxRadixTrie

start = memory_mb()
trie = ApproxRadixTrie()
trie.load_trie("{tmp_path}/{output_bname}")
assert trie.find("tylenol pm").id == 8410
print(memory_mb(start))
"""
    )
    assert 0.5 < memory_used < 30

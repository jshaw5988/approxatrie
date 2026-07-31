import pytest


@pytest.mark.parametrize(
    ("term", "edit_distance", "expected_id"),
    [
        ("tixlenol pmx", 3, 8410),
        ("tixlenol pmx", 2, None),
        ("tiixlenol pmx", 4, 8410),
        ("tiixlenol pmx", 3, None),
        ("tiixleinol pmx", 5, 8410),
        ("tiixleinol pmx", 4, None),
    ],
)
def test_find_approximate_with_and_without_cache(
    drug_trie, term, edit_distance, expected_id
):
    uncached_result = drug_trie.find_approximate(
        term, edit_distance, is_cache_mode=False
    )
    cached_result = drug_trie.find_approximate(term, edit_distance, is_cache_mode=True)

    assert (None if uncached_result is None else uncached_result.id) == expected_id
    assert (None if cached_result is None else cached_result.id) == expected_id

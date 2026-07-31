"""Tests for tokenization and utility helpers."""

from apxtrie.util import (
    TokenType,
    get_space_indices,
    get_token_indices,
    get_token_type_indices,
    next_space_index,
    next_space_index_eq,
)


def test_get_space_indices():

    st = "hello, this is james"
    # idx_list = get_token_indices()
    idx_list = get_space_indices(st)
    start = 0
    for end in idx_list:
        print("'" + st[start:end] + "'")
        start = end + 1
    print("idx_list = " + str(idx_list))
    assert idx_list == [6, 11, 14, 20]


def test_next_space_index_uses_end_sentinel():
    idx_list = get_space_indices("one two")

    assert next_space_index(0, idx_list) == 3
    assert next_space_index(3, idx_list) == 7
    assert next_space_index_eq(3, idx_list) == 3
    assert next_space_index_eq(7, idx_list) == 7


def test_get_token_starts():
    st = "hello,        this is james."
    se_list = get_token_indices(st)
    for (start, end) in se_list:
        print("'" + st[start:end] + "'")
    print("start_end_list = " + str(se_list))

    assert se_list == [(0, 5), (14, 18), (19, 21), (22, 27)]

    st = "hello"
    se_list = get_token_indices(st)
    print("start_end_list = " + str(se_list))
    assert se_list == [(0, 5)]

    st = ""
    se_list = get_token_indices(st)
    print("start_end_list = " + str(se_list))
    assert not se_list

    st = "h"
    se_list = get_token_indices(st)
    print("start_end_list = " + str(se_list))
    assert se_list == [(0, 1)]

    st = "h james"
    se_list = get_token_indices(st)
    print("start_end_list = " + str(se_list))
    assert se_list == [(0, 1), (2, 7)]

    st = "h james "
    se_list = get_token_indices(st)
    print("start_end_list = " + str(se_list))
    assert se_list == [(0, 1), (2, 7)]

    st = "h james ."
    se_list = get_token_indices(st)
    print("start_end_list = " + str(se_list))
    assert se_list == [(0, 1), (2, 7)]


def test_get_token_type_indices():
    st = "hello,        this is james."
    setype_list = get_token_type_indices(st)
    for (start, end, token_type) in setype_list:
        print(f"[{st[start:end]}] ({start}, {end}) is {token_type}")
    print("start_end_type_list = " + str(setype_list))
    assert setype_list == [(0, 5, TokenType.LETTER),
                           (5, 6, TokenType.PUNCTUATION),
                           (6, 14, TokenType.SPACE),
                           (14, 18, TokenType.LETTER),
                           (18, 19, TokenType.SPACE),
                           (19, 21, TokenType.LETTER),
                           (21, 22, TokenType.SPACE),
                           (22, 27, TokenType.LETTER),
                           (27, 28, TokenType.PUNCTUATION)]

    st = "  hello,,, this!"
    setype_list = get_token_type_indices(st)
    for (start, end, token_type) in setype_list:
        print(f"[{st[start:end]}] ({start}, {end}) is {token_type}")
    print("start_end_type_list = " + str(setype_list))
    assert setype_list == [(0, 2, TokenType.SPACE),
                           (2, 7, TokenType.LETTER),
                           (7, 10, TokenType.PUNCTUATION),
                           (10, 11, TokenType.SPACE),
                           (11, 15, TokenType.LETTER),
                           (15, 16, TokenType.PUNCTUATION)]

    st = "  !"
    setype_list = get_token_type_indices(st)
    for (start, end, token_type) in setype_list:
        print(f"[{st[start:end]}] ({start}, {end}) is {token_type}")
    print("start_end_type_list = " + str(setype_list))
    assert setype_list == [(0, 2, TokenType.SPACE),
                           (2, 3, TokenType.PUNCTUATION)]

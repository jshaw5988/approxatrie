import operator
import re
import string
from enum import Enum


class TokenType(Enum):
    LETTER = 1
    SPACE = 2
    PUNCTUATION = 3

def normalize_spaces(st):
    st = st.strip()
    st = re.sub(r"\s+", " ", st)
    return st

def tokenize(st, sep, is_include_sep=False):
    """based on sep using regex"""
    return tokenize_by_pattern(st, re.compile(sep), is_include_sep)

def tokenize_by_pattern(st, sep_pattern, is_include_sep=False):
    """based on sep using compiled regex, to save some time"""
    result = []
    pat = sep_pattern
    prev = 0
    found = pat.search(st, prev)
    while found is not None:
        if prev < found.start():   # don't add empty
            result.append(st[prev:(found.start())])
        if is_include_sep:
            result.append(st[found.start():found.end()])
        prev = found.end()
        found = pat.search(st, prev)
    if prev < len(st):
        result.append(st[prev:])
    return result

def tokenize_pos(st, sep, is_include_sep=False):
    """ based on sep using regex, to save some time """
    return tokenize_pos_by_pattern(st, re.compile(sep), is_include_sep)

def tokenize_pos_by_pattern(st, sep_pattern, is_include_sep=False):
    """based on sep using compiled regex, to save some time"""
    result = []
    pat = sep_pattern
    prev = 0
    found = pat.search(st, prev)
    while found is not None:
        if prev < found.start():   # don't add empty
            result.append((prev, found.start(), st[prev:(found.start())]))
        if is_include_sep:
            result.append((found.start(), found.end(), st[found.start():found.end()]))
        prev = found.end()
        found = pat.search(st, prev)
    if prev < len(st):
        result.append((prev, len(st), st[prev:]))
    return result

def tokenize2(st, sep, is_include_sep=False):
    """ based on sep using string """
    result = []
    prev = 0
    found = st.find(sep, prev)
    while found != -1:
        result.append(st[prev:(found-prev)])
        if is_include_sep:
            result.append(sep)
        prev = found + 1
        found = st.find(sep, prev)
    if prev < len(st):
        result.append(st[prev:])
    return result

def get_space_indices(st):
    idx = 0
    idx_list = []
    try:
        while True:
            idx = st.index(' ', idx)
            idx_list.append(idx)
            idx += 1
    except ValueError:
        idx_list.append(len(st))
    return idx_list

punctuation_set = set(string.punctuation)
space_set = set(" \t\n\r")
space_punctuation_set = space_set.union(punctuation_set)

def get_token_indices(st, sep=None):
    start = -1
    st_len = len(st)
    is_prev_char_space = True
    if sep is None:
        sep_set = space_punctuation_set
    else:
        sep_set = set(sep)
    result = []
    for i in range(st_len):
        if st[i] in sep_set:
            if is_prev_char_space:
                start += 1
            else:
                result.append((start, i))
                start = i
                is_prev_char_space = True
        else:
            if is_prev_char_space:
                start = i
                is_prev_char_space = False
            else:
                pass
    if not is_prev_char_space:
        result.append((start, st_len))
    return result

def get_token_type_indices(st):
    start = -1
    st_len = len(st)
    prev_char_type = TokenType.SPACE
    result = []
    for i in range(st_len):
        if st[i] in space_set:
            if prev_char_type == TokenType.SPACE:
                start = max(start, 0)
            else:
                result.append((start, i, prev_char_type))
                start = i
            prev_char_type = TokenType.SPACE
        elif st[i] in punctuation_set:
            if prev_char_type == TokenType.PUNCTUATION:
                pass
            else:
                if start >= 0:
                    result.append((start, i, prev_char_type))
                start = i
            prev_char_type = TokenType.PUNCTUATION
        else:  # TokenType.LETTER
            if prev_char_type == TokenType.LETTER:
                pass
            else:
                if start >= 0:
                    result.append((start, i, prev_char_type))
                start = i
            prev_char_type = TokenType.LETTER
    if start != st_len:
        result.append((start, st_len, prev_char_type))
    return result

def next_token_type_index(token_type_indices, start_index, prev_token_end):
    num_tokens = len(token_type_indices)
    for i in range(start_index, num_tokens):
        (start, _end, _token_type) = token_type_indices[i]
        if start >= prev_token_end:
            return i
    return num_tokens

# return th end token st index > last_st_index
def next_token_end_index(token_type_indices, start_index, last_st_index):
    num_tokens = len(token_type_indices)
    for i in range(start_index, num_tokens):
        (start, end, _token_type) = token_type_indices[i]
        if start <= last_st_index <= end:
            return end
    return token_type_indices[num_tokens - 1][1]

# return (next_token_index, next_st_start)
def move_next_token_with_start(token_type_indices, start_index, prev_token_end):
    num_tokens = len(token_type_indices)
    for i in range(start_index, num_tokens):
        (start, end, _token_type) = token_type_indices[i]
        if start >= prev_token_end:
            return (i, start)
        if i == num_tokens -1:  # last one
            return (num_tokens, end)
    # for whatever reason, start_idnex >= num_tokens
    return (num_tokens, token_type_indices[num_tokens-1][1])

# return (next_token_index, next_st_start)
def move_next_token(token_type_indices, start_index):
    num_tokens = len(token_type_indices)
    if start_index + 1 == num_tokens:
        return (start_index + 1, token_type_indices[start_index][1])
    return (start_index + 1, token_type_indices[start_index + 1][0])


def get_next_non_space(st, start):
    st_length = len(st)
    while start < st_length:
        if st[start] != ' ':
            return start
        start += 1
    return -1

def chomp_with_indices(start, end, st):
    stlen = end-start
    i = 0
    while i<stlen:
        if st[i] != ' ':
            break
        i += 1
    j = stlen-1
    while j> 0:
        if st[j] != ' ':
            break
        j -= 1
    if i >= j:  # must be size 0
        return (start, start, "")
    return (start+i, start+j+1, st[i:j+1])

def next_space_index(start, idx_list):
    """Return the next space index, or the end-of-string sentinel."""
    for idx in idx_list:
        if idx > start:
            return idx
    return idx_list[-1]

def next_space_index_eq(start, idx_list):
    """Return the current/next space index, or the end-of-string sentinel."""
    for idx in idx_list:
        if idx >= start:
            return idx
    return idx_list[-1]

def print_dict_sort_by_value(adict):
    for k, v in sorted(adict.items(), key=operator.itemgetter(1)):
        print(str(k) + "\t" + str(v))

# assume st1 is the node
# and first char already matched
def prefix_overlap_1(st1, st2, start= 0):
    i = start
    len1 = len(st1)
    len2 = len(st2)
    while i < len1 and i < len2:
        if st1[i] != st2[i]:
            break
        i += 1
    return i


# pylint: disable=pointless-string-statement
"""
if __name__ == "__main__":
    st = "hello,        this is james."
    setype_list = get_token_type_indices(st)
    for (start, end, token_type) in setype_list:
        print(f"[{st[start:end]}] is {token_type}")
    print("start_end_type_list = " + str(setype_list))

    # st = "hello,        this is james."
    # se_list = get_token_indices(st)
    # print("start_end_list = " + str(se_list))
    # for (start, end) in se_list:
    #    print("[{}]".format(st[start:end]))
"""

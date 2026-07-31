"""Word-token trie with whole-word approximate matching."""

import json
from collections import deque

from apxtrie import util
from apxtrie.dictdefn import DictDefn


class _WdApxTrieNode:
    """A word-trie node with optional child and terminal-definition containers."""

    __slots__ = ("children", "dict_defn_list")

    def __init__(self):
        self.children = None
        self.dict_defn_list = None


class WordApproxTrie:
    """A trie that indexes terms by words and matches them by word edit distance."""

    def __init__(self, defn_class=None):
        self._root = _WdApxTrieNode()
        self._term_map = {}
        self._max_term_words = 0
        self.defn_class = defn_class or DictDefn
        self.defn_list = [DictDefn(0, "ignoreDictDefnTerm", "ignoreDictDefn")]
        self.num_defn = 0

    @staticmethod
    def _tokenize(st):
        """Split text into the word units used by word-distance matching."""
        return [st[start:end] for start, end in util.get_token_indices(st)]

    def prepare_wd_token_text(self, st):
        """Return punctuation-free word tokens as normalized, space-separated text."""
        return " ".join(self._tokenize(st))

    def wd_add_definition(self, term, definition):
        """Create and insert a definition, returning ``None`` for duplicate terms."""
        definition_id = self.num_defn + 1
        dict_defn = self.defn_class(definition_id, term, definition)
        if not self.wd_insert(term, dict_defn):
            return None
        self.num_defn = definition_id
        self.defn_list.append(dict_defn)
        return dict_defn

    def wd_insert(self, term, dict_defn):
        """Insert a preconstructed definition under its sequence of word tokens."""
        if term in self._term_map:
            return False

        term_words = self._tokenize(term)
        self._max_term_words = max(self._max_term_words, len(term_words))
        node = self._root
        for word in term_words:
            if node.children is None:
                node.children = {}
            node = node.children.setdefault(word, _WdApxTrieNode())
        if node.dict_defn_list is None:
            node.dict_defn_list = []
        node.dict_defn_list.append(dict_defn)
        self._term_map[term] = dict_defn
        return True

    def wd_load(self, file_name):
        """Load tab-separated term/definition entries into the word trie."""
        with open(file_name, "r", encoding="utf-8") as infile:
            for line in infile:
                line = line.rstrip("\r\n")
                if not line or line.startswith("##"):
                    continue
                term, definition = line.split("\t", 1)
                self.wd_add_definition(term, definition)

    def wd_find_approximate(self, st, edit_dist=0):
        """Return the best definition within ``edit_dist`` whole-word edits."""
        candidates = self.wd_find_approximate_candidates(st, edit_dist=edit_dist)
        if not candidates:
            return None
        return min(candidates, key=lambda candidate: candidate[1])[2]

    def wd_find_approximate_candidates(self, st, edit_dist=0):
        """Return ``(edits_left, edit_cost, definition, operations)`` candidates."""
        if edit_dist < 0:
            return []

        query_words = self._tokenize(st)
        initial_row = list(range(len(query_words) + 1))
        candidates = []
        self._collect_candidates(self._root, query_words, initial_row, [], edit_dist,
                                 candidates)
        return candidates

    def wd_substr_search(self, st, edit_dist=0, terms=None):
        """Find word-trie terms in text, preserving original character offsets.

        Each result is ``(cost, start, end, edits_left, definition, operations)``.
        ``start`` and ``end`` index the original, unnormalized text.
        The first word must match the first word of a dictionary term exactly.
        Set ``terms`` to an iterable of known dictionary terms to restrict an
        edit-distance substring search to those terms.
        """
        if edit_dist < 0:
            return []
        tokens = [(st[start:end], start, end) for start, end in util.get_token_indices(st)]
        if terms is not None:
            matches = self._filtered_substr_matches(tokens, edit_dist, terms)
            return self._post_process_substr_matches(matches)
        if edit_dist == 0:
            return self._post_process_substr_matches(self._exact_substr_matches(tokens))

        matches = []
        max_window_words = self._max_term_words + edit_dist
        for token_index, (_word, start, _end) in enumerate(tokens):
            if not self._root.children or tokens[token_index][0] not in self._root.children:
                continue
            token_window = tokens[token_index:token_index + max_window_words]
            query_words = [word for word, _start, _end in token_window]
            initial_row = list(range(len(query_words) + 1))
            first_word = query_words[0]
            first_row = self._next_row(initial_row, query_words, first_word)
            self._collect_substr_candidates(
                self._root.children[first_word], query_words, first_row, [first_word], token_window,
                start,
                edit_dist, matches,
            )
        return self._post_process_substr_matches(matches)

    def wd_write(self, file_name):
        """Write a ``.wd_trie`` structure file and its definition sidecar."""
        self._validate_file_name(file_name)
        self._write_definitions(file_name + ".dictdefn")

        pending_nodes = deque([(self._root, 0, -1, "")])
        next_node_id = 1
        with open(file_name, "w", encoding="utf-8") as outfile:
            while pending_nodes:
                node, node_id, parent_id, word = pending_nodes.popleft()
                definition_ids = [dict_defn.id for dict_defn in node.dict_defn_list or []]
                outfile.write(
                    f"{node_id}\t{parent_id}\t{json.dumps(word)}\t"
                    f"{json.dumps(definition_ids)}\n"
                )
                if node.children:
                    for child_word, child in node.children.items():
                        pending_nodes.append((child, next_node_id, node_id, child_word))
                        next_node_id += 1

    def wd_load_trie(self, file_name):
        """Load a ``.wd_trie`` structure file and its definition sidecar."""
        self._validate_file_name(file_name)
        self._load_definitions(file_name + ".dictdefn")
        definitions_by_id = {dict_defn.id: dict_defn for dict_defn in self.defn_list}
        nodes = {}
        with open(file_name, "r", encoding="utf-8") as infile:
            for line in infile:
                node_id, parent_id, raw_word, raw_definition_ids = line.rstrip("\n").split("\t")
                node = _WdApxTrieNode()
                nodes[int(node_id)] = node
                definition_ids = json.loads(raw_definition_ids)
                if definition_ids:
                    node.dict_defn_list = [definitions_by_id[definition_id]
                                           for definition_id in definition_ids]

                parent_id = int(parent_id)
                if parent_id == -1:
                    self._root = node
                else:
                    parent = nodes[parent_id]
                    if parent.children is None:
                        parent.children = {}
                    parent.children[json.loads(raw_word)] = node
        self._term_map = {dict_defn.term: dict_defn for dict_defn in self.defn_list[1:]}

    def wd_print_trie(self):
        """Print every node in the word trie, including terminal definitions."""
        lines = []
        self._append_print_lines(self._root, "root", 0, lines)
        for line in lines:
            print(line)

    def _write_definitions(self, file_name):
        with open(file_name, "w", encoding="utf-8") as outfile:
            outfile.writelines(f"{dict_defn.id}\t{dict_defn.term}\t{dict_defn.serialize_defn()}\n"
                               for dict_defn in self.defn_list[1:])

    def _load_definitions(self, file_name):
        self.defn_list = [DictDefn(0, "ignoreDictDefnTerm", "ignoreDictDefn")]
        self.num_defn = 0
        self._max_term_words = 0
        with open(file_name, "r", encoding="utf-8") as infile:
            for line in infile:
                definition_id, term, raw_definition = line.rstrip("\n").split("\t")
                definition_id = int(definition_id)
                self.num_defn = max(self.num_defn, definition_id)
                self._max_term_words = max(self._max_term_words, len(self._tokenize(term)))
                self.defn_list.append(self.defn_class(
                    definition_id, term, self.defn_class.deserialize_defn(raw_definition)
                ))

    @staticmethod
    def _validate_file_name(file_name):
        if not file_name.endswith(".wd_trie"):
            raise ValueError("word-trie files must end with '.wd_trie'")

    def _append_print_lines(self, node, word, depth, lines):
        line = "|--" * depth + word
        if node.dict_defn_list:
            line += ": " + ", ".join(str(dict_defn) for dict_defn in node.dict_defn_list)
        lines.append(line)
        if node.children:
            for child_word, child in sorted(node.children.items()):
                self._append_print_lines(child, child_word, depth + 1, lines)

    def _exact_substr_matches(self, tokens):
        matches = []
        for token_index, (_word, start, _end) in enumerate(tokens):
            node = self._root
            for current_index in range(token_index, len(tokens)):
                word, _current_start, end = tokens[current_index]
                if not node.children or word not in node.children:
                    break
                node = node.children[word]
                if node.dict_defn_list:
                    operations = "M" * (current_index - token_index + 1)
                    for dict_defn in node.dict_defn_list:
                        matches.append((0, start, end, 0, dict_defn, operations))
        return matches

    def _filtered_substr_matches(self, tokens, edit_dist, terms):
        matches = []
        for term in terms:
            dict_defn = self._term_map.get(term)
            if dict_defn is None:
                continue
            term_words = self._tokenize(term)
            if not term_words:
                continue
            min_query_words = max(1, len(term_words) - edit_dist)
            max_query_words = len(term_words) + edit_dist
            for token_index, (_word, start, _end) in enumerate(tokens):
                if tokens[token_index][0] != term_words[0]:
                    continue
                token_window = tokens[token_index:token_index + max_query_words]
                for query_length in range(min_query_words, len(token_window) + 1):
                    query_words = [word for word, _start, _end in token_window[:query_length]]
                    edit_cost = self._edit_cost(query_words, term_words)
                    if edit_cost <= edit_dist:
                        end = token_window[query_length - 1][2]
                        operations = self._edit_operations(query_words, term_words)
                        matches.append((edit_cost, start, end, edit_dist - edit_cost,
                                        dict_defn, operations))
        return matches

    @staticmethod
    def _post_process_substr_matches(matches):
        """Keep the best boundary-anchored match for each definition and start.

        A one-word exact prefix is also retained when all remaining dictionary
        words are deleted, such as ``"tylenol"`` matching ``"tylenol extra
        strength"`` with a cost of two.
        """
        best_matches = {}
        for match in matches:
            edit_cost, start, end, _edits_left, dict_defn, operations = match
            is_single_word_prefix = (
                operations.startswith("M")
                and operations.count("M") == 1
                and set(operations) <= {"M", "I"}
            )
            if not operations.startswith("M") or (
                not operations.endswith("M") and not is_single_word_prefix
            ):
                continue
            key = (start, dict_defn.id)
            current_match = best_matches.get(key)
            if current_match is None or (edit_cost, -end) < (
                current_match[0], -current_match[2]
            ):
                best_matches[key] = match
        return sorted(best_matches.values(), key=lambda match: (match[1], match[2], match[4].id))

    def _collect_substr_candidates(self, node, query_words, row, term_words,
                                   token_window, start, edit_dist, matches):
        if node.dict_defn_list:
            for query_length, edit_cost in enumerate(row[1:], start=1):
                if edit_cost <= edit_dist:
                    operations = self._edit_operations(query_words[:query_length], term_words)
                    end = token_window[query_length - 1][2]
                    for dict_defn in node.dict_defn_list:
                        matches.append((edit_cost, start, end, edit_dist - edit_cost,
                                        dict_defn, operations))

        if node.children:
            for word, child in node.children.items():
                next_row = self._next_row(row, query_words, word)
                if min(next_row) <= edit_dist:
                    self._collect_substr_candidates(
                        child, query_words, next_row, term_words + [word], token_window,
                        start, edit_dist, matches,
                    )

    def _collect_candidates(self, node, query_words, row, term_words, edit_dist, candidates):
        edit_cost = row[-1]
        if node.dict_defn_list and edit_cost <= edit_dist:
            operations = self._edit_operations(query_words, term_words)
            for dict_defn in node.dict_defn_list:
                candidates.append((edit_dist - edit_cost, edit_cost, dict_defn, operations))

        if node.children:
            for word, child in node.children.items():
                next_row = self._next_row(row, query_words, word)
                if min(next_row) <= edit_dist:
                    self._collect_candidates(child, query_words, next_row,
                                             term_words + [word], edit_dist, candidates)

    @staticmethod
    def _next_row(previous_row, query_words, word):
        next_row = [previous_row[0] + 1]
        for query_index, query_word in enumerate(query_words, start=1):
            substitution_cost = 0 if word == query_word else 1
            next_row.append(min(
                previous_row[query_index] + 1,
                next_row[query_index - 1] + 1,
                previous_row[query_index - 1] + substitution_cost,
            ))
        return next_row

    @staticmethod
    def _edit_cost(query_words, term_words):
        row = list(range(len(query_words) + 1))
        for word in term_words:
            row = WordApproxTrie._next_row(row, query_words, word)
        return row[-1]

    @staticmethod
    def _edit_operations(query_words, term_words):
        """Return one minimal word-edit operation string for a candidate."""
        rows = [list(range(len(query_words) + 1))]
        for word in term_words:
            rows.append(WordApproxTrie._next_row(rows[-1], query_words, word))

        operations = []
        term_index = len(term_words)
        query_index = len(query_words)
        while term_index or query_index:
            if term_index and query_index:
                is_match = term_words[term_index - 1] == query_words[query_index - 1]
                substitution_cost = 0 if is_match else 1
                if rows[term_index][query_index] == (
                    rows[term_index - 1][query_index - 1] + substitution_cost
                ):
                    operations.append("M" if is_match else "S")
                    term_index -= 1
                    query_index -= 1
                    continue
            if term_index and (
                rows[term_index][query_index] == rows[term_index - 1][query_index] + 1
            ):
                operations.append("I")
                term_index -= 1
            else:
                operations.append("D")
                query_index -= 1
        return "".join(reversed(operations))

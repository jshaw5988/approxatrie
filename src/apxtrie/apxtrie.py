from __future__ import annotations

import logging
import logging.config
import operator
import sys
import time
from pathlib import Path

from apxtrie import util
from apxtrie.dictdefn import DictDefn
from apxtrie.apxtrienode import ApxTrieNode

_LOGGING_CONFIG = Path(__file__).resolve().parents[2] / "logging.conf"
if _LOGGING_CONFIG.is_file():
    logging.config.fileConfig(_LOGGING_CONFIG, disable_existing_loggers=False)

# create logger
logger = logging.getLogger(__name__)

IS_DEBUG = False
IS_GLOBAL_DEBUG = False

# end of term character
EO_TERM = "~"


def update_prefix_count_map(prefix_count_map, node_id, node_st_start, st_start, edist_left):
    min_needed_edist_left = prefix_count_map.get((node_id, node_st_start, st_start))
    if min_needed_edist_left is None:
        prefix_count_map[(node_id, node_st_start, st_start)] = edist_left
    else:
        if edist_left > min_needed_edist_left:
            prefix_count_map[(node_id, node_st_start, st_start)] = edist_left
    # no need to update prefix-count_map


class ApproxRadixTrie:
    phraseCounter = 0
    num_op = 0   # only for debug purpose

    def __init__(self, defn_class=None):
        self.root_map = {}
        self.initialized = False
        self.num_defn = 0
        self.defn_class = defn_class or DictDefn
        self.defn_list = []
        self.defn_list.append(DictDefn(0, "ignoreDictDefnTerm", "ignoreDictDefn"))  # first 0 index

    def get(self, st):
        return self.find(st)

    def put(self, st, defn):
        return self.insert(st, defn)

    def add_definition(self, term, definition):
        """Create, register, and insert a definition for ``term``.

        Definition IDs are allocated by the trie because they are used as
        indexes in its serialized definition table. Returns ``None`` if the
        term is already present.
        """
        next_definition_id = self.num_defn + 1
        dict_defn = self.defn_class(next_definition_id, term, definition)
        if not self.insert(term, dict_defn):
            return None

        self.num_defn = next_definition_id
        self.defn_list.append(dict_defn)
        return dict_defn

    def insert(self, st, defn):
        st += EO_TERM  # add end-of-term character
        trie_root = self.root_map.get(st[0])
        if trie_root is None:
            self.root_map[st[0]] = ApxTrieNode(st, defn)
            self.initialized = False
            ApproxRadixTrie.phraseCounter += 1
            return True
        try:
            self.__insert(trie_root, st, defn)
        except IndexError:
            sys.stderr.write("duplicate entry: '" + st + "'\n")
            return False
        self.initialized = False
        ApproxRadixTrie.phraseCounter += 1
        return True

    def __insert(self, node, st, defn, depth=0):
        node_length = len(node.st)
        # first one is always matched already
        i = util.prefix_overlap_1(node.st, st, 1)

        if IS_DEBUG:
            logger.debug("%s__insert(%s) called, i=%s, node_length=%s", "  " * depth,
                         st, i, node_length)
            logger.debug("%snode=%r, %r", "  " * depth, node.st, node.dict_defn)

        # check if current node have the same prefix
        # if not
        if i < node_length:  # need split
            nst1 = node.st[:i]
            nst2 = node.st[i:]
            st2 = st[i:]

            copied_node = node.make_copy(nst2)
            node.reset_defn_child(nst1, st2[0], ApxTrieNode(st2, defn))
            node.update_child(nst2[0], copied_node)
        elif i == node_length: # no need to split, but need to insert to child
            if i < len(st):
                child = node.find_child(st[i])
                if child is None:
                    node.update_child(st[i], ApxTrieNode(st[i:], defn))
                    # node.chil_hash[st[i]]= ApxTrieNode(st[i:],defn)
                else:
                    self.__insert(child, st[i:], defn)
            else:
                raise IndexError

    #
    # returns DictDefn or None
    #
    def find(self, st):
        if not self.initialized:
            self.sort_children()
        st += EO_TERM  # add end-of-term character
        # no need to insert the last char, since prefix
        trie_root = self.root_map.get(st[0])
        if not trie_root:
            return None
        return self.__find(trie_root, st)

    #
    # returns DictDefn or None
    #
    def __find(self, node, st):
        node_length = len(node.st)
        # first one is always matched already
        i = util.prefix_overlap_1(node.st, st, 1)

        # check if current node have the same prefix
        # if not
        if i < node_length:  # inside the node, failed
            return None
        if i == node_length: # have same length,
            if i == len(st):   # finished st match
                return node.dict_defn
            child = node.binsearch_child(st[i])
            if not child:
                return None
            return self.__find(child, st[i:])
        return None

    #
    # returns a list of DictDefn, [] if empty
    #
    def find_prefix(self, st):
        if not self.initialized:
            self.sort_children()
        # no need to insert the last char, since prefix
        trie_root = self.root_map.get(st[0])
        if not trie_root:
            return []
        return self.__find_prefix(trie_root, st)

    #
    # returns a list of DictDefn, [] if empty
    #
    def __find_prefix(self, node, st) -> list[DictDefn]:
        if not node:
            return []
        # print "__find_prefix(" + node.st + "," + st + ")"
        node_length = len(node.st)
        # first one is always matched already
        i = util.prefix_overlap_1(node.st, st, 1)

        # check if current node have the same prefix
        # if not
        if i < node_length:  # inside the node, return all children
            if len(st) != i:
                return []
            return node.get_decendent_defn()
        if i == node_length: # no need to split, but need to insert to child
            if i >= len(st):
                return node.get_decendent_defn()
            child = node.binsearch_child(st[i])
            return self.__find_prefix(child,st[i:])
        return []

    #
    # return the best candidate, DictDefn
    #
    def find_approximate(self, st, edit_dist=0, is_cache_mode=True, is_debug=False):
        edist_defn_list = self.find_approximate_candidates(st, edit_dist=edit_dist,
                                                           is_cache_mode=is_cache_mode,
                                                           is_debug=is_debug)

        print("edist_defn_list = " + str(edist_defn_list))
        # take the one with smallest edit distance
        if not edist_defn_list:
            return None

        min_edit_dist = 1000
        min_defn = None
        for _edist_left, edist_cost, defn, _operation_string in edist_defn_list:
            if edist_cost < min_edit_dist:
                min_edit_dist = edist_cost
                min_defn = defn
        return min_defn

    #
    # return list of tuples:
    # (edist_left: int, edist_cost : int, node.dict_defn: DictDefn, oprSt: str)
    #
    def find_approximate_candidates(self, st, edit_dist=0, is_cache_mode=True,
                                    is_debug=False):
        ApproxRadixTrie.num_op = 0
        if is_debug:
            logger.debug("find_approximate(%s, %s)", st, edit_dist)
        if edit_dist == 0:          # an optimization
            dict_defn = self.find(st)
            return [(0, 0, dict_defn, "M" * len(st))]

        st += EO_TERM
        edist_defn_list = []
        # prefix_count_map = defaultdict(int)  # debug purpose
        prefix_count_map = {}
        # 'ch' in self.root_map is not needed
        for trie_root in self.root_map.values():
            edist_defn_list.extend(
                self.__find_approximate(node=trie_root,
                                        node_st_start=0,
                                        st=st,
                                        st_start=0,
                                        edist_left=edit_dist,
                                        edist_cost=0,
                                        depth=0,
                                        op_st="",
                                        prefix_count_map=prefix_count_map,
                                        node_path="",
                                        is_cache_mode=is_cache_mode,
                                        is_debug=is_debug))

        if is_debug:
            logger.debug("edist_defn_list=%s", edist_defn_list)
            for prefix, count in sorted(prefix_count_map.items(), key=operator.itemgetter(1)):
                print("prefix_count_map[" + str(prefix) + "] = " + str(count))

        return edist_defn_list

    #
    # return list of tuples:
    # (edist_left: int, edist_cost : int, node.dict_defn: DictDefn, oprSt: str)
    #
    def __find_approximate(self, node, node_st_start, st, st_start,
                           edist_left, edist_cost, depth, op_st,
                           prefix_count_map, node_path,
                           is_cache_mode=True, is_debug=False):
        if is_debug:
            print("|--" * depth + "__find_approximate(node.id=" + str(node.id) + \
                  ", node.st=" + node.st + ", " + node.st[node_st_start:] +
                  ", st=" + st + "," + st[st_start:] +", ed_left=" + str(edist_left) +
                  ", ed_cost=" + str(edist_cost) + ", node_path=" + node_path + \
                  ", opSt=" + op_st + ")")
        ApproxRadixTrie.num_op += 1

        # if edist_left < 0:
        #    return []
        node_st_length = len(node.st)

        if node.st[node_st_start] == st[st_start]:
            adjusted_edist_left = edist_left
        else:
            adjusted_edist_left = edist_left - 1

        if adjusted_edist_left < 0:
            return []

        if is_debug:
            node_path += f"{node.id}-{node_st_start}-{adjusted_edist_left}-{op_st}" + " -> "

        if is_cache_mode:
            min_needed_edist_left = prefix_count_map.get((node.id, node_st_start, st_start))
            if min_needed_edist_left is not None and \
               adjusted_edist_left <= min_needed_edist_left:
                if is_debug:
                    print("|--" * depth + "return reject xcache [], " + \
                          str((node.id, node_st_start, adjusted_edist_left)))
                return []

        edit_defn_list= []

        if node_st_start + 1 != node_st_length:  # inside the node still
            if st_start + 1 == len(st):   # finished st match
                # now, everything left in node.st must be deleted
                num_del = node_st_length - node_st_start - 1
                if is_debug:
                    print("|--" * depth + "adjusted_edist_left= %d, edist_cost=%d, numDel= %d")
                # not adjusted_edist_left, because it is already del'ed
                if node.dict_defn is not None and edist_left - num_del >= 0:
                    if is_debug:
                        print("|--" * depth + "return x1 " + \
                              str([(adjusted_edist_left, edist_cost,
                                    node.dict_defn, op_st+("x" * num_del))]))
                    return [(adjusted_edist_left, edist_cost + num_del,
                             node.dict_defn, op_st+("x" * num_del))]

                if is_debug:
                    print("|--" * depth + "return x1 [], add_prefix_count[" + \
                          str((node.id, node_st_start, st_start, edist_left)) + "]")
                if adjusted_edist_left >= 0:
                    update_prefix_count_map(prefix_count_map,
                                            node.id, node_st_start, st_start,
                                            adjusted_edist_left)
                return []

            if edist_left == adjusted_edist_left:
                edit_defn_list.extend(
                    self.__find_approximate(node, node_st_start+1, st, st_start+1,
                                            adjusted_edist_left, edist_cost, depth+1, op_st+"m",
                                            prefix_count_map, node_path,
                                            is_cache_mode=is_cache_mode, is_debug=is_debug))
            else:
                # try deletion, st advances, not node
                edit_defn_list.extend(
                    self.__find_approximate(node, node_st_start, st, st_start+1,
                                            adjusted_edist_left, edist_cost+1, depth+1, op_st+"d",
                                            prefix_count_map, node_path,
                                            is_cache_mode=is_cache_mode, is_debug=is_debug))
                # try substitution, both chars advance
                edit_defn_list.extend(
                    self.__find_approximate(node, node_st_start+1, st, st_start+1,
                                            adjusted_edist_left, edist_cost+1, depth+1, op_st+"s",
                                            prefix_count_map, node_path,
                                            is_cache_mode=is_cache_mode, is_debug=is_debug))
                # try insertion, node advances
                edit_defn_list.extend(
                    self.__find_approximate(node, node_st_start+1, st, st_start,
                                            adjusted_edist_left, edist_cost+1, depth+1, op_st+"i",
                                            prefix_count_map, node_path,
                                            is_cache_mode=is_cache_mode, is_debug=is_debug))

        else:  # exhausted the node st

            if st_start + 1 == len(st):   # finished st match
                if node.dict_defn is not None:
                    if is_debug:
                        print("|--" * depth + "return x2 " + \
                              str([(adjusted_edist_left, edist_cost, node.dict_defn, op_st)]))
                    return [(adjusted_edist_left, edist_cost, node.dict_defn, op_st)]

                if is_debug:
                    print("|--" * depth + "return x2 [], add_prefix_count[" + \
                          str((node.id, node_st_start, st_start, edist_left)) + "]")
                if adjusted_edist_left >= 0:
                    update_prefix_count_map(prefix_count_map, node.id, node_st_start,
                                            st_start, adjusted_edist_left)
                return []

            if edist_left == adjusted_edist_left:
                for _ch, child in node.get_children():
                    # matched, both chars are advanced
                    edit_defn_list.extend(
                        self.__find_approximate(child, 0, st, st_start+1,
                                                adjusted_edist_left, edist_cost, depth+1, op_st+"M",
                                                prefix_count_map, node_path,
                                                is_cache_mode=is_cache_mode, is_debug=is_debug))
            else:
                # try deletion, st advances, not node
                edit_defn_list.extend(
                    self.__find_approximate(node, node_st_start, st, st_start+1,
                                            adjusted_edist_left, edist_cost+1, depth+1, op_st+"D",
                                            prefix_count_map, node_path,
                                            is_cache_mode=is_cache_mode, is_debug=is_debug))
                for _ch, child in node.get_children():
                    # try substitution, both chars are advanced
                    edit_defn_list.extend(
                        self.__find_approximate(child, 0, st, st_start+1,
                                                adjusted_edist_left, edist_cost+1, depth, op_st+"S",
                                                prefix_count_map, node_path,
                                                is_cache_mode=is_cache_mode, is_debug=is_debug))
                    # try insertion, node advances
                    edit_defn_list.extend(
                        self.__find_approximate(child, 0, st, st_start,
                                                adjusted_edist_left, edist_cost+1, depth, op_st+"I",
                                                prefix_count_map, node_path,
                                                is_cache_mode=is_cache_mode, is_debug=is_debug))

        if not edit_defn_list:
            if is_debug:
                print("|--" * depth + "return x4 [], add_prefix_count[" + \
                      str((node.id, node_st_start, st_start, edist_left)) + "]")
            if adjusted_edist_left >= 0:
                update_prefix_count_map(prefix_count_map, node.id, node_st_start,
                                        st_start, adjusted_edist_left)
        else:
            if is_debug:
                print("|--" * depth + "return x4, edit_defn_list = " + str(edit_defn_list))
        return edit_defn_list


# returns (tmp_cost, tmp_end, tmp_edist_left, defn, op_st, dict_st)
    def __substr_search(self, node, node_st_start, st, st_start,
                        edist_left, edist_cost, depth,
                        token_type_indices, token_index, result_list,
                        op_st, dict_st,
                        # TODO, verify if 'is_cache_mode' is really not used
                        # pylint: disable=unused-argument
                        is_cache_mode=True, is_debug= False):

        if is_debug:
            logger.debug("|--" * depth)
            logger.debug("__substr_search(%s, %s, %s, %s, %s, %r, dict_st=%r)",
                         node.st, node.st[node_st_start:], st, st[st_start:], edist_left,
                         op_st, dict_st)

        if st_start >= len(st):  # exhausted st
            return []

        # reached a terminal node
        if node.st[node_st_start] == EO_TERM:
            # next_token_end = token_type_indices[token_index][1]
            next_token_end = util.next_token_end_index(token_type_indices, token_index, st_start)
            if next_token_end - st_start <= edist_left:
                num_del = next_token_end - st_start
                if is_debug:
                    logger.debug("|--" * depth)
                    logger.debug("******** added %r, edist_left=%s, num_del=%s ******",
                                 node.dict_defn, edist_left, num_del)
                result_list.append((edist_cost + num_del, next_token_end, edist_left,
                                    node.dict_defn, op_st + ("x" * num_del), dict_st))
        else:
            node_st_length = len(node.st)

            if node.st[node_st_start] == st[st_start]:
                adjusted_edist_left = edist_left
            else:
                adjusted_edist_left = edist_left - 1

            if is_debug:
                logger.debug("adjusted_edist_left=%s", adjusted_edist_left)

            if adjusted_edist_left >= 0:
                if node_st_start + 1 != node_st_length:  # inside the node still
                    if edist_left == adjusted_edist_left:
                        self.__substr_search(node, node_st_start+1, st, st_start+1,
                                             adjusted_edist_left, edist_cost, depth+1,
                                             token_type_indices, token_index,
                                             result_list, op_st+"m", dict_st+node.st[node_st_start])
                    else:
                        # try deletion,  st advances,  not node
                        self.__substr_search(node, node_st_start, st, st_start+1,
                                             adjusted_edist_left, edist_cost+1, depth+1,
                                             token_type_indices, token_index,
                                             result_list, op_st+"d", dict_st)
                        # try substitution,  both chars advance
                        self.__substr_search(node, node_st_start+1, st, st_start+1,
                                             adjusted_edist_left, edist_cost+1, depth+1,
                                             token_type_indices, token_index,
                                             result_list, op_st+"s", dict_st+node.st[node_st_start])
                        # try insertion,  node advances
                        self.__substr_search(node, node_st_start+1, st, st_start,
                                             adjusted_edist_left, edist_cost+1, depth+1,
                                             token_type_indices, token_index,
                                             result_list, op_st+"i", dict_st+node.st[node_st_start])

                else:  # exhausted the node st
                    if edist_left == adjusted_edist_left:
                        for _ch, child in node.get_children():
                            # matched,  both chars are advanced
                            self.__substr_search(child, 0, st, st_start+1,
                                                 adjusted_edist_left, edist_cost, depth+1,
                                                 token_type_indices, token_index,
                                                 result_list, op_st+"M",
                                                 dict_st+node.st[node_st_start])
                    else:
                        # try deletion,  st advances,  not node
                        self.__substr_search(node, node_st_start, st, st_start+1,
                                             adjusted_edist_left, edist_cost+1, depth+1,
                                             token_type_indices, token_index,
                                             result_list, op_st+"D", dict_st)
                        for _ch, child in node.get_children():
                            # try substitution,  both chars are advanced
                            self.__substr_search(child, 0, st, st_start+1,
                                                 adjusted_edist_left, edist_cost+1, depth+1,
                                                 token_type_indices, token_index,
                                                 result_list, op_st+"S",
                                                 dict_st+node.st[node_st_start])
                            # try insertion,  node advances
                            self.__substr_search(child, 0, st, st_start,
                                                 adjusted_edist_left, edist_cost+1, depth+1,
                                                 token_type_indices, token_index,
                                                 result_list, op_st+"I",
                                                 dict_st+node.st[node_st_start])

        if is_debug:
            sys.stdout.write("|--" * depth)
            print("return x1")
        return result_list


    def substr_search(self, st, edist_left, is_debug=False):
        if st is None or st.strip() == "":
            return []
        # spaceIdxList = util.getSpaceIndeces(st)
        token_type_pos_list = util.get_token_type_indices(st)
        if is_debug:
            logger.debug("substr_search(%s, %s)", st, edist_left)
            logger.debug("token_indices=%s", token_type_pos_list)

        stlen = len(st)   # don't count the padded char
        st += EO_TERM
        final_list = []
        # num_tokens = len(token_type_pos_list)
        token_index = 0
        start = token_type_pos_list[token_index][0]  # must exist because st is not ""

        while  start < stlen:
            # print "substr_search(" + st[start:] + "," + str(edist_left) +")"
            # self.__substr_search(self.root, st, start, 0, idx_list, result_list, "fs")
            token_type = token_type_pos_list[token_index][2]
            if token_type in (util.TokenType.PUNCTUATION, util.TokenType.SPACE):
                (token_index, start) = util.move_next_token(token_type_pos_list, token_index)
                # move to the next token if space or punctuation
                continue

            # for edist_left != 0
            edist_defn_list= []
            # 'ch' in self.root_map is never used
            for trie_root in self.root_map.values():
                self.__substr_search(node=trie_root,
                                     node_st_start=0,
                                     st=st,
                                     st_start=start,
                                     edist_left=edist_left,
                                     edist_cost=0,
                                     depth=0,
                                     token_type_indices=token_type_pos_list,
                                     token_index=token_index,
                                     result_list=edist_defn_list,
                                     op_st="",
                                     dict_st="",
                                     is_cache_mode=False,
                                     is_debug=False)

            # self.__substr_search(self.root, st, start, edist_left, 0, idx_list, result_list, "fs")

            if is_debug:
                print("edist_defn_list= " + str(edist_defn_list))
            max_len = start
            for (tmp_cost, tmp_end, tmp_edist, defn, operation_string,
                 dict_string) in sorted(edist_defn_list):
                # skip those short terms with any cost
                if tmp_end - start < 5 and tmp_cost != 0:
                    continue
                final_list.append((tmp_cost, start, tmp_end, tmp_edist, defn,
                                   operation_string, dict_string))
                # print str((defn, start, tmpEnd, tmpDist))
                max_len = max(max_len, tmp_end)

            # logger.debug("start=%s, max_len=%s", start, max_len)

            if max_len == stlen:
                break
            if start == max_len:   # no match
                # this is somewhat inefficient, didn't remember from last
                # location
                final_list.append(
                    (-1, start, token_type_pos_list[token_index][1], -1, 0, "", "")
                )
                # start = util.next_space_index(start, space_idx_list) + 1
                (token_index, start) = util.move_next_token(token_type_pos_list, token_index)
            else:
                # token_index = util.next_token_type_index(token_type_pos_list, token_index, maxLen)
                (token_index, start) = util.move_next_token_with_start(token_type_pos_list,
                                                                       token_index, max_len)

            # if token_index < num_tokens:
            #    start = token_type_pos_list[token_index][0]
            #else:
            #    start = stlen
        if is_debug:
            for (cost, start, end, x_edist_left, defn, _operation_string,
                 _dict_string) in final_list:
                logger.debug("candidate %s, %r => %r", (cost, start, end, x_edist_left, defn),
                             st[start:end], defn)
        unique_list = get_longest_st_min_cost(final_list)
        #for (defn, start, end, dist) in unique_list:
        # print str(defn) + " y(" + self.dict[defn] + ")"
        return unique_list

    def substr_search_dist_filter(self, st, skip_word_dict=None):
        if skip_word_dict is None:
            skip_word_dict = set()
        is_debug= False
        if IS_GLOBAL_DEBUG:
            is_debug= True
        edist_left= 2

        token_type_pos_list = util.get_token_type_indices(st)
        if is_debug:
            # self.myPrint()
            logger.debug("substr_search_dist_filter(%s, %s)", st, edist_left)
            logger.debug("space_idx_list=%s", token_type_pos_list)

        stlen = len(st)   # don't count padded char
        st += EO_TERM
        start = 0
        final_list = []
        # num_tokens = len(token_type_pos_list)
        token_index = 0
        start = token_type_pos_list[token_index][0]  # must exist because st is not ""

        while start < stlen:
            # print "substr_search(" + st[start:] + "," + str(edit_dist) +")"
            # self.__substr_search(self.root, st, start, 0, idx_list, result_list, "fs")

            # see if to skip the word (a non-medication word)
            # first_word = st[start:util.next_space_index(start, space_idx_list)]
            (tok_start, tok_end, _tok_type) = token_type_pos_list[token_index]
            first_word = st[tok_start:tok_end]
            # print "first_word= '" + first_word + "'"
            if first_word in skip_word_dict:
                (token_index, start) = util.move_next_token(token_type_pos_list, token_index)
                continue
            # skip words with just 1 char, otherwise "5 with" will
            # be matched with 6 char with edit distance of 2
            # which is skipped.  So "with" is missing from annotation
            if len(first_word) == 1:
                (token_index, start) = util.move_next_token(token_type_pos_list, token_index)
                # print "skipped"
                continue

            # for edit_dist != 0
            edist_defn_list= []
            # 'ch' is not used in self.root_map
            for trie_root in self.root_map.values():
                self.__substr_search(node=trie_root,
                                     node_st_start=0,
                                     st=st,
                                     st_start=start,
                                     edist_left=edist_left,
                                     edist_cost=0,
                                     depth=0,
                                     token_type_indices=token_type_pos_list,
                                     token_index=token_index,
                                     result_list=edist_defn_list,
                                     op_st="",
                                     dict_st="",
                                     is_cache_mode=False,
                                     is_debug=False)

            # self.__substr_search(self.root, st, start, edit_dist, 0, idx_list, result_list, "fs")

            if is_debug:
                logger.debug("edist_defn_list=%s", edist_defn_list)
                # print("edist_defn_list= " + str(edist_defn_list))

            max_len = start
            # adjust the edit distance
            for (tmp_cost, tmp_end, tmp_edist_left, defn, operation_string,
                 dict_string) in edist_defn_list:
                if is_debug:
                    logger.debug("%s", (tmp_cost, start, tmp_end, tmp_edist_left, defn,
                                        operation_string, dict_string))
                # final_list.append((start, tmp_end, defn, (edit_dist-dist_left)))

                if tmp_end-start < 5:
                    if tmp_cost == 0:
                        if is_debug:
                            logger.debug("case 1")
                        final_list.append((tmp_cost, start, tmp_end, tmp_edist_left, defn,
                                           operation_string, dict_string))
                    else:  # edit distance is not 0
                        final_list.append((-1, start, tmp_end, -1,  0, "", ""))
                elif tmp_end-start <= 6 and tmp_cost <= 1:
                    if is_debug:
                        logger.debug("case 2")
                    final_list.append((tmp_cost, start, tmp_end, tmp_edist_left, defn,
                                       operation_string, dict_string))
                elif tmp_end-start > 6:
                    if is_debug:
                        logger.debug("case 3")
                    final_list.append((tmp_cost, start, tmp_end, tmp_edist_left, defn,
                                       operation_string, dict_string))
                else:
                    if is_debug:
                        logger.debug("case 4, pass")
                    # pass
                    final_list.append((-1, start, tmp_end, -1, 0, "", ""))

                max_len = max(max_len, tmp_end)
            # if is_debug:
            #    logger.debug("start= " + str(start) + ", maxLen= " + str(maxLen) +
            #                 ", length= " + str(spaceIdxList[-1]))

            if max_len == stlen:
                break
            if start == max_len:   # no match
                # this is somewhat inefficient, didn't remember from last
                # location
                # final_list.append((start, util.next_space_index(start, space_idx_list),
                #                    -1, 0, "", ""))
                final_list.append(
                    (-1, start, token_type_pos_list[token_index][1], -1, 0, "", "")
                )
                # start = util.next_space_index(start, space_idx_list) + 1
                (token_index, start) = util.move_next_token(token_type_pos_list, token_index)
            else:
                # token_index = util.next_token_type_index(token_type_pos_list, token_index, maxLen)
                (token_index, start) = util.move_next_token_with_start(token_type_pos_list,
                                                                       token_index, max_len)
        if is_debug:
            for (start, end, defn, dist, operation_string, dict_string) in final_list:
                logger.debug("candidate %s, st[]=%r => defn=%r", (start, end, defn, dist),
                             st[start:end], defn)
        unique_list = get_longest_st_min_cost(final_list)
        #for (defn, start, end, dist) in unique_list:
        # print str(defn) + " y(" + self.dict[defn] + ")"
        return unique_list

    def sort_children(self):
        for _ch, trie_root in sorted(self.root_map.items()):
            trie_root.sort_children()
        self.initialized = True

    def write(self, file_name):
        if not self.initialized:
            self.sort_children()

        with open(file_name, "w", encoding="utf-8") as outfile:
            for ch, trie_root in sorted(self.root_map.items()):
                trie_root.write(outfile, 0, ch, trie_root.dict_defn, depth=0)
        logger.info("wrote %s", file_name)

        defn_fname = file_name + ".dictdefn"
        with open(defn_fname, 'w', encoding="utf-8") as outfile:
            for dict_defn in self.defn_list:
                if dict_defn.id == 0:
                    continue
                outfile.write(str(dict_defn.id) + "\t" + dict_defn.term + "\t" + \
                              dict_defn.serialize_defn() + "\n")
        logger.info("wrote %s", defn_fname)

    def load(self, file_name, is_debug=False):
        t = time.time()
        num_entry= 0

        with open(file_name, 'rt', encoding="utf-8") as fd:
            for line in fd:
                num_entry += 1
                line = line.strip()
                # print "line num= " + str(size+1)
                if line.startswith("##") or line == "":
                    continue
                term, defn = line.split("\t")
                term = term.replace(EO_TERM, " ")
                self.add_definition(term, defn)
        if is_debug:
            logger.info("load(%r) took %.3f seconds, num_entry=%d", file_name,
                        time.time() - t, num_entry)

    def load_trie(self, file_name, is_debug=False):
        t = time.time()
        with open(file_name + ".dictdefn", 'rt', encoding="utf-8") as fd:
            for line in fd:
                line = line.rstrip("\r\n")
                idx, term, defn = line.split("\t")
                definition_id = int(idx)
                self.num_defn = max(self.num_defn, definition_id)
                self.defn_list.append(self.defn_class(definition_id,
                                                      term,
                                                      self.defn_class.deserialize_defn(defn)))

        num_entry= 0
        node_id_map = {}

        with open(file_name, 'rt', encoding="utf-8") as fd:
            for line in fd:
                num_entry += 1

                if line.startswith("##") or line == "":
                    continue
                # (self.id, pid, ch, self.st, defn_idx, self.defn)
                entry_id, parent_id, ch, st, defn_idx, _term = line.split("\t", 5)
                entry_id, parent_id, defn_idx = int(entry_id), int(parent_id), int(defn_idx)
                retrieved_defn = None
                if defn_idx != -1:
                    retrieved_defn = self.defn_list[defn_idx]
                xpatnode = ApxTrieNode(sys.intern(st), retrieved_defn, entry_id)
                node_id_map[entry_id] = xpatnode
                if parent_id == 0:
                    self.root_map[ch] = xpatnode
                else:
                    parent_node = node_id_map[parent_id]
                    parent_node.update_child(ch, xpatnode)

        if is_debug:
            logger.info("load(%r) took %.3f seconds, num_entry=%d", file_name,
                        time.time() - t, num_entry)

    def print_trie(self):
        if not self.initialized:
            self.sort_children()
        st_list = []
        for _ch, trie_root in sorted(self.root_map.items()):
            trie_root.str_aux(0, st_list)
        for st in st_list:
            print(st)


    def get_num_op(self):
        return ApproxRadixTrie.num_op

# this prefer longer one first, then cost
# ok, this is the right version.  You don't want the distance first
# "tylenol pim" should match "tylnol pm", not "tylenol"
def get_longest_st_min_cost(substr_found_list, is_debug=False):
    idx_end_map = {}
    idx_cost_map = {}
    idx_tuple_map = {}
    idx_dict_map = {}

    for substr_found_tuple in substr_found_list:
        (cost, start, end, _edist_left, defn, opr_st, dict_st) = substr_found_tuple

        if defn == 0:  # ignore entry
            continue

        # avoid the case of "xxx y" matching "xxx" instead of "xxx" itself
        if len(dict_st) > 1 and dict_st[-2] == " " and opr_st.endswith(
            ("ds", "sx", "s", "di", "ix")
        ):
            continue

        if end > idx_end_map.get(start, 0):
            idx_end_map[start] = end
            idx_cost_map[start] = cost
            idx_tuple_map[start] = substr_found_tuple
            idx_dict_map[start] = dict_st

        elif end == idx_end_map.get(start, 0):   # same st length, get min cost

            if cost < idx_cost_map.get(start, 1000):  # get min cost
                idx_cost_map[start] = cost
                idx_tuple_map[start] = substr_found_tuple
                idx_dict_map[start] = dict_st
            # if same cost, one with longer diction term wins.  Not sure why?
            # Probably can simply ignore this section
#            elif cost == idx_cost_map.get(start, 1000) and \
#                 len(idx_dict_map.get(start)) < len(dict_st):
#                idx_cost_map[start] = cost
#                idx_tuple_map[start] = substr_found_tuple
#                idx_dict_map[start] = dict_st
            else:
                pass

    result_list = []
    is_debug = False
    for idx in sorted(idx_tuple_map.keys()):
        if is_debug:
            logger.debug("my_tuple=%s", idx_tuple_map[idx])
        #(start,end,defn,dist,oprSt,dictSt)= idxTupleHash[idx]
        #if defn == "IGNORE":
        #    # resultList.append((start,end,-1,dist,dictSt))
        #    # pass
        #    resultList.append(idxTupleHash[idx])
        #else:
        #    resultList.append(idxTupleHash[idx])
        result_list.append(idx_tuple_map[idx])
    return result_list

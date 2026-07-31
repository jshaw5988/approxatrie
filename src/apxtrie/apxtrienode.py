
import copy
from abc import ABCMeta, abstractmethod


class BaseApxTrieNode:
    __metaclass__ = ABCMeta

    @abstractmethod
    def make_copy(self, st):
        pass

    @abstractmethod
    def reset_defn_child(self, st, ch, apatnode):
        pass

    @abstractmethod
    def update_child(self, ch, apatnode):
        pass

    @abstractmethod
    def get_children(self):
        pass

    @abstractmethod
    def find_child(self, ch):
        pass

    @abstractmethod
    def write(self, fd, pid, ch, dict_defn, depth):
        pass


class ApxTrieNode(BaseApxTrieNode):
    node_id = 0

    def __init__(self, st, dict_defn, aid=None):
        if aid is not None:
            self.id = aid
            ApxTrieNode.node_id = max(ApxTrieNode.node_id, aid)
        else:
            ApxTrieNode.node_id += 1
            self.id = ApxTrieNode.node_id
        self.st = st
        self.dict_defn = dict_defn
        self.child = []

    def __str__(self):
        st_list = []
        atuple = (self.id, self.st, self.dict_defn)
        st_list.append(str(atuple))
        for ch, child in self.child:
            st_list.append("  " + ch + "\t" + str((child.id, child.st, child.dict_defn)))
        return "\n".join(st_list)

    def make_copy(self, st):
        acopy = copy.copy(self)
        ApxTrieNode.node_id += 1
        acopy.id = ApxTrieNode.node_id
        acopy.st = st
        return acopy

    def reset_defn_child(self, st, ch, apatnode):
        self.st = st
        # set up the new children
        self.dict_defn= None
        self.child = []
        self.child.append((ch, apatnode))
        # # set up the new children
        # node.dict_defn= None
        # node.child_hash[st2[0]]= ApxTrieNode(st2,defn)

    def update_child(self, ch, apatnode):
        self.child.append((ch, apatnode))

    def get_children(self):
        return self.child

    def find_child(self, ch):
        for ach, achild in self.child:
            if ach == ch:
                return achild
        return None

    def binsearch_child(self, ch):
        lo = 0
        hi = len(self.child) - 1
        alist = self.child

        while lo <= hi:
            mid = lo + (hi - lo) // 2
            if alist[mid][0] == ch:
                return alist[mid][1]

            if ch < alist[mid][0]:
                hi = mid - 1
            else:
                lo = mid + 1
        return None

    def sort_children(self):
        self.child = sorted(self.child)
        for _ach, achild in self.child:
            achild.sort_children()

    def write(self, fd, pid, ch, dict_defn, depth=0):
        defn_idx = -1
        term = ""
        if dict_defn is not None:
            defn_idx = dict_defn.id
            term = dict_defn.term
        atuple = (self.id, pid, ch, self.st, defn_idx, term)
        # fd.write("  " * depth + str(atuple) + "\t" + str(len(self.child))+ "\n")
        fd.write("\t".join(map(str, atuple)) + "\n")
        for ach, achild in self.child:
            achild.write(fd, self.id, ach, achild.dict_defn, depth + 1)

    def get_decendent_defn(self):
        # print "getDecendentDefn(" + node.st + ")"
        result= []
        if self.dict_defn is not None:
            result.append(self.dict_defn)
        for _ch, child in self.get_children():
            result.extend(child.get_decendent_defn())
        return result

    def str_aux(self, depth, st_list):
        st_buffer = ""
        for _i in range(depth):
            st_buffer += "|--"
        st_buffer += f"{self.st}:nid:{self.id}:"
        if self.dict_defn is not None:
            st_buffer += "(" + str(self.dict_defn) + ")"
            st_list.append(st_buffer)
        else:
            st_list.append(st_buffer)
        for _ch, child in self.get_children():
            child.str_aux(depth+1, st_list)

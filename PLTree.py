# Single-threaded version of P-Lexi Trees.

# NOTE:
# - Many optimizations (both at the language and algorithm level) are possible,
#   but I decided to keep the code as simple and as readable as possible.
# - In practice, one would probably implement this in a fast language such as
#   C/C++/Rust and take into account cache misses, happy paths, etc...

from __future__ import annotations
from random import random
from typing import Final, Generic, Tuple
from misc import *
from misc import _Missing, _missing
from generic import K, V, T, Node, Tree

MaxLevel: Final[int] = 100

class _PNode(Node[K, V]):
    """Node for P-Lexi Trees"""
    level: int

    def __init__(self, key: K, val: V, level: int,
                 left: _PNode | None = None,
                 right: _PNode | None = None) -> None:
        self.key = key
        self.val = val
        self.level = level
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        # NOTE: no recursive repr to make the debugging faster!
        return f"Node({self.key} @ {self.level})"

    # generic interface
    def left_level(self, cur_level: int):
        assert isinstance(self.left, _PNode)
        return self.left.level

    # generic interface
    def right_level(self, cur_level: int):
        assert isinstance(self.right, _PNode)
        return self.right.level

class PLTree(Generic[K, V], Tree[K, V]):
    _p: float
    _root: Final[_PNode[K, V]]
    _maxLevel: int
    _len: int

    def __init__(self, any_key: K, any_val: V, *, p=0.5):
        """NOTE: `any_key` and `any_val` are needed for type stability, not
        that Python cares about it.
        """
        self._p = p
        self._root = _PNode[K, V](any_key, any_val, MaxLevel + 1)
        self._maxLevel = -1
        self._len = 0
        
    @property
    def first(self):
        return self._root.right
        
    @property
    def height(self):
        return self._maxLevel + 1
    
    # Needed for the generic interface.
    def get_height(self):
        assert (
            (self.first is None and self._maxLevel == -1) or
            (self.first is not None and self._maxLevel == self.first.level)
        )
        return self._maxLevel + 1

    def _rand_level(self):
        level = 0
        maxLevel = min(self._maxLevel + 1, MaxLevel)
        while level < maxLevel and random() < self._p:
            level += 1
        return level
    
    def __len__(self):
        return self._len

    # Returns (prev, cur, prev_cmp, cur_cmp). If there's already a node with
    # key `key`, then `cur` is that node, otherwise it's the next node of a
    # hypothetical Node(k, l):
    #     prev
    #        \
    #         \             Node(k, l)
    #          \
    #          cur
    def _find_insertion_pos(self, key: K, level: int) -> \
            Tuple[_PNode[K, V], _PNode[K, V] | None, int, int]:
        prev = self._root
        prev_cmp = -1               # root.key < anything
        cur = prev.right
        while cur is not None:
            if cur.key < key:
                if cur.level < level:
                    # cur is next(new) ==> prev is prev(new)
                    return prev, cur, prev_cmp, -1
                prev = cur
                prev_cmp = -1
                cur = cur.right
            elif key < cur.key:
                if cur.level <= level:
                    # cur is next(new) ==> prev is prev(new)
                    return prev, cur, prev_cmp, 1
                prev = cur
                prev_cmp = 1
                cur = cur.left
            else:       # cur.key = key
                return prev, cur, prev_cmp, 0
        return prev, cur, prev_cmp, 2           # 2 = invalid
    
    # NOTE: This is just _find_insertion_pos without the level tests.
    def _get_node_pos(self, key: K) -> \
            Tuple[_PNode[K, V], _PNode[K, V] | None, int]:
        return self._find_insertion_pos(key, -1)[:3]

    # Sets nodes = [first1, last1, ..., firstN, lastN, None, None, None].
    #                         (key)
    #        first1             |
    #              \            |
    #               last1 ------|---------> first2
    #                           |          /
    #                 ... <-----|---- last2
    #                           |
    #               firstN      |
    #                    \      |
    #                   lastN   |    None
    #                           |  
    #                           | None
    #                     None  |
    # If there's a node with key equal to `key`, stops immediately and returns
    # that node (nodes will be incomplete).
    # NOTE:
    # - One can have first_i = last_i.
    # - Required: len(nodes) >= 4*(first1.level+1) + 3.
    # - The 3 final `None`s are added for regularity (to help __setitem__).
    def _get_side_pairs(self, key: K, first1: _PNode[K, V] | None,
                        first1_cmp: int, nodes: list[_PNode[K, V] | None]) -> \
                            _PNode[K, V] | None:
        assert first1_cmp != 0
        if first1 is None:
            nodes[0] = nodes[1] = None
            return None
        nodes[0] = first1
        i = 1
        prev = first1
        prev_cmp = first1_cmp
        cur = first1.right if first1_cmp < 0 else first1.left
        while cur is not None:
            assert prev_cmp != 0
            if cur.key < key:
                if prev_cmp > 0:
                    nodes[i] = prev         # last_j
                    nodes[i+1] = cur        # first_{j+1}
                    i += 2
                prev = cur
                prev_cmp = -1
                cur = cur.right
            elif key < cur.key:
                if prev_cmp < 0:
                    nodes[i] = prev         # last_j
                    nodes[i+1] = cur        # first_{j+1}
                    i += 2
                prev = cur
                prev_cmp = 1
                cur = cur.left
            else:       # cur.key == key
                return cur
        nodes[i] = prev             # adds lastN
        nodes[i+1] = nodes[i+2] = nodes[i+3] = None
        return None
    
    def __contains__(self, key: K) -> bool:
        return self._find(key) is not notFound
    
    def __getitem__(self, key: K) -> V:
        val = self._find(key)
        if val is notFound:
            raise KeyError
        return val
    
    def _find(self, key: K) -> V | NotFound:
        cur = self._root.right
        while cur is not None:
            if cur.key < key:
                cur = cur.right
            elif key < cur.key:
                cur = cur.left
            else:
                return cur.val
        return notFound

    # Inserts with replacement.
    def __setitem__(self, key: K, val: V):
        self.insert(key, val)
        
    def insert(self, key: K, val: V, level: int | None = None):
        level = self._rand_level() if level is None else level

        prev, cur, prev_cmp, cur_cmp = self._find_insertion_pos(key, level)
        if cur is not None and cur_cmp == 0:        # cur.key = key
            # simple update
            cur.val = val
            return

        # NOTE: We use `nodes` only to avoid a double traversal. If key
        #   comparisons are fast, there's no need.
        nodes: list[_PNode[K, V] | None] = [None] * (4*(self._maxLevel+1) + 3)
        key_node = self._get_side_pairs(key, cur, cur_cmp, nodes)
        if key_node is not None:
            # simple update
            key_node.val = val
            return

        new = _PNode[K, V](key, val, level)
        
        # prev -> new
        if prev_cmp < 0:
            prev.right = new
        else:
            prev.left = new

        # new -> starts of left and right chains
        if cur_cmp < 0:
            new.left = cur
            new.right = nodes[2]        # first2
        else:
            new.right = cur
            new.left = nodes[2]         # first2

        # completes the left and right chains
        i = 1                       # starts from last1
        last_cmp = cur_cmp          # last1_cmp
        while True:
            last = nodes[i]         # (makes Pyright happy)
            if last is None:
                break
            # last_j -> first_{j+2}
            if last_cmp < 0:
                last.right = nodes[i+3]
            else:
                last.left = nodes[i+3]
            last_cmp = -last_cmp
            i += 2                  # moves to last_{j+1}

        self._len += 1
        if level > self._maxLevel: self._maxLevel = level

    def __delitem__(self, key: K):
        self.remove(key)
        
    #      prev----------------.
    #                           \                  
    #           .----------- Node(key)--------------.
    #          /                 |                    \   
    #         ()                 |                     \
    #           \                |                      \
    #            ()--()--()      |                       ()
    #                      \     |                      /
    #    left chain         \    |                    ()    right chain
    #                        \   |                   /       
    #                         () |       ()---------
    #                            |      /
    #                            |    ()
    #                            |   /
    #                            | ()
    def remove(self, key: K, default: T | _Missing = _missing) -> V | T:
        cur, key_node, cur_cmp = self._get_node_pos(key)
        if key_node is None:        # node not found
            if default is _missing:
                raise KeyError
            return default
        
        left_cur = key_node.left
        right_cur = key_node.right
        key_node.left = key_node.right = None

        # merges together the left and right chains
        done = False
        while not done and cur is not None:
            if right_cur is None or left_cur is None:
                next = left_cur if left_cur is not None else right_cur
                next_cmp = 2            # invalid, not used
                done = True
            elif left_cur.level >= right_cur.level:
                next = left_cur
                next_cmp = -1
                left_cur = left_cur.right
            else:
                next = right_cur
                next_cmp = 1
                right_cur = right_cur.left
                
            if cur_cmp < 0:
                if cur.right is not next: cur.right = next
            else:       # cur_cmp > 0
                if cur.left is not next: cur.left = next
            cur = next
            cur_cmp = next_cmp
        
        self._len -= 1
        max_lvl = self._root.right.level if self._root.right is not None \
                    else -1
        self._maxLevel = max_lvl
        return key_node.val
    
    @staticmethod
    def _check_sub(cur: _PNode[K, V], above_me: K | None = None,
                   below_me: K | None = None):
        """NOTE: cur.key must be in ]above_me, below_me[."""
        assert below_me is None or cur.key < below_me
        assert above_me is None or above_me < cur.key
        if cur.left is not None:
            assert cur.left.level < cur.level
            PLTree._check_sub(cur.left, above_me, cur.key)
        if cur.right is not None:
            assert cur.right.level <= cur.level
            PLTree._check_sub(cur.right, cur.key, below_me)

    # Checks whether the tree is valid.
    def _check(self):
        if self._root.right is None:
            assert self._maxLevel == -1
            return
        assert self._maxLevel == self._root.right.level
        self._check_sub(self._root.right)
    
    def _pretty_print_sub(self, cur: _PNode[K, V], elem_width):
        if cur.left is not None:
            self._pretty_print_sub(cur.left, elem_width)
        indent = ' ' * ((elem_width + 1) * cur.level)
        if type(cur.key) is float:
            print(f"{indent}{cur.key:>{elem_width}.2f}")
        else:
            print(f"{indent}{cur.key:>{elem_width}}")
        if cur.right is not None:
            self._pretty_print_sub(cur.right, elem_width)
        
    def pretty_print(self, elem_width = 7):
        if self._root.right is not None:
            self._pretty_print_sub(self._root.right, elem_width)

# Single-threaded version of 3-Lexi Trees.

# NOTE:
# - Many optimizations (both at the language and algorithm level) are possible,
#   but I decided to keep the code as simple and as readable as possible.
# - In practice, one would probably implement this in a fast language such as
#   C/C++/Rust and take into account cache misses, happy paths, etc...

from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Tuple
from misc import *
from misc import _Missing, _missing
from lift import lift
from lower3 import lower
from generic import K, V, T, Tree
from DLTree_misc import _DNode
from DLTree import DLTree

@dataclass
class PathData(Generic[K, V]):
    prev_leaf: _DNode[K, V]
    leaf: _DNode[K, V]
    prev_lower_me: _DNode[K, V]
    lower_me: _DNode[K, V]
    prev_key_node: _DNode[K, V] | None = None
    key_node: _DNode[K, V] | None = None

class D3LTree(DLTree[K, V], Tree[K, V]):
    def _lift_and_find(self, key: K) -> \
            Tuple[_DNode[K, V] | None, _DNode[K, V], _DNode[K, V] | None, int]:
        """Returns (prev2, prev, key_node, prev_cmp).
            If a node of key `key` was found in the tree, then
                prev -> key_node;   prev2 = None
            otherwise
                prev2 -> prev;   key_node = None
            and prev indicates the insertion position for a node of key `key`.
        """
        prev2 = None
        prev = self._root
        prev_cmp = -1
        cur = prev.right
        assert not prev.high_right          # root is above everything
        while cur is not None:
            if cur.high_right and cur.right is not None:
                right = cur.right
                if right.high_right and right.right is not None:
                    # lifts `right`
                    ret = lift(prev2, prev, cur, right, right.right,
                               prev_is_root=prev is self._root)
                    cur_prev, right_prev, right2_prev, _, _ = ret
                    # NOTE: This special handling avoids the possibility of
                    #   having to go through prev again (see Case II in _lift)
                    #   since we would restart from cur = right.
                    if key < right.key:
                        # stays with cur
                        prev = cur_prev
                    elif right.key < key:
                        # skips to cur = right.right
                        prev = right2_prev
                        cur = right.right
                    else:       # Node(key) found
                        # NOTE: We may not know right_prev2, so we return None
                        #  (again, see Case II in _lift).
                        return None, right_prev, right, -1
            prev2 = prev
            prev = cur
            if cur.key < key:
                prev_cmp = -1
                cur = cur.right
            elif key < cur.key:
                prev_cmp = 1
                cur = cur.left
            else:       # Node(key) found
                # NOTE: We return None instead of prev2 for uniformity.
                return None, prev, cur, prev_cmp
        return prev2, prev, cur, prev_cmp

    # Inserts with replacement.
    def __setitem__(self, key: K, val: V):
        prev2, prev, key_node, prev_cmp = self._lift_and_find(key)
        if key_node is not None:        # Node(key) already present
            # updates Node(key)
            key_node.val = val
            return
        key_node = _DNode[K, V](key, val, high_right=False)
        self._len += 1

        # prev -> key_node
        if prev2 is None:
            assert prev is self._root
            assert not prev.high_right
            prev.right = key_node
        elif prev_cmp > 0:
            #  P2 -------.   P2  ==>  P2 ----.        .--------- P2
            #             \ /    ==>          \      /
            #  P2 -------> P     ==>  P2 ---> key_node ------> P
            #             /      ==>                          /
            #       c=None       ==>                    c=None
            # NOTE:
            # - P is at level 0.
            # - `c` (i.e. `cur`) is None and just indicates that the search for
            #   `key` took Prev.left and thus prev_cmp > 0.
            if prev2.right is prev:
                prev2.right = key_node          # keeps high_right the same
            else:
                assert prev2.left is prev
                prev2.left = key_node
            key_node.right = prev
            key_node.high_right = True
        else:
            assert prev_cmp < 0
            # Prev (-----> other)  ==>  Prev ------> key_node (--> other)
            #     \                ==>      \    
            #      c=None          ==>       c=None
            # NOTE:
            # - P is at level 0.
            # - `c` (i.e. `cur`) is None and just indicates that the search for
            #   `key` took Prev.right and thus prev_cmp < 0.
            key_node.right = prev.right
            key_node.high_right = True      # ignored if right is None
            prev.right = key_node
            prev.high_right = True

    def __delitem__(self, key: K):
        self.remove(key)
        
    def _get_lowering_path(self, key: K) -> PathData[K, V] | None:
        prev = self._root
        cur = prev.right
        if cur is None:         # empty tree
            return None
        # lower_me = self._root.right (_root.right is always lowerable)
        prev_lower_me = prev
        lower_me = cur
        prev_leaf = leaf = None
        prev_key_node = key_node = None
        while True:
            if cur.key < key:
                c2 = cur.right
                o1 = cur.left
            else:       # key <= cur.key
                c2 = cur.left
                o1 = cur.right
                if not (key < cur.key):     # cur.key = key
                    # key-node found
                    prev_key_node = prev
                    key_node = cur
            # Lowerable cases:
            #   C1              C2            C3(R)              C3(L) 
            # P --> c        c --> ...             c            c
            #                               ______/ \          / \ 
            #                              /         \       c2   o1 o2 ... 
            #                            o1 o2 ...    c2    
            # NOTE: The extra lookup can be avoided by keeping the information
            #   in `c` as 1 or 2 bits (1 bit per side).
            lowerable = ((prev.right is cur and prev.high_right) or     # C1
                         (cur.right is not None and cur.high_right) or  # C2
                         (o1 is not None and o1.right is not None and
                          o1.high_right))                               # C3
            if lowerable:
                prev_lower_me = prev
                lower_me = cur
            if c2 is None:
                # leaf found
                prev_leaf = prev
                leaf = cur
                break
            prev = cur
            cur = c2
        assert (prev_leaf is not None and leaf is not None and
                prev_lower_me is not None and lower_me is not None)
        # NOTE: verbose but safer
        return PathData(prev_leaf=prev_leaf, leaf=leaf,
                        prev_lower_me=prev_lower_me, lower_me=lower_me,
                        prev_key_node=prev_key_node, key_node=key_node)

    def remove(self, key: K, default: T | _Missing = _missing) -> V | T:
        # NOTE: if key comparisons are slow, one can also save the path
        pd = self._get_lowering_path(key)
        if pd is None or pd.key_node is None:       # node not found
            if default is _missing:
                raise KeyError
            return default
        assert pd.prev_key_node is not None

        self._len -= 1

        # NOTE: (i) If there's no need to lower nodes, then lower_me = leaf and
        #   so we'll never enter the `while` loop below.
        #   (ii) In the loop below, c1.left and c1.right can't be None and c2
        #   must always be below c1.
        #
        #   PROOF. lower_me is defined as the last lowerable node in the
        #   root~>leaf path associated with key `key`.
        #   The `while` loop below loops through the path lower_me~>leaf, which
        #   is the final part of the root~>leaf path mentioned above.
        #   (i) If the leaf is lowerable, then the lower_me~>leaf path starts
        #   and ends with the leaf itself, so we must have lower_me = leaf.
        #   (ii) Since the tree is balanced, c1 lacks a pointer only if it's at
        #   level 0, so c2 must also be at level 0:
        #     c1 --> c2
        #   c2 is lowerable so c1 can't be in the lower_me~>leaf path. This
        #   shows that
        #       c1's ptr missing => level(c1) = level(c2) => c1 not in path
        #   which proves (ii).
        p = pd.prev_lower_me
        c1 = pd.lower_me
        while c1 is not pd.leaf:
            if c1 is pd.key_node or key < c1.key:
                #    c1
                #   /  \
                # c2    o1 (o2 o3)
                c2 = c1.left
                o1 = c1.right
                assert o1 is not None
                if c1.high_right:
                    o1 = o1.left
            elif c1.high_right:     # c1.key < key
                # c1 ---> c2 - - - - - -> r            p ---> c1 - - - - - -> r
                #        /  \   _ _ _ _ _/   ==FIX==>        /  \   _ _ _ _ _/
                #       /    \ /                            /    \ /
                #      x      o1 (o2 o3)                  c2      o1 (o2 o3)
                # (Note that the FIX operation is just a *relabeling*, so c1
                #  becomes p, c2 becomes c1, and x becomes c2.)
                # Since c2 is also lowerable, we must have lowered it just a
                # moment ago. Indeed, if c2 had been there before, the lowering
                # path would've never included c1.
                # This also means that we went from the then-higher c2 to c1 so
                # we must have `key < c2.key`.
                p = c1
                c1 = c1.right
                assert c1 is not None
                c2 = c1.left
                o1 = c1.right
                assert o1 is not None
                if c1.high_right:
                    o1 = o1.left
            else:                   # c1.key < key
                #            c1
                #   ________/  \
                #  /            \
                # o1 (o2 o3)     c2
                o1 = c1.left
                c2 = c1.right
                assert not c1.high_right        # c2 is always below c1
            assert o1 is not None and c2 is not None
            assert c2.right is None or not c2.high_right        # lonely node
            o2 = o3 = None
            if o1.high_right and o1.right is not None:
                o2 = o1.right
                if o2.high_right and o2.right is not None:
                    o3 = o2.right
            prev_c1, prev_c2 = lower(p, c1, c2, o1, o2, o3,
                                     prev_is_root=p is self._root)
            if c1 is pd.key_node: pd.prev_key_node = prev_c1
            if c2 is pd.key_node: pd.prev_key_node = prev_c2
            p = prev_c2
            c1 = c2
        # we may have changed the prev node of leaf
        pd.prev_leaf = p

        # If Node(key) has become a leaf, we remove it directly.
        # NOTE: We must have
        #   leaf --> key_node ...
        # because leaf must be right key-before key_node, by definition.
        if pd.leaf.right is pd.key_node:
            assert pd.prev_key_node is pd.leaf and pd.leaf.high_right
            pd.leaf.right = pd.key_node.right
            return pd.key_node.val

        self._replace_with_leaf(pd.prev_key_node, pd.key_node, pd.prev_leaf,
                                pd.leaf)

        return pd.key_node.val
        
    def _check(self):
        """Checks whether the tree is valid."""
        return super()._check(3)

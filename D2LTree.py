# Single-threaded version of 2-Lexi Trees.

# NOTE:
# - Many optimizations (both at the language and algorithm level) are possible,
#   but I decided to keep the code as simple and as readable as possible.
# - In practice, one would probably implement this in a fast language such as
#   C/C++/Rust and take into account cache misses, happy paths, etc...

from __future__ import annotations
from dataclasses import dataclass
from typing import Final, Generic, Tuple, cast
from generic import K, V, T, Tree
from DLTree_misc import _DNode
from DLTree import DLTree
from lift import lift
from lower2 import lower
from misc import _Missing, _missing

MAX_LEVEL: Final[int] = 40

@dataclass
class PathData(Generic[K, V]):
    """This is only used in `remove`"""
    prev_key_node: _DNode[K, V] | None
    key_node: _DNode[K, V] | None
    key_node_idx: int = 0           # idx of key_node in list of nodes
    last_idx: int = 0               # last valid idx in list of nodes

class D2LTree(DLTree[K, V], Tree[K, V]):
    def _insert_keynode(
        self, prev2: _DNode[K, V], prev: _DNode[K, V], prev_cmp: int,
        key_node: _DNode[K, V]
    ) -> Tuple[_DNode[K, V], _DNode[K, V]]:
        """Inserts keynode after prev and returns the new prev and cur"""
        if prev_cmp > 0:
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
            cur = prev
            prev = key_node
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
            cur = key_node
        return prev, cur

    def __setitem__(self, key: K, val: V):
        """Inserts with replacement."""
        # NOTE: additional +1 for the root.
        nodes: list[_DNode[K, V] | None] = [None] * (2*(MAX_LEVEL+1) + 1)
        nodes[0] = self._root
        last_idx = 0            # last idx in `nodes`
        # NOTE: prev_cmp is useful when key comparisons are expensive
        prev_cmp = -1

        # Finds the insertion point and collects the nodes along the path.
        cur = self._root.right
        while cur is not None:
            last_idx += 1
            nodes[last_idx] = cur
            if cur.key < key:
                prev_cmp = -1
                cur = cur.right
            elif key < cur.key:
                prev_cmp = 1
                cur = cur.left
            else:       # key already present
                cur.val = val
                return
        
        key_node = _DNode[K, V](key, val, high_right=False)
        self._len += 1
        
        # prev -> key_node
        prev = nodes[last_idx]
        assert prev is not None
        if last_idx == 0:              # empty tree
            prev.right = key_node
            return
        last_idx -= 1
        prev2 = nodes[last_idx]
        assert prev2 is not None
        prev, cur = self._insert_keynode(prev2, prev, prev_cmp, key_node)

        # rebalances the tree
        done = False
        while not done:
            done = True
            # makes sure prev is always above cur
            assert cur is not None and prev is not None
            if prev.high_right and prev.right is cur:
                last_idx -= 1
                cur = prev
                prev = prev2
                prev2 = nodes[last_idx] if last_idx >= 0 else None
                # NOTE: if prev2 is None, then prev is root and we are in lift
                #   Case I, so prev2 is not needed.
                done = False
            elif cur.high_right and cur.right is not None:
                right = cur.right
                if right.high_right and right.right is not None:
                    # lifts `right`
                    ret = lift(prev2, prev, cur, right, right.right,
                               prev_is_root=prev is self._root)
                    prev, cur = ret[3:]
                    done = False

    def __delitem__(self, key: K):
        self.remove(key)
        
    def _find_and_collect(self, key: K, nodes: list[_DNode[K, V] | None]) -> \
            PathData[K, V] | None:
        # Finds the insertion point and collects the nodes along the path.
        nodes[0] = self._root
        last_idx = 0                # last idx in nodes
        key_node = None
        prev_key_node = None        # makes the static checker happy
        cur = self._root.right
        if cur is None:             # empty tree
            return None
        key_node_idx = 0
        while cur is not None:
            last_idx += 1
            nodes[last_idx] = cur
            if cur.key < key:
                cur = cur.right
            elif key < cur.key:
                cur = cur.left
            else:       # cur.key = key
                key_node_idx = last_idx
                key_node = cur
                prev_key_node = nodes[last_idx-1]
                # Finds the leaf that's right key-before the key node (no
                # further key comparisons are needed).
                cur = cur.left
                while cur is not None:
                    last_idx += 1
                    nodes[last_idx] = cur
                    cur = cur.right
                break
        return PathData(prev_key_node=prev_key_node, key_node=key_node,
                        key_node_idx=key_node_idx, last_idx=last_idx)
        
    def remove(self, key: K, default: T | _Missing = _missing) -> V | T:
        # NOTE: additional +1 for the root.
        _nodes: list[_DNode[K, V] | None] = [None] * (2*(MAX_LEVEL+1) + 1)
        pd = self._find_and_collect(key, _nodes)
        if pd is None or pd.key_node is None:       # node not found
            if default is _missing:
                raise KeyError
            return default
        self._len -= 1

        # NOTE: nodes[i] is not None for i in {0, ..., pd.last_idx}.
        nodes: list[_DNode[K, V]] = cast(list, _nodes)
        assert pd.prev_key_node is not None
        last_idx = pd.last_idx
        prev_leaf = nodes[last_idx-1]
        leaf = nodes[last_idx]
        last_idx -= 1
        hole = self._replace_with_leaf(pd.prev_key_node, pd.key_node,
                                       prev_leaf, leaf)
        if not hole:
            return pd.key_node.val

        # updates `nodes` as well
        nodes[pd.key_node_idx] = leaf
        
        # Rebalances the tree.
        # NOTE: rereads nodes[last_idx] because it may have changed.
        cur = nodes[last_idx]       # first node to lower, if hole is True
        last_idx -= 1
        prev = nodes[last_idx]
        hole_side = -1 if cur.left is None else 1
        while hole:
            if hole_side == -1:
                other1 = cur.right
                assert other1 is not None
                if cur.high_right:
                    other1 = other1.left
                    assert other1 is not None
            else:
                other1 = cur.left
                assert other1 is not None
            other2 = other1.right
            if not other1.high_right:
                other2 = None

            hole_side = -1 if prev.left is cur else 1       # for next time
            hole = lower(prev, cur, other1, other2)

            # goes up
            if last_idx == 0:
                # cur would be the root so we're done
                break
            last_idx -= 1
            cur = prev
            prev = nodes[last_idx]
        
        return pd.key_node.val

    def _check(self):
        """Checks whether the tree is valid."""
        return super()._check(2)

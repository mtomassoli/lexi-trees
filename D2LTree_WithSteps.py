# NOTE: This code is just for making animations of D2LTree operations.

from __future__ import annotations
from typing import Final, cast
from generic import K, V
from lift import lift
from D2LTree import D2LTree
from DLTree_misc import _DNode
from lower2 import lower

MAX_LEVEL: Final[int] = 40

class D2LTree_WithSteps(D2LTree[K, V]):
    def _insert_steps(self, key: K, val: V):
        op_label = '[D2LTree Insertion]'
        frame = 0
        yield f"{op_label} Frame {frame}: Before"

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
        
        frame += 1
        yield f"{op_label} Frame {frame}: Keynode inserted"

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

                    frame += 1
                    yield f"{op_label} Frame {frame}: Node lifted"

    def _remove_steps(self, key: K):
        op_label = '[D2LTree Deletion]'
        frame = 0
        yield f"{op_label} Frame {frame}: Before"

        # NOTE: additional +1 for the root.
        _nodes: list[_DNode[K, V] | None] = [None] * (2*(MAX_LEVEL+1) + 1)
        pd = self._find_and_collect(key, _nodes)
        if pd is None or pd.key_node is None:       # node not found
            return
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

        frame += 1
        yield f"{op_label} Frame {frame}: Keynode replaced with leaf"

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

            frame += 1
            yield f"{op_label} Frame {frame}: Node lowered"

            # goes up
            if last_idx == 0:
                # cur would be the root so we're done
                break
            last_idx -= 1
            cur = prev
            prev = nodes[last_idx]

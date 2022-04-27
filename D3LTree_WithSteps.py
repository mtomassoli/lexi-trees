# NOTE: This code is just for making animations of D3LTree operations.

from __future__ import annotations
from lift import lift
from lower3 import lower
from generic import K, V
from DLTree_misc import _DNode
from D3LTree import D3LTree

class D3LTree_WithSteps(D3LTree[K, V]):
    def _lift_and_find_steps(self, key: K):
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
        
                    yield 'Node lifted'
                    
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
                        yield None, right_prev, right, -1
                        return
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
                yield None, prev, cur, prev_cmp
                return
        yield prev2, prev, cur, prev_cmp

    # Inserts with replacement.
    def _insert_steps(self, key: K, val: V):
        op_label = '[D3LTree Insertion]'
        frame = 0
        yield f"{op_label} Frame {frame}: Before"

        ret = ''
        for ret in self._lift_and_find_steps(key):
            if isinstance(ret, str):
                frame += 1
                yield f"{op_label} Frame {frame}: {ret}"
            else:
                break
        assert not isinstance(ret, str)
        prev2, prev, key_node, prev_cmp = ret
        
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

        frame += 1
        yield f"{op_label} Frame {frame}: Keynode inserted"

    def _remove_steps(self, key: K):
        op_label = '[D3LTree Deletion]'
        frame = 0
        yield f"{op_label} Frame {frame}: Before"

        # NOTE: if key comparisons are slow, one can also save the path
        pd = self._get_lowering_path(key)
        if pd is None or pd.key_node is None:       # node not found
            return
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

            frame += 1
            yield f"{op_label} Frame {frame}: Node lowered"

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

            frame += 1
            yield f"{op_label} Frame {frame}: Keynode removed"
            
            return

        self._replace_with_leaf(pd.prev_key_node, pd.key_node, pd.prev_leaf,
                                pd.leaf)

        frame += 1
        yield f"{op_label} Frame {frame}: Keynode replaced with leaf"

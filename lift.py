from __future__ import annotations
from typing import Tuple
from generic import K, V
from DLTree_misc import _DNode

def lift(prev2: _DNode[K, V] | None, prev: _DNode[K, V], cur: _DNode[K, V],
         right: _DNode[K, V], right2: _DNode[K, V], *, prev_is_root: bool) -> \
             Tuple[_DNode[K, V], _DNode[K, V], _DNode[K, V], _DNode[K, V],
                   _DNode[K, V]]:
    """Lifts `right` and returns the final
        cur_prev, right_prev, right2_prev, prev, cur.
    """
    if prev.right is cur:
        # Case I: prev.right = cur
        # P            ==>  P --> r
        #  \           ==>       / \
        #   c  r  r2   ==>      c   r2
        #     /        ==>       \ 
        prev.right = right
        prev.high_right = not prev_is_root
        cur.right = right.left
        cur.high_right = False
        right.left = cur
        right.high_right = False
        cur = right
        return right, prev, right, prev, right
    else:
        # Case II: prev.left = cur
        # P2 ------------.   P2  ==>  P2 ---.   .-------- P2
        #                 \ /    ==>         \ /
        # P2 ------------> P     ==>  P2 ---> r ---> P
        #        _________/      ==>         /      / 
        #       /                ==>        /      /
        #      c   r   r2        ==>       c     r2
        #     /   /              ==>      / \
        # NOTE: Prev2 can be in any of the 3 positions shown above.
        assert prev2 is not None
        if prev2.right is prev:
            prev2.right = right         # keeps same high_right
        else:
            prev2.left = right
        prev.left = right2
        cur.right = right.left
        cur.high_right = False
        right.left = cur
        right.right = prev
        return right, prev2, prev, right, prev

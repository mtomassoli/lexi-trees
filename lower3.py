from __future__ import annotations
from typing import Tuple
from generic import K, V
from DLTree_misc import _DNode

def lower(prev: _DNode[K, V], cur1: _DNode[K, V], cur2: _DNode[K, V],
          other1: _DNode[K, V], other2: _DNode[K, V] | None,
          other3: _DNode[K, V] | None, *, prev_is_root: bool) -> \
              Tuple[_DNode[K, V], _DNode[K, V]]:
    """Lowers `cur1`"""
    # RULE: cur1 always points to cur2 and cur2 is always below cur1 or we
    #   could lower cur2 without lowering cur1 first.
    assert cur1.left is cur2 or (cur1.right is cur2 and not cur1.high_right)
    
    if other2 is None:
        assert other3 is None
        # Case Left1
        # P=Root - -.        ==>  P=Root.
        #            \       ==>         \
        #     P ----> c1     ==>       P
        #            /  \    ==>        \ |
        #          o1    c2  ==>         o1   c1   c2
        #            \       ==>             /
        #
        # Case Right1
        # P=Root - -.        ==>  P=Root.
        #            \       ==>         \
        #     P ----> c1     ==>       P
        #            /  \    ==>        \ |
        #          c2    o1  ==>         c2   c1   o1
        #            \       ==>             /
        #
        # Case RightHi1
        # P ----.    .----- P  ==>  P ------------.   P
        #        \  /          ==>                 \ /
        # P ----> c1 ---> r    ==>  P ------------> r
        #        /       /     ==>       __________/
        #       /       /      ==>      / 
        #     c2      o1       ==>     c2   c1   o1
        #       \              ==>         /
        #
        # NOTE:
        # - Case Right1 is case Left1 with cur2 and other1 switched.
        # - There's no LeftHi1 case because c1 and c2 must be linked directly,
        #   so no `r` can separate them.
        # - Prev can be in any of the positions shown above.
        # - In Left1 and Right1, P can't be higher than c1 or lowering c1 would
        #   leave a hole. This isn't true for Right1 when r is present.
        # - If P is Root, then P.high_right can be False and this doesn't leave
        #   a hole because Root is a very special node.
        # - The flag prev_is_root is only used in an assert.
        c1_left = cur1.left
        assert c1_left is not None
        if cur1.high_right:         # RightHi1
            r = cur1.right
            assert r is not None
            assert c1_left is cur2
            r.left = cur2
            if prev.right is cur1:
                prev.right = r          # keeps same high_right
            else:
                prev.left = r
            cur1.right = other1
            prev_c2 = r
        else:                       # Left1 or Right1
            assert prev.right is cur1 and (prev.high_right or prev_is_root)
            prev.right = c1_left
            prev.high_right = False
            prev_c2 = cur1 if cur1.right is cur2 else prev
        cur1.left = c1_left.right
        cur1.high_right = True
        c1_left.right = cur1
        c1_left.high_right = True
        prev_c1 = c1_left
    else:
        if cur1.left is other1:
            # Case Left3
            # P ------------.    .-- P  ==>  P ----.    .----------- P
            #                \  /       ==>         \  /
            # P ------------> c1        ==>  P ----> o2
            #        ________/  \       ==>         /  \
            #       /            \      ==>        /    \   
            #     o1  o2  o3(LO)  c2    ==>      o1      o3(LO) c1  c2     
            #        /      \           ==>        \           / 
            #
            # Case Left2
            # P --------.    .-- P  ==>  P ----.    .------- P
            #            \  /       ==>         \  /
            # P --------> c1        ==>  P ----> o2(LO)
            #        ____/  \       ==>         /  \      
            #       /        \      ==>        /    \   
            #     o1  o2(LO)  c2    ==>      o1      c1  c2     
            #        /  \           ==>        \    /
            #
            # NOTE:
            # - There are no "Hi cases" because c1 and c2 must be linked
            #   directly, so no `r` can separate them.
            # - LO = last_other.
            # - Prev can be in any of the 3 positions shown above.
            last_other = other2 if other3 is None else other3
            if prev.right is cur1:
                prev.right = other2         # keeps same high_right
            else:
                prev.left = other2
            other1.right = other2.left
            other1.high_right = False
            other2.left = other1
            other2.high_right = False
            cur1.left = last_other.right
            cur1.high_right = True
            last_other.right = cur1
            last_other.high_right = last_other is other3
            prev_c1 = last_other
            prev_c2 = cur1
        else:
            assert cur1.left is cur2
            # Case Right3
            # P --.    .------------ P  ==>  P ----------.    .----- P
            #      \  /                 ==>               \  /
            # P --> c1 - - - - - > r    ==>  P ----------> o2 - -> r
            #      /  \    _ _ _ _/     ==>       ________/  \    /
            #     /    \  /             ==>      /            \  /
            #   c2      o1  o2  o3      ==>     c2  c1  o1     o3
            #     \    /   /            ==>        /   /  \
            #
            # Case Right2
            # P ---.    .--------- P  ==>  P -------.    .----- P
            #       \  /              ==>            \  /
            # P ---> c1 - - - -> r    ==>  P -------> o1 - -> r
            #       /  \    _ _ /     ==>        ____/  \    /
            #      /    \  /          ==>       /        \  /
            #    c2      o1  o2       ==>      c2  c1     o2
            #      \    /             ==>         /  \  
            #
            # NOTE:
            # - Prev can be in any of the 3 positions shown above.
            # - c1 and o1 are connected either directly or through r. The
            #   same goes for lifted and lifted.right.
            # - These are almost the inverse of case Left2 and Left3.
            if other3 is not None:
                before_lifted = other1
                lifted = other2
            else:
                before_lifted = cur1
                lifted = other1
            if cur1.high_right:
                r = cur1.right
                assert r is not None
                r.left = lifted.right
                lifted.right = r
                cur1.right = before_lifted      # needed if other3 != None
            before_lifted.right = lifted.left
            lifted.left = cur2
            lifted.high_right = cur1.high_right
            before_lifted.high_right = False
            if prev.right is cur1:
                prev.right = lifted         # keeps same high_right
            else:
                prev.left = lifted
            cur1.left = cur2.right
            cur1.high_right = before_lifted is not cur1
            cur2.right = cur1
            cur2.high_right = True
            prev_c1 = cur2
            prev_c2 = lifted
    return prev_c1, prev_c2

from __future__ import annotations
from generic import K, V
from DLTree_misc import _DNode

def lower(prev: _DNode[K, V], cur1: _DNode[K, V], other1: _DNode[K, V],
          other2: _DNode[K, V] | None) -> bool:
    """Lowers `cur1` and returns `hole`, which tells whether a hole was created
    by the lowering."""
    if other2 is None:
        # Case Left1
        # P! ---.    .----- P!  ==>  P! ---.      .------ P!
        #        \  /           ==>         \    /
        # P ----> c1            ==>  P ----. |  /
        #        /  \           ==>         \| /
        #      o1    \          ==>          o1   c1
        #        \    \         ==>              /  \
        #              (c2)     ==>                  (c2)
        #
        # Case Right1
        # P! ----.    .---- P!  ==>  P! ---.      .---- P!
        #         \  /          ==>         \    /
        # P -----> c1           ==>  P ----. |  /
        #         /  \          ==>         \| /
        #        /    o1        ==>          c1   o1
        #       /               ==>         /
        #   (c2)                ==>     (c2)
        #
        # Case RightHi1
        # P -------.    .----- P  ==>  P ------------.   .--- P
        #           \  /          ==>                 \ /
        # P -------> c1 --- r     ==>  P ------------> r
        #           /      /      ==>            _____/
        #          /      /       ==>           /
        #         /     o1        ==>         c1   o1
        #        /                ==>        /
        #    (c2)                 ==>    (c2)
        # NOTE:
        # - There is no LeftHi1 case because c1 and c2 must be linked directly,
        #   so no `r` can separate them.
        # - The exclamation mark after the P means that, when P is in that
        #   position, the operation will leave a hole.
        # - `c2` is between parentheses because it's not really needed. Whether
        #   it's None or one level lower than it should (thus leaving a hole),
        #   the algorithm doesn't change.
        if cur1.left is other1:
            # Left1
            high_case = False
            first = other1
            cur1.left = other1.right
            other1.right = cur1
            other1.high_right = True
        elif cur1.high_right:
            # RightHi1
            assert cur1.right is not None and cur1.right.left is other1
            high_case = True
            first = cur1.right          # first = r
            first.left = cur1
            cur1.right = other1
        else:
            # Right1
            high_case = False
            first = cur1
            cur1.high_right = True

        # sets prev
        if prev.left is cur1:
            hole = not high_case
            prev.left = first
        else:
            hole = not high_case and not prev.high_right
            prev.right = first
            prev.high_right = prev.high_right and high_case
        return hole
    else:
        # Case Left2
        # P ---------.    .------- P  ==>  P ----.    .------- P
        #             \  /            ==>         \  /
        # P ---------> c1             ==>  P ----> o2
        #        _____/  \            ==>         /  \      
        #       /         \           ==>        /    \   
        #     o1   o2      \          ==>      o1      c1
        #         /  \      \         ==>        \    /  \
        #                    (c2)     ==>                 (c2)
        #
        # Case Right2
        # P ------.    .----------- P  ==>  P -------.    .------ P
        #          \  /                ==>            \  /
        # P ------> c1 - - - - > r     ==>  P -------> o1 - -> r
        #          /  \    _ _ _/      ==>            /  \    /
        #         /    \  /            ==>           /    \  /
        #        /      o1   o2        ==>         c1      o2
        #       /      /               ==>        /  \  
        #   (c2)                       ==>    (c2)
        #
        # NOTE:
        # - There is no LeftHi2 case because c1 and c2 must be linked directly,
        #   so no `r` can separate them.
        if cur1.left is other1:
            # Left2
            first = other2
            other1.right = other2.left
            other1.high_right = False
            cur1.left = other2.right
            other2.left = other1
            other2.right = cur1
            other2.high_right = False
        else:
            # Right2
            first = other1
            r = cur1.right
            cur1.right = other1.left
            cur1.high_right = False
            other1.left = cur1
            if r is not other1:
                # `r` is present
                assert r is not None
                other1.right = r
                r.left = other2
            else:
                other1.high_right = False
        
        # sets prev
        if prev.left is cur1:
            prev.left = first
        else:
            prev.right = first          # keeps same high_right
        return False            # No Hole

from __future__ import annotations
from typing import Final, Generic
from generic import K, V
from DLTree_misc import _DNode
from misc import NotFound, notFound, _Missing, _missing

class DLTree(Generic[K, V]):
    _root: Final[_DNode[K, V]]
    _len: int

    def __init__(self, any_key: K, any_val: V):
        """NOTE: `any_key` and `any_val` are needed for type stability, not
        that Python cares about it.
        """
        self._root = _DNode[K, V](any_key, any_val, high_right=False)
        self._len = 0
        
    @property
    def first(self):
        return self._root.right

    def __len__(self):
        return self._len

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

    def _iter_sub(self, cur: _DNode[K, V]):
        if cur.left is not None:
            yield from self._iter_sub(cur.left)
        yield (cur.key, cur.val)
        if cur.right is not None:
            yield from self._iter_sub(cur.right)
    
    def __iter__(self):
        cur = self._root.right
        if cur is not None:
            yield from self._iter_sub(cur)

    def _key_val_levels_sub(self, cur: _DNode[K, V], cur_level: int,
                            levels: slice):
        if cur_level < levels.start:
            return              # stop!
        if cur.left is not None:
            yield from self._key_val_levels_sub(cur.left, cur_level-1, levels)
        if cur_level < levels.stop:
            yield cur.key, cur.val, cur_level
        if cur.right is not None:
            right_level = cur_level if cur.high_right else cur_level - 1
            yield from self._key_val_levels_sub(cur.right, right_level, levels)

    def key_vals_levels(self, levels: slice):
        if levels.step is not None:
            raise ValueError("level.step is not supported")
        levels = slice(levels.start or 0,
                       self.__len__() if levels.stop is None else levels.stop,
                       None)
        cur = self._root.right
        if cur is not None:
            yield from self._key_val_levels_sub(cur, self.get_height() - 1,
                                                levels)

    @staticmethod
    def _safely_get_height_sub(cur: _DNode[K, V]) -> int:
        height = 0
        if cur.left is not None:
            height = DLTree._safely_get_height_sub(cur.left)
        if cur.right is not None:
            inc = 0 if cur.high_right else 1
            height = max(
                height, inc + DLTree._safely_get_height_sub(cur.right))
        return height

    # NOTE: It works even when the tree is not valid, but it's slow (O(N)).
    def _safely_get_height(self) -> int:
        if self._root.right is None: return 0
        return DLTree._safely_get_height_sub(self._root.right) + 1

    def get_height(self) -> int:
        height = 0
        cur = self._root.right
        while cur is not None:
            height += 1
            cur = cur.left
        return height
    
    @staticmethod
    def _check_sub(cur: _DNode[K, V], above_me: K | None = None,
                   below_me: K | None = None, num_high_rights: int = 0, *,
                   max_list_len: int, cur_height: int, tree_height: int):
        """NOTE: cur.key must be in ]above_me, below_me[."""
        assert below_me is None or cur.key < below_me
        assert above_me is None or above_me < cur.key
        if cur.left is not None:
            DLTree._check_sub(cur.left, above_me, cur.key,
                              max_list_len=max_list_len,
                              cur_height=cur_height+1,
                              tree_height=tree_height)
        else:
            assert cur_height == tree_height
        if cur.right is not None:
            num_high_rights = num_high_rights + 1 if cur.high_right else 0
            assert num_high_rights < max_list_len
            new_cur_height = cur_height if cur.high_right else cur_height+1
            DLTree._check_sub(cur.right, cur.key, below_me, num_high_rights,
                              max_list_len=max_list_len,
                              cur_height=new_cur_height,
                              tree_height=tree_height)
        else:
            assert cur_height == tree_height

    def _check(self, max_list_len: int):
        """Checks whether the tree is valid."""
        tree_height = self.get_height()
        if self._root.right is not None:
            self._check_sub(self._root.right, max_list_len=max_list_len,
                            cur_height=1, tree_height=tree_height)

    def _pretty_print_sub(
        self, cur: _DNode[K, V], level: int, elem_width: int, *,
        from_level: int | None=None, to_level: int | None=None,
        from_key: K | _Missing=_missing, to_key: K | _Missing=_missing
    ):
        opts = dict(from_level=from_level, to_level=to_level,
                    from_key=from_key, to_key=to_key)
        if cur.left is not None:
            cond = ((from_level is None or from_level <= level - 1) and
                    (from_key is _missing or from_key < cur.key))
            if cond:
                self._pretty_print_sub(cur.left, level - 1, elem_width, **opts)
        cond = ((to_level is None or level <= to_level) and 
                (from_key is _missing or not (cur.key < from_key)) and
                (to_key is _missing or not (to_key < cur.key)))
        if cond:
            indent = ' ' * ((elem_width + 1) * level)
            if type(cur.key) is float:
                print(f"{indent}{cur.key:>{elem_width}.2f}")
            else:
                print(f"{indent}{cur.key:>{elem_width}}")
        if cur.right is not None:
            right_level = level if cur.high_right else level - 1
            cond = ((from_level is None or from_level <= right_level) and
                    (to_key is _missing or cur.key < to_key))
            if cond:
                self._pretty_print_sub(cur.right, right_level, elem_width,
                                       **opts)

    def pretty_print(self, elem_width = 7, *, safe_height=True,
                     from_level: int | None=None, to_level: int | None=None,
                     from_key: K | _Missing=_missing,
                     to_key: K | _Missing=_missing):
        height = self._safely_get_height() if safe_height \
                 else self.get_height()
        if self._root.right is not None:
            self._pretty_print_sub(self._root.right, height - 1, elem_width,
                                   from_level=from_level, to_level=to_level,
                                   from_key=from_key, to_key=to_key)
            
    def _replace_with_leaf(self, prev_node: _DNode[K, V], node: _DNode[K, V],
                           prev_leaf: _DNode[K, V], leaf: _DNode[K, V]):
        # removes the leaf
        if prev_leaf.right is leaf:
            # prev_leaf --.             ==> prev_leaf --.
            #              \            ==>              \
            # prev_leaf --> leaf --> r  ==> prev_leaf --> r
            # NOTE: `r` may be None
            hole = (not prev_leaf.high_right and leaf.right is None and
                    prev_leaf is not self._root)
            prev_leaf.right = leaf.right
        else:
            #               prev_leaf  ==>     prev_leaf
            #      ________/           ==>    /
            #     /                    ==>   /
            # leaf --> r               ==>  r
            # NOTE: `r` may be None
            hole = leaf.right is None
            prev_leaf.left = leaf.right

        # replaces key_node with the leaf unless they're the same node
        if node is not leaf:
            # NOTE: Another option, less general, is to just overwrite the
            #   `key` and `val` fields of key_node.
            leaf.right = node.right
            leaf.high_right = node.high_right
            leaf.left = node.left
            if prev_node.right is node:
                prev_node.right = leaf
            else:
                prev_node.left = leaf

        return hole

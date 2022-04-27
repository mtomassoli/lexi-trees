from __future__ import annotations
from generic import K, V, Node

class _DNode(Node[K, V]):
    high_right: bool            # True <=> right.level = self.level

    def __init__(self, key: K, val: V, high_right: bool = False,
                 left: _DNode | None = None,
                 right: _DNode | None = None) -> None:
        self.key = key
        self.val = val
        self.high_right = high_right
        self.left = left
        self.right = right
    
    # generic interface
    def left_level(self, cur_level: int):
        return cur_level - 1
    
    # generic interface
    def right_level(self, cur_level: int):
        return cur_level if self.high_right else cur_level - 1

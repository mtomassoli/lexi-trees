from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from math import sqrt
from random import random
from typing import Any, Generic, Protocol, Sized, TypeVar
from typing_extensions import Self
from misc import _Missing, _missing
import numpy as np

K = TypeVar('K', bound='WithLessThan')
V = TypeVar('V')
T = TypeVar('T')

K_Cov = TypeVar('K_Cov', bound='WithLessThan', covariant=True)

class WithLessThan(Protocol):
    @abstractmethod
    def __lt__(self: K, other: K, /) -> bool: pass

class Node(Generic[K, V], Protocol[K, V]):
    key: K
    val: V
    left: Self | None
    right: Self | None

    def __hash__(self):
        return hash(self.key)

    def __repr__(self) -> str:
        # NOTE: no recursive repr to make the debugging faster!
        return f"Node({self.key})"
    
    def left_level(self, cur_level: int) -> int: ...
    def right_level(self, cur_level: int) -> int: ...
    
class Tree(Sized, Protocol[K, V]):
    @property
    def first(self) -> Node[K, V] | None: ...

    # NOTE: As a general rule, I don't use properties for things that can be
    #   expensive to compute.
    @abstractmethod
    def get_height(self) -> int: ...
    
    @abstractmethod
    def __contains__(self, key: K) -> bool: ...

    @abstractmethod
    def __getitem__(self, key: K) -> V: ...

    @abstractmethod
    def __setitem__(self, key: K, val: V): ...

    @abstractmethod
    def __delitem__(self, key: K): ...

    @abstractmethod
    def remove(self, key: K, default: T | _Missing = _missing) -> V | T: ...

    @abstractmethod
    def _check(self): ...
    
    @abstractmethod
    def pretty_print(self, elem_width = 7): ...

    def get_graph(self, *, from_level: int | None=None,
                to_level: int | None=None, from_key: K | _Missing=_missing,
                to_key: K | _Missing=_missing):
        """Returns:
            nodes: all the nodes sorted by key
            edges: all the parent->child edges as pairs of indices
        """
        nodes: list[tuple[K, int]] = []         # (key, level) pairs
        edges: list[tuple[int, int]] = []       # (from_idx, to_idx) pairs
        
        def sub(cur: Node[K, V], level: int) -> int | None:
            """Returns the index of `cur` in `nodes`."""
            left_cond = right_cond = None
            left_idx = cur_idx = right_idx = None
            
            # adds the nodes
            if cur.left is not None:
                left_cond = (
                    (from_level is None or from_level <= level - 1) and
                    (from_key is _missing or from_key < cur.key))
                if left_cond:
                    left_idx = sub(cur.left, cur.left_level(level))
            cond = ((to_level is None or level <= to_level) and 
                    (from_key is _missing or not (cur.key < from_key)) and
                    (to_key is _missing or not (to_key < cur.key)))
            if cond:
                cur_idx = len(nodes)
                nodes.append((cur.key, level))
            if cur.right is not None:
                right_level = cur.right_level(level)
                right_cond = (
                    (from_level is None or from_level <= right_level) and
                    (to_key is _missing or cur.key < to_key))
                if right_cond:
                    right_idx = sub(cur.right, right_level)

            # adds the edges
            if cur_idx is not None:
                if left_idx is not None:
                    edges.append((cur_idx, left_idx))
                if right_idx is not None:
                    edges.append((cur_idx, right_idx))
                return cur_idx
            return None
        
        if self.first is not None:
            sub(self.first, self.get_height())
        return nodes, edges

def sample_path_lengths(tree: Tree[float, Any] | Tree[int, Any],
                        num_samples: int):
    """NOTE: This assumes keys are uniformly distributed"""
    lengths = [0] * num_samples
    if tree.first is None:
        return lengths
    
    # finds the key interval
    cur = tree.first
    while True:
        if cur.left is None:
            min_key = cur.key
            break
        cur = cur.left
    cur = tree.first
    while True:
        if cur.right is None:
            max_key = cur.key
            break
        cur = cur.right

    for i in range(num_samples):
        # NOTE: the precise key value is not important
        key = min_key + random()*(max_key-min_key)
        count = 0
        cur = tree.first
        while cur is not None:
            count += 1
            if cur.key < key:
                cur = cur.right
            else:
                cur = cur.left
        lengths[i] = count
    return lengths

@dataclass
class PathLenStats:
    min_len: int = 0
    max_len: int = 0
    num_leaves: int = 0
    mean_len: float = 0
    std_len: float = 0

def path_length_stats(tree: Tree) -> PathLenStats:
    """NOTE: This only considers root->leaf paths."""
    min_len = 0
    max_len = 0
    num_leaves = 0
    first_len = 0
    tot_len = 0
    # NOTE: The shift avoids numerical problems especially with floats, but
    #   here we could use rational numbers.
    tot_sqslen = 0              # sum of squared shifted lengths
    
    def sub(cur: Node, len_so_far: int = 0):
        nonlocal min_len, max_len, num_leaves, tot_len, tot_sqslen, first_len
        len_so_far += 1
        leaf = False
        for c in [cur.left, cur.right]:
            if c is not None:
                sub(c, len_so_far)
            else:
                leaf = True
        if leaf:
            if first_len == 0:
                first_len = len_so_far
                min_len = max_len = len_so_far
            elif len_so_far > max_len: max_len = len_so_far
            elif len_so_far < min_len: min_len = len_so_far
            num_leaves += 1
            tot_len += len_so_far
            delta = len_so_far - first_len
            tot_sqslen += delta*delta
    
    if tree.first is not None:
        sub(tree.first)
        mean_len = tot_len / num_leaves
        mean_slen = mean_len - first_len
        std_len = sqrt(tot_sqslen/num_leaves - mean_slen*mean_slen)
        return PathLenStats(
            min_len=min_len,
            max_len=max_len,
            num_leaves=num_leaves,
            mean_len=mean_len,
            std_len=std_len
        )
    return PathLenStats()

def get_path_lengths(tree: Tree):
    """NOTE: This only considers root->leaf paths."""
    lengths = np.empty(len(tree))
    i: int = 0

    def sub(cur: Node, len_so_far: int = 0):
        nonlocal i
        len_so_far += 1
        leaf = False
        for c in [cur.left, cur.right]:
            if c is not None:
                sub(c, len_so_far)
            else:
                leaf = True
        if leaf:
            lengths[i] = len_so_far
            i += 1
    
    if tree.first is not None:
        sub(tree.first)
        return lengths[:i]
    return None

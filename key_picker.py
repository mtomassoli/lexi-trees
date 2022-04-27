from __future__ import annotations
import queue
from random import random
from typing import Any, Generic, Literal, Protocol

from figures import savefig
from generic import K, K_Cov

class KeyWithOrder(Generic[K]):
    key: K
    order: float
    def __init__(self, key: K):
        self.key = key
        self.order = random()
        
    def __lt__(self, other: Any) -> bool:       # `other: Self` in the future
        return self.order < other.order

class KeyPicker(Protocol[K_Cov]):
    def get_ins_key(self) -> K_Cov:
        """NOTE: The returned key is remembered and can be returned by
        get_del_key."""
        ...

    def get_del_key(self) -> K_Cov | None:
        """NOTE: The returned key is forgotten."""

class UniformKeyPicker(KeyPicker[float]):
    max_key: float
    int_key: bool

    # contains keys in tree but "in random order"
    _current_keys: queue.PriorityQueue[KeyWithOrder[float]]

    # prob. of generating new rand keys
    insert_new_rand_prob: float
    delete_new_rand_prob: float
    
    def __init__(self, max_key: float = 1000, *, int_key: bool = False,
                 insert_new_rand_prob: float = 0.9,
                 delete_new_rand_prob: float = 0.1) -> None:
        self.max_key = max_key
        self.int_key = int_key
        self.insert_new_rand_prob = insert_new_rand_prob
        self.delete_new_rand_prob = delete_new_rand_prob
        self._current_keys = queue.PriorityQueue()

    def _get_key(self, op: Literal['insert', 'delete']) -> float:
        """NOTE: the returned key is always forgotten."""
        p = self.insert_new_rand_prob if op == 'insert' \
            else self.delete_new_rand_prob
        if random() < p:
            key = random() * self.max_key
            return round(key) if self.int_key else key
        try:
            return self._current_keys.get_nowait().key
        except queue.Empty:
            key = random() * self.max_key
            return round(key) if self.int_key else key
    
    def get_ins_key(self) -> float:
        key = self._get_key('insert')
        # remembers `key` and gives it a random order
        self._current_keys.put_nowait(KeyWithOrder(key))
        return key
    
    def get_del_key(self) -> float | None:
        return self._get_key('delete')

class IncFifoKeyPicker(KeyPicker[float]):
    _start_key: int = 0
    _end_key: int = 0
    
    def __init__(self, inc: int) -> None:
        self._inc = inc
    
    def get_ins_key(self):
        self._end_key += self._inc
        return self._end_key - self._inc

    def get_del_key(self):
        if self._start_key != self._end_key:
            self._start_key += self._inc
            return self._start_key - self._inc
        return None

class IncLifoKeyPicker(KeyPicker[float]):
    _end_key: int = 0
    
    def __init__(self, inc: int) -> None:
        self._inc = inc
    
    def get_ins_key(self):
        self._end_key += self._inc
        return self._end_key - self._inc

    def get_del_key(self):
        if self._end_key != 0:
            self._end_key -= self._inc
            return self._end_key
        return None

def _get_center_key(count: int):
    sign = 1 - 2*(count & 1)
    return sign * 1/count

class CenterFifoKeyPicker(KeyPicker[float]):
    _start_count: int = 0
    _end_count: int = 0

    def get_ins_key(self):
        self._end_count += 1
        return _get_center_key(self._end_count)

    def get_del_key(self):
        if self._start_count != self._end_count:
            self._start_count += 1
            return _get_center_key(self._start_count)
        return None

class CenterLifoKeyPicker(KeyPicker[float]):
    _end_count = 0

    def get_ins_key(self):
        self._end_count += 1
        return _get_center_key(self._end_count)

    def get_del_key(self):
        if self._end_count != 0:
            self._end_count -= 1
            return _get_center_key(self._end_count + 1)
        return None

def draw_key_picker(ax: Axes, kp: KeyPicker[float], n: int = 100):
    ins_keys = np.empty(n, dtype=np.float64)
    del_keys = np.empty(n, dtype=np.float64)
    for i in range(n):
        ins_keys[i] = kp.get_ins_key()
    for i in range(n):
        k = kp.get_del_key()
        assert k is not None
        del_keys[i] = k
    ax.scatter(np.arange(n), ins_keys, color='blue')
    ax.scatter(np.arange(n, 2*n), del_keys, color='red')

def _show_all_key_pickers(n: int = 50, save_to: str = ''):
    fig = set_figure(figsize=(15, 15), dpi=80)
    kp_pairs = [
        (UniformKeyPicker(1),),
        (CenterFifoKeyPicker(), CenterLifoKeyPicker()),
        (IncFifoKeyPicker(1), IncLifoKeyPicker(1)),
        (IncFifoKeyPicker(-1), IncLifoKeyPicker(-1)),
    ]
    title_pairs = [
        ("Uniform",),
        ("Center FIFO", "Center LIFO"),
        ("Inc FIFO", "Inc LIFO"),
        ("Dec FIFO", "Dec LIFO"),
    ]
    num_rows = len(kp_pairs)
    for i, (kps, titles) in enumerate(zip(kp_pairs, title_pairs)):
        for j, (kp, title) in enumerate(zip(kps, titles)):
            num_cols = len(kps)
            ax = fig.add_subplot(num_rows, num_cols, 1 + 2*i+j)
            ax.set_title(title)
            draw_key_picker(ax, kp, n*2//num_cols)
    plt.suptitle("KeyPickers", size=20)
    legend_elements = [Line2D([0], [0], color='b', lw=4, label='Insert'),
                       Line2D([0], [0], color='r', lw=4, label='Delete')]
    fig.legend(handles=legend_elements, handlelength=5, borderpad=1.2,
               labelspacing=1.2, loc=(.8, .91))
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)
    if save_to:
        savefig(save_to)
    plt.show()

if __name__ == '__main__':
    from matplotlib import pyplot as plt
    from matplotlib.axes import Axes
    from matplotlib.lines import Line2D
    from figures import set_figure

    import numpy as np
    _show_all_key_pickers(save_to='images/key_pickers.svg')

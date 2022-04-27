# NOTE: This code was modified countless times and was not written with
#   readability in mind. It just works!

from __future__ import annotations
from dataclasses import dataclass
from math import pi, sin, log2
from random import random, seed
from time import time
from typing import Any, Literal
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
import numpy as np

from D2LTree import D2LTree
from D3LTree import D3LTree
from PLTree import PLTree
from generic import Tree, get_path_lengths
from misc import *
from figures import savefig, set_figure
from key_picker import (
    CenterFifoKeyPicker, CenterLifoKeyPicker, IncFifoKeyPicker,
    IncLifoKeyPicker, KeyPicker, UniformKeyPicker
)

def _print_progress(tree: Tree, *, i: int, num_ops: int, num_inserts: int):
    ins_frac = 0 if i == 0 else 100*num_inserts/i
    print(f"done: {100*i/num_ops:.2f}% ({i}/{num_ops}); "
          f"len: {len(tree)}; inserts: {ins_frac:.2f}%")

def _get_len_ratio_qs(tree: Tree):
    tree_size = len(tree)
    if tree_size > 0:
        logn = log2(tree_size+1)
        lengths = get_path_lengths(tree)
        assert lengths is not None
        qs = np.quantile(lengths, np.linspace(0, 1, num=19))
        row: list[float] = (qs / logn).tolist()
        return row
    return None

def _print_len_ratio_qs(qs: list[float]):
    row_str = " | ".join([f"{r:.2f}" for r in qs])
    print("len_ratio_qs: " + row_str)

@dataclass
class TestStats:
    insert_probs: list[float]
    tree_sizes: list[int]
    # Quantiles of path lengths divided by log(n+1), the optimal path length,
    # collected at regular intervals of time.
    len_ratio_qs: list[list[float]]

def test(
    my_map: Tree[float, float], num_ops: int, num_cycles: int, *,
    key_picker: KeyPicker[float], print_tree_every: int | None = None,
    print_ops: bool = False, print_progress: bool = True,
    print_len_ratio_qs: bool = True, inserts_only: bool = True,
    check_every: int | None = None, progress_every: int | None = None,
    len_ratio_qs_every: int | None = None
) -> TestStats:
    if inserts_only:
        print('-------------------------------------------------------------\n'
              'WARNING: inserts_only = True\n'
              '-------------------------------------------------------------')
    map: dict[float, float] = {}
    test_stats: TestStats = TestStats([], [], [])

    def check():
        my_map._check()
        assert len(map) == len(my_map)
        for (k, v) in map.items():
            assert v == my_map[k]
    
    num_inserts = 0
    insert_prob = 0
    
    def print_cond(i: int, every: int | None):
        return every is not None and (i == num_ops or i % every == 0)
    
    def progress_and_stats(i: int):
        if print_cond(i, progress_every):
            test_stats.insert_probs.append(insert_prob)
            test_stats.tree_sizes.append(len(my_map))
            if print_progress:
                _print_progress(my_map, i=i, num_ops=num_ops,
                                num_inserts=num_inserts)
        if print_cond(i, len_ratio_qs_every):
            len_ratio_qs = _get_len_ratio_qs(my_map)
            if len_ratio_qs is not None:
                if print_len_ratio_qs:
                    _print_len_ratio_qs(len_ratio_qs)
                test_stats.len_ratio_qs.append(len_ratio_qs)

    for i in range(num_ops):
        t = i/num_ops * 2*pi*num_cycles         # in [0, 2pi num_cycles]
        insert_prob = (sin(t) + 1) / 2          # in [0, 1]
        progress_and_stats(i)
        if inserts_only or random() < insert_prob:
            key = key_picker.get_ins_key()
            val = random()
            if print_ops:
                print(f"Insert {key}")
            assert (key in my_map) == (key in map)
            my_map[key] = val
            map[key] = val
            assert my_map[key] == map[key] == val
            num_inserts += 1
        else:
            key = key_picker.get_del_key()
            if key is not None:
                if print_ops:
                    print(f"Remove {key}")
                ret1 = my_map.remove(key, None)
                ret2 = map.pop(key, None)
                assert ret1 == ret2
        if print_tree_every is not None and (i + 1) % print_tree_every == 0:
            print(f'i = {i} --------------------------------------')
            my_map.pretty_print()
            print()
        if check_every is not None and (i + 1) % check_every == 0:
            check()
    progress_and_stats(num_ops)
    return test_stats

TestType = Literal['uniform', 'inc_fifo', 'inc_lifo', 'dec_fifo', 'dec_lifo',
                   'center_fifo', 'center_lifo']
key_pickers = dict(
    uniform = UniformKeyPicker,
    inc_fifo = lambda: IncFifoKeyPicker(1),
    dec_fifo = lambda: IncFifoKeyPicker(-1),
    inc_lifo = lambda: IncLifoKeyPicker(1),
    dec_lifo = lambda: IncLifoKeyPicker(-1),
    center_lifo = CenterLifoKeyPicker,
    center_fifo = CenterFifoKeyPicker,
)

TreeType = Literal['prob', 'det2', 'det3']

class TestConf:
    tree_type: TreeType
    test_type: TestType
    num_ops: int
    num_cycles: int
    ins_only: bool
    
    # bool = do it or not; int = do it at the specified interval
    len_ratio_qs_every: bool | int
    check_every: bool | int
    progress_every: bool | int
    
    min_kwargs: dict[str, Any]
    max_kwargs: dict[str, Any]
    median_kwargs: dict[str, Any]
    fill_kwargs: dict[str, Any]
    show_image: bool
    save_image: bool
    save_stats: bool
    
    def __init__(self, tree_type: TreeType, test_type: TestType,
                 num_ops: int, num_cycles: int, *, ins_only: bool = False,
                 progress_every: bool | int = True,
                 len_ratio_qs_every: bool | int = True,
                 check_every: bool | int = True,
                 def_kwargs: dict[str, Any] | None = None,
                 min_kwargs: dict[str, Any] | None = None,
                 max_kwargs: dict[str, Any] | None = None,
                 median_kwargs: dict[str, Any] | None = None,
                 fill_kwargs: dict[str, Any] | None = None,
                 show_image: bool = False, save_image: bool = True,
                 save_stats: bool = True):
        """NOTE: both progress and len_ratio_qs are considered stats"""
        self.tree_type = tree_type
        self.test_type = test_type
        self.num_ops = num_ops
        self.num_cycles = num_cycles
        self.ins_only = ins_only
        self.progress_every = progress_every
        self.len_ratio_qs_every = len_ratio_qs_every
        self.check_every = check_every

        median_def_kwargs = default(def_kwargs, dict(color='black', lw=2))
        def_kwargs = default(def_kwargs, dict(color='blue'))
        self.min_kwargs = default(min_kwargs, def_kwargs)
        self.max_kwargs = default(max_kwargs, def_kwargs)
        self.median_kwargs = default(median_kwargs, median_def_kwargs)
        self.fill_kwargs = default(fill_kwargs, def_kwargs)

        self.show_image = show_image
        self.save_image = save_image
        self.save_stats = save_stats

    def _make_title(self, tree_str: str):
        plural = 's' if self.num_cycles > 1 else ''
        cycles_str = f"{self.num_cycles} cycle{plural}"
        cycles_str = 'insertions only' if self.ins_only else cycles_str
        test_type = self.test_type.capitalize()
        return (f'{test_type} test with {tree_str}: '
                f'{self.num_ops} nodes with {cycles_str}')

    def _make_fname(self, tree_str: str):
        cycles_str = 'ins_only' if self.ins_only else f"c{self.num_cycles}"
        return f'{tree_str}_{self.test_type}_{self.num_ops}_{cycles_str}_test'
    
    @staticmethod
    def _tree_name_of(tree_type: TreeType):
        return ('P-Lexi' if tree_type == 'prob' else
                '2-Lexi' if tree_type == 'det2' else '3-Lexi')
        
    @property
    def tree_name(self):
        return self._tree_name_of(self.tree_type)
        
    @property
    def title(self):
        return self._make_title(self.tree_name + ' Tree')

    @property
    def base_fname(self):
        return self._make_fname(self.tree_type)
                          
    def title_vs(self, tree1_type: TreeType, tree2_type: TreeType):
        name1 = self._tree_name_of(tree1_type)
        name2 = self._tree_name_of(tree2_type)
        return self._make_title(f'{name1} VS {name2} Trees')

    def fname_vs(self, tree1_type: TreeType, tree2_type: TreeType):
        return self._make_fname(f'{tree1_type}_vs_{tree2_type}')

def do_test(test_conf: TestConf):
    tc = test_conf
    kp = key_pickers[tc.test_type]()
    tree_class = {'prob': PLTree, 'det2': D2LTree, 'det3': D3LTree}
    tree: Tree = tree_class[tc.tree_type](0., 0.)

    every = max(1, tc.num_ops//100)
    def get_every(x):
        return None if x is False else every if x is True else x
    
    len_ratio_qs_every = get_every(tc.len_ratio_qs_every)
    check_every = get_every(tc.check_every)
    progress_every = get_every(tc.progress_every)

    t = time()
    stats = test(tree, tc.num_ops, tc.num_cycles, key_picker=kp,
                 inserts_only=tc.ins_only, progress_every=progress_every,
                 check_every=check_every,len_ratio_qs_every=len_ratio_qs_every)
    print(f"time = {time()-t:.2f}")
    if tc.save_stats:
        if stats.len_ratio_qs:
            len_ratio_qs = np.array(stats.len_ratio_qs, dtype=np.float64)
            np.savetxt(f'data/{tc.base_fname}.txt', len_ratio_qs)
        if stats.insert_probs:
            progress = np.array([stats.insert_probs, stats.tree_sizes],
                                dtype=np.float64).T
            np.savetxt(f'data/{tc.base_fname}_progress.txt', progress)

def _plot_test_graph(test_conf: TestConf, ax: Axes, all_lines: bool = True):
    rows = np.loadtxt(f'data/{test_conf.base_fname}.txt')
    xs = np.arange(rows.shape[0])
    if all_lines:
        num_qs = rows.shape[1]
        assert num_qs & 1 == 1
        i_mid = (num_qs-1)//2
        ax.plot(rows[:, i_mid], **test_conf.median_kwargs)      # median
        ax.plot(rows[:, 0], **test_conf.min_kwargs)             # min
        ax.plot(rows[:, -1], **test_conf.max_kwargs)            # max
        for i in range(i_mid):
            # NOTE: Uses 2 different draws to avoid overlaps in case one needs
            #   alpha < 1 for visualizing multiple data.
            # color = cmap(0.05 + i/i_mid*0.95)           # little compression
            alpha = 0.05 + i/i_mid*0.95
            ax.fill_between(xs, rows[:, i], rows[:, i+1], alpha=alpha,
                            **test_conf.fill_kwargs)
            ax.fill_between(xs, rows[:, -i-1], rows[:, -i-2], alpha=alpha,
                            **test_conf.fill_kwargs)
    
def draw_test_graph(test_conf: TestConf):
    fig = set_figure(figsize=(15, 7), dpi=80)
    ax = fig.add_subplot(1, 1, 1)
    _plot_test_graph(test_conf, ax)
    plt.title(test_conf.title)
    plt.suptitle(r'Quantiles of path lengths divided by $\log_2{(n+1)}$',
                 fontsize=15)
    plt.tight_layout()
    if test_conf.save_image:
        savefig(f'images_tests/{test_conf.base_fname}.svg')
    if test_conf.show_image:
        plt.show()

def draw_vs_test_graph(test_confs: list[TestConf], *, title: str,
                       show: bool = True, save_to: str = ''):
    fig = set_figure(figsize=(15, 7), dpi=80)
    ax = fig.add_subplot(1, 1, 1)

    tree_names = []
    legend_elements = []
    for tc in test_confs:
        _plot_test_graph(tc, ax)
        if 'color' not in tc.fill_kwargs:
            raise ValueError("Can't determine the color for the quantiles")
        tree_names.append(tc.tree_name)
        legend_elements.append(Line2D([0], [0], color=tc.fill_kwargs['color'],
                                      lw=4, label=tree_names[-1] + ' Tree'))
    col_meds = [tc.median_kwargs.get('color') for tc in test_confs]
    if any(c is None for c in col_meds):
        raise ValueError("Can't determine the color for the medians")
    if all(c == col_meds[0] for c in col_meds):         # all same color
        legend_elements.append(Line2D([0], [0], color=col_meds[0], lw=4,
                                      label='median'))
    else:
        for col, name in zip(col_meds, tree_names):
            legend_elements.append(Line2D([0], [0], color=col, lw=4,
                                          label=name + ' median'))
        
    plt.legend(handles=legend_elements)
    plt.title(title)
    plt.suptitle(r'Quantiles of path lengths divided by $\log_2{(n+1)}$',
                 fontsize=15)
    plt.tight_layout()
    if save_to:
        savefig(f'images_tests/{save_to}.svg')
    if show:
        plt.show()

def draw_tree_vs_tree(test_type: TestType, tree1_type: TreeType,
                      tree2_type: TreeType, num_ops: int, num_cycles: int, *,
                      ins_only: bool = False, show: bool = True,
                      save: bool = False):
    test_confs = [
        TestConf(tree1_type, test_type, num_ops, num_cycles, ins_only=ins_only,
                 def_kwargs=dict(color='green'),
                 median_kwargs=dict(color='yellow', lw=2)),
        TestConf(tree2_type, test_type, num_ops, num_cycles, ins_only=ins_only,
                 def_kwargs=dict(color='blue'),
                 median_kwargs=dict(color='red', lw=2)),
    ]
    save_to = test_confs[0].fname_vs(tree1_type, tree2_type) if save else ''
    draw_vs_test_graph(test_confs, show=show, save_to=save_to,
                       title=test_confs[0].title_vs(tree1_type, tree2_type))

def do_all_tests(*, draw_only=False):
    tree_types: list[TreeType] = ['prob', 'det2', 'det3']
    test_types: list[TestType] = [
       'center_fifo', 'center_lifo', 'uniform', 'inc_fifo', 'inc_lifo',
       'dec_fifo', 'dec_lifo',
    ]
    num_ops = 10_000_000
    num_cycles = 2
    tree_type = 'prob'
    test_conf_io = TestConf(tree_type, 'uniform', num_ops, num_cycles,
                            ins_only=True)
    test_conf = TestConf(tree_type, 'uniform', 2*num_ops, num_cycles,
                         ins_only=False)
    for tree_type in tree_types:
        for test_type in test_types:
            for tc in [test_conf, test_conf_io]:
                tc.tree_type = tree_type
                tc.test_type = test_type
                if not draw_only:
                    do_test(tc)
                draw_test_graph(tc)

def draw_test_progress(test_conf: TestConf, title: str = ''):
    progress = np.loadtxt(f'data/{test_conf.base_fname}_progress.txt')
    fig = set_figure(figsize=(15, 7), dpi=80)
    ax1 = fig.add_subplot(1, 1, 1)
    ax1.plot(progress[:, 0], color='b', label="Prob(insert)")
    ax2 = plt.twinx(ax1)
    ax2.plot(progress[:, 1], color='g', label="len(tree)")
    ax1.legend(loc='upper left', fontsize=12)
    ax2.legend(loc='upper right', fontsize=12)
    if title: plt.title(title, fontsize=14)
    plt.tight_layout()
    if test_conf.save_image:
        savefig(f'images_tests/{test_conf.base_fname}_progress.svg')
    if test_conf.show_image:
        plt.show()

def main_test_progress(*, draw_only=False):
    num_ops = 10_000_000
    num_cycles = 2
    test_conf = TestConf('det3', 'uniform', num_ops, num_cycles,
                         len_ratio_qs_every=False, show_image=True)
    if not draw_only:
        do_test(test_conf)
    plural = 's' if num_cycles > 1 else ''
    title = f"{num_cycles} cycle{plural}"
    draw_test_progress(test_conf, title)
    
def main_do_single_test():
    test_conf = TestConf(
        tree_type='det2',
        test_type='uniform',
        num_ops=1_000_000,
        num_cycles=2,
        ins_only=False,
        save_stats=True,
        save_image=True,
        show_image=True,
    )
    do_test(test_conf)
    if test_conf.save_image and test_conf.show_image:
        draw_test_graph(test_conf)
    
def draw_all_vs_graphs(tree1_type: TreeType, tree2_type: TreeType, *,
                       show: bool = False, save: bool = True):
    test_types: list[TestType] = [
       'center_fifo', 'center_lifo', 'uniform', 'inc_fifo', 'inc_lifo',
       'dec_fifo', 'dec_lifo',
    ]
    for test_type in test_types:
        for num_ops, ins_only in [(10_000_000, True), (20_000_000, False)]:
            draw_tree_vs_tree(
                test_type, tree1_type, tree2_type, num_ops=num_ops,
                num_cycles=2, ins_only=ins_only, show=show, save=save)
            
if __name__ == "__main__":
    seed(45)
    # main_do_single_test()

    main_test_progress(draw_only=True)

    do_all_tests(draw_only=True)
    draw_all_vs_graphs('prob', 'det2')
    draw_all_vs_graphs('det3', 'det2')

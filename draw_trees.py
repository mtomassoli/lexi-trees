# NOTE: This code was modified countless times and was not written with
#   readability in mind. It even requires some live editing!

from __future__ import annotations
from dataclasses import dataclass
from itertools import zip_longest
from math import floor
from pathlib import Path
from typing import Any, Generic, Iterable, Literal, Tuple, overload, cast
from matplotlib.axes import Axes
import networkx as nx
import matplotlib.pyplot as plt
from random import random, seed
from PIL import Image
import os

from figures import savefig, set_figure, showfig
from misc import _Missing, _missing
from PLTree import PLTree
from D2LTree import MAX_LEVEL
from D2LTree_WithSteps import D2LTree_WithSteps as D2LTree
from D3LTree_WithSteps import D3LTree_WithSteps as D3LTree
from PLTree import _PNode
from DLTree_misc import _DNode
from generic import K, Node, Tree

@dataclass
class DrawOpts(Generic[K]):
    scale: float = 1
    from_level: int | None=None
    to_level: int | None=None
    from_key: K | _Missing=_missing
    to_key: K | _Missing=_missing
    colors: dict[K, str] | None=None
    size_scales: dict[K, float] | None=None
    # Annotations are external labels. The dict is the kwargs for plt.annotate.
    annotations: dict[K, dict[str, Any]] | None=None
    keys_to_draw: set[K] | None=None
    with_labels: bool=False                         # internal labels
    arrow_heads: bool=False

def draw_tree(tree: Tree, opts: DrawOpts[int], save_to: str = '',
              save_dpi: int | None = None, key_line: int | None = None,
              show: bool = True, xlim: Tuple[float, float] | None = None,
              ylim: Tuple[float, float] | None = None, title: str = ''):
    nodes, edges = tree.get_graph(
        from_level=opts.from_level, to_level=opts.to_level,
        from_key=opts.from_key, to_key=opts.to_key)
    edges_by_key = [(nodes[i][0], nodes[j][0]) for i, j in edges]
    if opts.keys_to_draw is not None:
        ktd = opts.keys_to_draw
        nodes = [n for n in nodes if n[0] in ktd]
        edges_by_key = [(f, t) for f, t in edges_by_key
                        if f in ktd and t in ktd]

    G = nx.DiGraph() if opts.arrow_heads else nx.Graph()
    G.add_edges_from(edges_by_key)
    # sets the node positions explicitly
    pos = {key: (i, level) for i, (key, level) in enumerate(nodes)}
    key_pos = 0
    if key_line is not None:
        for i, n in enumerate(nodes):
            if n[0] == key_line:        # we're on the key line
                key_pos = i
                break
            elif n[0] > key_line:       # we crossed the key line
                key_pos = i - 0.5
                break
    scale = opts.scale
    options = {
        "font_size": scale*16,
        "node_size": scale*500,
        "node_color": "white" if opts.with_labels else "black",
        "edgecolors": "black",
        "linewidths": scale*2,
        "width": scale*2,
        "with_labels": opts.with_labels,
    }
    if opts.colors is not None:
        options['node_color'] = [opts.colors.get(n, 'black') for n in G]
    if opts.size_scales is not None:
        options['node_size'] = [
            opts.size_scales.get(n, scale)*500 for n in G]
    fig = set_figure(figsize=(15, 7), dpi=80)
    if xlim is not None:
        plt.xlim(*xlim)
    if ylim is not None:
        plt.ylim(*ylim)
    # fig.add_subplot(1, 1, 1)
    ax: Axes = fig.gca()
    
    nx.draw_networkx(G, pos, ax=ax, **options)
    if key_line is not None:
        plt.axvline(key_pos, color='red')
    if opts.annotations is not None:
        for (key, coords) in pos.items():
            kwargs = opts.annotations.get(key)
            if kwargs is not None and 'text' in kwargs:
                text = kwargs['text']
                kwargs = {k: v for k, v in kwargs.items() if k != 'text'}
                plt.annotate(text, xy=coords, **kwargs)

    if title:
        plt.title(title)
    plt.tight_layout()
    if save_to:
        savefig(save_to, save_dpi)
    if show:
        showfig()

def get_search_path(tree: Tree, key: int):
    nodes: list[Node] = []
    cur = tree.first
    while cur is not None:
        nodes.append(cur)
        if cur.key < key:
            cur = cur.right
        else:
            cur = cur.left
    return nodes

def get_missing_siblings(nodes: list[Node]):
    # NOTE: The assertions for _PNode and _DNode are necessary because I
    #   couldn't make the `Self` type work in `Node` the way I want.
    nset = set(nodes)
    siblings = []
    if not nodes:
        return siblings
    prob = isinstance(nodes[0], _PNode)
    for n in nodes:
        for c in [n.left, n.right]:
            if c is None:
                continue
            if prob:
                assert isinstance(c, _PNode)
                level = c.level
                # adds all siblings, including high right nodes
                while c is not None and c.level == level:
                    if c not in nset:
                        siblings.append(c)
                    c = c.right
                    assert isinstance(c, _PNode)
            else:
                assert isinstance(c, _DNode)
                while c is not None:
                    if c not in nset:
                        siblings.append(c)
                    if not c.high_right:
                        break
                    c = c.right
                    assert isinstance(c, _DNode)
    return siblings

def get_side_nodes(tree: PLTree[int, int], key: int, level: int):
    """NODE: There must be no node with key `key` in `tree`."""
    prev, cur, prev_cmp, cur_cmp = tree._find_insertion_pos(key, level)
    if cur_cmp == 0:
        raise ValueError(f'The tree must not contain the specified key {key}')
    nodes: list[_PNode[int, int] | None] = [None] * (4*(tree._maxLevel+1) + 3)
    tree._get_side_pairs(key, cur, cur_cmp, nodes)
    return [n for n in nodes if n is not None]

@dataclass
class SidesData:
    nodes: list[_PNode[int, int]]
    colors: dict[int, str]
    size_scales: dict[int, float]
    annotations: dict[int, dict[str, Any]] | None

def complete_side_nodes(nodes: list[_PNode[int, int]], key: int, *,
                        scale: float = 1.0, gray_if_above: int | None = None,
                        sibs_depth: int = 0,
                        add_annotations: bool = False) -> SidesData:
    """NOTE: the trailing '_' means that the objects are modified."""
    colors = {n.key: 'green' if key < n.key else 'blue'
              for n in nodes}
    
    annotations: dict[int, dict[str, Any]] | None = None
    if add_annotations:
        annotations = {}
        num_blue = 0
        num_green = 0
        for n in nodes:
            if n.key not in annotations:
                if key < n.key:
                    num_green += 1
                    annotations[n.key] = dict(
                        text = f"$G_{{{num_green}}}$",
                        xytext = (6, -16),
                        textcoords = 'offset points',
                        fontsize = 'large'
                    )
                else:
                    num_blue += 1
                    annotations[n.key] = dict(
                        text = f"$B_{{{num_blue}}}$",
                        xytext = (-17.5, -17.5),
                        textcoords = 'offset points',
                        fontsize = 'large'
                    )
    
    size_scales = {}

    # Completes the chains by adding the nodes between first and last of each
    # (first, last) pair.
    middle: list[_PNode[int, int]] = []
    for f, t in zip_longest(nodes[::2], nodes[1::2], fillvalue=None):
        # NOTE: the last pair can be (f, None), but not (None, None).
        if t is None:
            break
        if f.key <= key:
            while f != t:
                assert f.right is not None
                middle.append(f.right)
                f = f.right
        else:
            while f != t:
                assert f.left is not None
                middle.append(f.left)
                f = f.left
    nodes = [*nodes, *middle]

    # Draws the siblings as smaller gray dots, to indicate they're secondary.
    siblings: list[_PNode[int, int]] = []
    for _ in range(sibs_depth):
        siblings.extend(get_missing_siblings(cast(list, nodes)))
        nodes.extend(siblings)
    for n in siblings:
        colors[n.key] = 'gray'
        size_scales[n.key] = scale*0.5

    if gray_if_above is not None:
        for n in nodes:
            if n.level > gray_if_above:
                colors[n.key] = 'gray'
        
    return SidesData(nodes, colors, size_scales, annotations)

def draw_nodes(tree: Tree, nodes: list[Node], opts: DrawOpts[int], *,
               key_line: int | None = None, save_to: str="", show: bool = True):
    opts.keys_to_draw = set(n.key for n in nodes)
    draw_tree(tree, opts, key_line=key_line, save_to=save_to, show=show)
    
def draw_search_path(tree: Tree, key: int, *, scale: float = 1.0,
                     save_to: str="", add_siblings: bool = False,
                     show: bool = True):
    nodes = get_search_path(tree, key)
    opts = DrawOpts(scale=scale)
    if add_siblings:
        siblings = get_missing_siblings(nodes)
        nodes.extend(siblings)
        opts.colors = {n.key: 'gray' for n in siblings}
        opts.size_scales = {n.key: scale*0.5 for n in siblings}
    draw_nodes(tree, nodes, opts, key_line=key, save_to=save_to, show=show)

def get_sides_opts(tree: PLTree[int, int], key: int, level: int, *,
                   opts_: DrawOpts[int], sibs_depth: int = 0,
                   add_annotations: bool = False):
    # NOTE: The real chains for a key at level L starts from L and go down, but
    #   we want to show the full chains for educational purposes.
        
    # gets the whole chains as if the insertion was at maxLevel
    nodes = get_side_nodes(tree, key, tree._maxLevel)
    # NOTE: the nodes of level > max_level are grayed out.
    sides_data = complete_side_nodes(nodes, key, gray_if_above=level,
                                     scale=opts_.scale, sibs_depth=sibs_depth,
                                     add_annotations=add_annotations)
    nodes_set = set(n.key for n in sides_data.nodes)
    opts_.keys_to_draw = nodes_set
    opts_.colors = sides_data.colors
    opts_.size_scales = sides_data.size_scales
    opts_.annotations = sides_data.annotations

@overload
def init_tree(_type: Literal['p'], num_nodes: int,
              max_key: int | None = None, *,
              reload: bool = True) -> PLTree[int, int]: ...
@overload
def init_tree(_type: Literal['d2'], num_nodes: int,
              max_key: int | None = None, *,
              reload: bool = True) -> D2LTree[int, int]: ...
@overload
def init_tree(_type: Literal['d3'], num_nodes: int,
              max_key: int | None = None, *,
              reload: bool = True) -> D3LTree[int, int]: ...

def init_tree(_type: Literal['p', 'd2', 'd3'], num_nodes: int,
              max_key: int | None = None, *, reload: bool = True):
    if max_key is None: max_key = 50*num_nodes
    tree: Tree[int, int]
    
    from pathlib import Path
    from dill import dump, load

    fpath = Path("data") / f"{_type}_tree_{num_nodes}.dat"
    if fpath.exists() and reload:
        print('loading tree...', end='')
        with open(str(fpath), 'rb') as f:
            tree = load(f)
        print('done')
    else:
        # inserts some nodes
        print('generating tree...', end='')
        tree = (PLTree(0, 0) if _type == 'p' else
                D2LTree(0, 0) if _type == 'd2' else D3LTree(0, 0))
        for _ in range(num_nodes):
            k = floor(random() * (max_key + 1))
            tree[k] = 0
        with open(str(fpath), 'wb') as f:
            dump(tree, f)
        print('done')
    return tree

def draw_search_paths(tree: Tree, keys: list[int], *, scale: float = 1.0,
                      save_to_base: str="", add_siblings: bool = False,
                      show: bool = True):
    p = Path(save_to_base)          # (makes Pyright happy)
    if save_to_base:
        save_to_base = str(p.with_suffix(''))
    for key in keys:
        print(f"drawing search path for key = {key}")
        save_to = f"{save_to_base}{key}{p.suffix}" if save_to_base else ""
        draw_search_path(tree, key, scale=scale, save_to=save_to,
                         add_siblings=add_siblings, show=show)

def main_prob_draw_insertion(
    tree: PLTree[int, int], key: int, level: int, *, scale: float = 1,
    sibs_depth: int = 0, show: bool = True, save_before_to: str = '',
    save_after_to: str = '', add_annotations: bool = False
):
    if key in tree:
        raise ValueError(f'The tree must not contain the specified key {key}')
    opts = DrawOpts[int](scale=scale)
    get_sides_opts(tree, key, level, opts_=opts, sibs_depth=sibs_depth,
                   add_annotations=add_annotations)
    assert opts.keys_to_draw is not None and opts.colors is not None

    draw_tree(tree, opts, key_line=key, show=show, save_to=save_before_to)

    tree.insert(key, 0, level)
    opts.keys_to_draw.add(key)
    opts.colors[key] = 'red'

    draw_tree(tree, opts, key_line=key, show=show, save_to=save_after_to)
    
    del tree[key]

def make_gif(frames_paths: list[str], gif_path: str):
    frames = [Image.open(f) for f in frames_paths]
    frames[0].save(gif_path, format='GIF', append_images=frames[1:],
                   save_all=True, duration=1500, loop=0)
    
def get_draw_opts(tree: Tree[int, int], key: int, *, scale: float = 1,
                  up_to_level: int | None = None, sibs_depth: int = 0):
    nodes = get_search_path(tree, key)
    opts = DrawOpts(scale=scale, to_level=up_to_level)
    siblings: list[_DNode[int, int]] = []
    for _ in range(sibs_depth):
        siblings.extend(get_missing_siblings(nodes))
        nodes.extend(siblings)
    opts.colors = {n.key: 'gray' for n in siblings}
    opts.size_scales = {n.key: scale*0.5 for n in siblings}
    opts.keys_to_draw = set(n.key for n in nodes)
    return opts

def highlight_key_node_and_leaf_(opts: DrawOpts, tree: D2LTree, key: int):
    _nodes: list[_DNode | None] = [None] * (2*(MAX_LEVEL+1) + 1)
    pd = tree._find_and_collect(key, _nodes)
    assert pd is not None and pd.key_node is not None
    key_node = pd.key_node
    leaf = _nodes[pd.last_idx]
    assert leaf is not None
    if opts.colors is None:
        opts.colors = {}
    opts.colors[key_node.key] = 'red'
    opts.colors[leaf.key] = 'green'
    kwargs = dict(textcoords = 'offset points', fontsize = 'large')
    opts.annotations = {
        key_node.key: dict(text = 'KN', xytext = (10, 5), **kwargs),
        leaf.key: dict(text = 'LE', xytext = (-20, -20), **kwargs),
    }

def save_frames(frames: Iterable[str], tree: Tree, key: int, opts: DrawOpts, *,
                gif_path: str, frames_base_fpath: str):
    xlim = None
    ylim = None
    fpaths: list[str] = []
    for frame_idx, frame_desc in enumerate(frames):
        fpaths.append(f'{frames_base_fpath}_{frame_idx}.png')
        draw_tree(tree, opts, key_line=key, save_to=fpaths[-1], save_dpi=200,
                  show=False, xlim=xlim, ylim=ylim, title=frame_desc)
        if xlim is None:
            xlim = plt.xlim()
            ylim = plt.ylim()

    make_gif(fpaths, gif_path)
    
    # deletes frame images
    for f in fpaths:
        os.remove(f)

def get_d2_insertion_opts(tree: D2LTree, key: int, *, scale: float = 1,
                          up_to_level: int | None = None, sibs_depth: int = 0):
    if key in tree:
        raise ValueError(f'The tree must not contain the specified key {key}')

    opts = get_draw_opts(tree, key, scale=scale, up_to_level=up_to_level,
                         sibs_depth=sibs_depth)
    assert opts.keys_to_draw is not None
    assert opts.colors is not None
    opts.keys_to_draw.add(key)
    opts.colors[key] = 'red'
    return opts

def main_det2_draw_insertion(
    tree: D2LTree[int, int], key: int, *, scale: float = 1, show: bool = True,
    save_before_to: str = '', save_after_to: str = '',
    no_rebalance: bool = False, up_to_level: int | None = None,
    sibs_depth: int = 0
):
    opts = get_d2_insertion_opts(
        tree, key, scale=scale, up_to_level=up_to_level, sibs_depth=sibs_depth)
    draw_tree(tree, opts, key_line=key, save_to=save_before_to, show=show)

    if no_rebalance:
        for _ in tree._insert_steps(key, 0):
            if key in tree:
                break           # skips rebalance
    else:
        tree[key] = 0

    draw_tree(tree, opts, key_line=key, show=show, save_to=save_after_to)
    if not no_rebalance:
        del tree[key]
    
def main_det2_anim_insertion(
    tree: D2LTree[int, int], key: int, *, gif_path: str,
    frames_base_fpath: str, scale: float = 1, up_to_level: int | None = None,
    sibs_depth: int = 0
):
    opts = get_d2_insertion_opts(
        tree, key, scale=scale, up_to_level=up_to_level, sibs_depth=sibs_depth)
    save_frames(tree._insert_steps(key, 0), tree, key, opts, gif_path=gif_path,
                frames_base_fpath=frames_base_fpath)
    del tree[key]

def main_det2_draw_deletion(
    tree: D2LTree[int, int], key: int, *, scale: float = 1, show: bool = True,
    save_before_to: str = '', save_after_to: str = '',
    no_rebalance: bool = False, up_to_level: int | None = None,
    sibs_depth: int = 0
):
    if key not in tree:
        raise ValueError(f'The tree must contain the specified key {key}')

    opts = get_draw_opts(tree, key, scale=scale, up_to_level=up_to_level,
                         sibs_depth=sibs_depth)
    highlight_key_node_and_leaf_(opts, tree, key)

    draw_tree(tree, opts, key_line=key, save_to=save_before_to, show=show)

    if no_rebalance:
        val = 0                 # (makes Pyright happy)
        for _ in tree._remove_steps(key):
            if key not in tree:
                break           # skips rebalance
    else:
        val = tree[key]
        del tree[key]

    draw_tree(tree, opts, key_line=key, show=show, save_to=save_after_to)
    if not no_rebalance:
        tree[key] = val
    
def main_det2_anim_deletion(
    tree: D2LTree[int, int], key: int, *, gif_path: str,
    frames_base_fpath: str, scale: float = 1, up_to_level: int | None = None,
    sibs_depth: int = 0
):
    if key not in tree:
        raise ValueError(f'The tree must contain the specified key {key}')

    opts = get_draw_opts(tree, key, scale=scale, up_to_level=up_to_level,
                         sibs_depth=sibs_depth)
    highlight_key_node_and_leaf_(opts, tree, key)
    
    val = tree[key]
    save_frames(tree._remove_steps(key), tree, key, opts, gif_path=gif_path,
                frames_base_fpath=frames_base_fpath)
    tree[key] = val

def get_d3_insertion_opts(tree: D3LTree, key: int, *, scale: float = 1,
                          up_to_level: int | None = None, sibs_depth: int = 0):
    if key in tree:
        raise ValueError(f'The tree must not contain the specified key {key}')

    opts = get_draw_opts(tree, key, scale=scale, up_to_level=up_to_level,
                         sibs_depth=sibs_depth)
    assert opts.keys_to_draw is not None
    assert opts.colors is not None
    opts.keys_to_draw.add(key)
    opts.colors[key] = 'red'

    # highlights the middle nodes of triples
    triples = get_triples(tree, key)
    for t in triples:
        assert t.right is not None
        opts.colors[t.right.key] = 'green'
    return opts

def main_det3_draw_insertion(
    tree: D3LTree[int, int], key: int, *, scale: float = 1, show: bool = True,
    save_before_to: str = '', save_after_to: str = '',
    up_to_level: int | None = None, sibs_depth: int = 0
):
    opts = get_d3_insertion_opts(
        tree, key, scale=scale, up_to_level=up_to_level, sibs_depth=sibs_depth)
    draw_tree(tree, opts, key_line=key, save_to=save_before_to, show=show)

    tree[key] = 0

    draw_tree(tree, opts, key_line=key, show=show, save_to=save_after_to)
    del tree[key]

def main_det3_anim_insertion(
    tree: D3LTree[int, int], key: int, *, scale: float = 1, gif_path: str,
    frames_base_fpath: str, up_to_level: int | None = None, sibs_depth: int = 0
):
    opts = get_d3_insertion_opts(
        tree, key, scale=scale, up_to_level=up_to_level, sibs_depth=sibs_depth)

    save_frames(tree._insert_steps(key, 0), tree, key, opts, gif_path=gif_path,
                frames_base_fpath=frames_base_fpath)
    del tree[key]
    
def get_d3_deletion_opts(tree: D3LTree, key: int, *, scale: float = 1,
                         up_to_level: int | None = None, sibs_depth: int = 0):
    if key not in tree:
        raise ValueError(f'The tree must contain the specified key {key}')

    opts = get_draw_opts(tree, key, scale=scale, up_to_level=up_to_level,
                         sibs_depth=sibs_depth)
    assert opts.keys_to_draw is not None
    assert opts.colors is not None
    
    # highlights the important nodes
    pd = tree._get_lowering_path(key)
    assert pd is not None and pd.key_node is not None
    opts.colors[pd.key_node.key] = 'red'
    cur = pd.lower_me
    while cur is not pd.leaf:           # LO->LE subpath
        assert cur is not None
        opts.colors[cur.key] = 'green'
        cur = cur.right
    opts.colors[pd.leaf.key] = 'yellow'

    kwargs = dict(textcoords = 'offset points', fontsize = 'large')
    opts.annotations = {
        pd.key_node.key: dict(text = 'KN', xytext = (-20, -20), **kwargs),
        pd.leaf.key: dict(text = 'LE', xytext = (-20, -20), **kwargs),
        pd.lower_me.key: dict(text = 'LO', xytext = (10, 5), **kwargs),
    }
    return opts

def main_det3_draw_deletion(
    tree: D3LTree[int, int], key: int, *, scale: float = 1, show: bool = True,
    save_before_to: str = '', save_after_to: str = '',
    up_to_level: int | None = None, sibs_depth: int = 0
):
    opts = get_d3_deletion_opts(tree, key, scale=scale,up_to_level=up_to_level,
                                sibs_depth=sibs_depth)
    draw_tree(tree, opts, key_line=key, save_to=save_before_to, show=show)

    val = tree[key]
    del tree[key]

    draw_tree(tree, opts, key_line=key, show=show, save_to=save_after_to)
    tree[key] = val

def main_det3_anim_deletion(
    tree: D3LTree[int, int], key: int, *, scale: float = 1, gif_path: str,
    frames_base_fpath: str, up_to_level: int | None = None, sibs_depth: int = 0
):
    opts = get_d3_deletion_opts(tree, key, scale=scale,up_to_level=up_to_level,
                                sibs_depth=sibs_depth)
    val = tree[key]
    save_frames(tree._remove_steps(key), tree, key, opts, gif_path=gif_path,
                frames_base_fpath=frames_base_fpath)
    tree[key] = val

def get_close_key(tree: Tree, key: int):
    cur = tree.first
    if cur is None:
        return None
    while True:
        if cur.key < key:
            next = cur.right
        elif key < cur.key:
            next = cur.left
        else:
            assert cur.key == key
            return key
        if next is None:
            return cur.key
        cur = next
        
def get_triples(tree: D3LTree[int, int], key: int):
    """Returns the first node of each triple."""
    triples: list[_DNode[int, int]] = []
    cur = tree._root.right
    if cur is None:
        return []
    
    def is_triple(node: _DNode[int, int]):
        if node.high_right and node.right is not None:
            r = node.right
            return r is not None and r.high_right and r.right is not None
        return False
    
    while True:
        if cur.key < key:
            next = cur.right
            if next is None:
                break
            if not cur.high_right and is_triple(next):
                triples.append(next)
        else:
            next = cur.left
            if next is None:
                break
            if is_triple(next):
                triples.append(next)
        cur = next
    return triples

def count_consec_lists(tree: D2LTree[int, int] | D3LTree[int, int], key: int,
                       list_len: int):
    count = 0
    cur = tree._root.right
    if cur is None:
        return count
    
    def is_list_ok(node: _DNode[int, int] | None):
        count = 0
        while node is not None:
            count += 1
            if node.high_right:
                node = node.right
            else: break
        return count == list_len
    
    while True:
        if cur.key < key:
            next = cur.right
            if not cur.high_right:
                count = count + 1 if is_list_ok(next) == list_len else 0
        else:
            next = cur.left
            count = count + 1 if is_list_ok(next) else 0
        if next is None:
            return count
        cur = next

def find_end_consec_lists(tree: D2LTree[int, int] | D3LTree[int, int],
                          max_key: int, list_len: int):
    """Tries to find search paths which end with as many consecutive lists of
    length `list_len` as possible.
    """
    def sub(cur: _DNode[int, int]):
        # Cur is the first node of its list. We consider all the children of
        # that list:
        #     * -> * -> *        (list)
        #    /    /    / \
        #  c1   c2   c3   c4     (children)
        max_consec_lists = 0
        uninterrupted = False
        max_key = cur.key
        cur_list_len = 1
        is_leaf = True
        while True:
            if cur.left is not None:
                is_leaf = False
                max_trip, unint, k = sub(cur.left)
                if max_trip > max_consec_lists:
                    max_consec_lists = max_trip
                    max_key = k
                if unint:
                    uninterrupted = True
                    # max_key = k         # (not needed)
                    # NOTE: If we break, we need to count list_len separately.
                    # break               # we can't do better
            if cur.right is not None:
                if cur.high_right:
                    cur = cur.right
                    cur_list_len += 1
                else:       # last node in the list
                    is_leaf = False
                    max_trip, unint, k = sub(cur.right)
                    if max_trip > max_consec_lists:
                        max_consec_lists = max_trip
                        max_key = k
                    if unint:
                        uninterrupted = True
                        # max_key = k         # (not needed)
                    break
            else:
                break
        assert cur_list_len <= 3
        cur_list_ok = cur_list_len == list_len
        if is_leaf:
            return 1 if cur_list_ok else 0, cur_list_ok, max_key
        if cur_list_ok and uninterrupted:
            return max_consec_lists + 1, True, max_key
        return max_consec_lists, False, max_key
    
    if tree._root.right is None:
        return None, 0
    max_consec_lists, _, max_key = sub(tree._root.right)
    return max_consec_lists, max_key

def remove_rand_keys(tree: Tree, num_keys: int,
                     key_min_max: Tuple[int, int]):
    kmin, kmax = key_min_max
    for _ in range(num_keys // 2):
        key = get_close_key(tree, round(kmin + random()*(kmax - kmin)))
        if key is not None: tree.remove(key)

ProbWhat = Literal['search', 'chains', 'chains_labels']

def draw_PTrees(what: ProbWhat, *, reload: bool = True):
    num_nodes = 1_000_000
    max_key = 50 * num_nodes
    scale = 0.2

    tree = init_tree('p', num_nodes, max_key=max_key, reload=reload)
    
    if what == 'search':
        keys = [37897720, 39189929, 34199197, 33407660, 24678893]
        save_to_base = ''
        # save_to_base = 'images/search_path_'
        for add_sibs, suffix in [(False, ''), (True, 'with_sibs_')]:
            st = save_to_base + suffix if save_to_base else ''
            draw_search_paths(tree, keys, scale=scale, save_to_base=st,
                              add_siblings=add_sibs, show=True)
    elif what == 'chains':
        key = 33407640
        levels = [0, 3, 7, 12, tree._maxLevel]
        for level in levels:
            save_before_to = save_after_to = ''
            # save_before_to = f'images/chains_before_ins_lev{level}.svg'
            # save_after_to = f'images/chains_after_ins_lev{level}.svg'
            main_prob_draw_insertion(
                tree, key, level, scale=scale, save_before_to=save_before_to,
                save_after_to=save_after_to, sibs_depth=False, show=True)
    elif what == 'chains_labels':
        key = 33407640
        level = tree._maxLevel
        save_before_to = save_after_to = ''
        # save_before_to = f'images/chains_before_ins_lev{level}_with_labels.svg'
        # save_after_to = f'images/chains_after_ins_lev{level}_with_labels.svg'
        main_prob_draw_insertion(
            tree, key, level, scale=scale, save_before_to=save_before_to,
            save_after_to=save_after_to, sibs_depth=False, show=True,
            add_annotations=True)
    else:
        raise ValueError(f"Unknown `what`: {what}")

def main_d2_op(tree: D2LTree, op: Literal['ins', 'del'], key: int, *,
               scale: float = 1.0, num_nodes: int, max_key: int,
               up_to_level: int | None = None, sibs_depth: int = 0):
    draw_op = (main_det2_draw_insertion if op == 'ins' else
               main_det2_draw_deletion)
    anim_op = (main_det2_anim_insertion if op == 'ins' else
               main_det2_anim_deletion)
    save_before_to = save_after_to = ''
    cropped = '' if up_to_level is None else '_cropped'
    save_before_to = f'images/d2-path_before_{op}1{cropped}.svg'
    save_after_to = f'images/d2-path_after_{op}1_no_rebalance{cropped}.svg'
    draw_op(tree, key, scale=scale, save_before_to=save_before_to, show=False,
            save_after_to=save_after_to, up_to_level=up_to_level,
            sibs_depth=sibs_depth, no_rebalance = True)

    # resets the tree
    tree = init_tree('d2', num_nodes, max_key=max_key)
    assert isinstance(tree, D2LTree)
    save_before_to = ''
    save_after_to = f'images/d2-path_after_{op}1{cropped}.svg'
    draw_op(tree, key, scale=scale, save_before_to=save_before_to, show=False,
            save_after_to=save_after_to, up_to_level=up_to_level,
            sibs_depth=sibs_depth)

    # resets the tree
    tree = init_tree('d2', num_nodes, max_key=max_key)
    assert isinstance(tree, D2LTree)
    base_path = f'images/d2-path_{op}1{cropped}'
    anim_op(tree, key, scale=scale, gif_path=base_path + '.gif',
            frames_base_fpath=base_path, up_to_level=up_to_level,
            sibs_depth=sibs_depth)

def main_d3_op(tree: D3LTree, op: Literal['ins', 'del'], key: int, *,
               scale: float = 1.0, num_nodes: int, max_key: int,
               up_to_level: int | None = None, sibs_depth: int = 0):
    draw_op = (main_det3_draw_insertion if op == 'ins' else
               main_det3_draw_deletion)
    anim_op = (main_det3_anim_insertion if op == 'ins' else
               main_det3_anim_deletion)
    save_before_to = save_after_to = ''
    cropped = '' if up_to_level is None else '_cropped'
    save_before_to = f'images/d3-path_before_{op}1{cropped}.svg'
    save_after_to = f'images/d3-path_after_{op}1{cropped}.svg'
    draw_op(tree, key, scale=scale, save_before_to=save_before_to, show=False,
            save_after_to=save_after_to, up_to_level=up_to_level,
            sibs_depth=sibs_depth)

    # resets the tree
    tree = init_tree('d3', num_nodes, max_key=max_key)
    assert isinstance(tree, D3LTree)
    base_path = f'images/d3-path_{op}1{cropped}'
    anim_op(tree, key, scale=scale, gif_path=base_path + '.gif',
            frames_base_fpath=base_path, up_to_level=up_to_level,
            sibs_depth=sibs_depth)

DetWhat = Literal[
    'tree_d2', 'tree_d3', 'search_path_d3', 'search_path_d2', 'insert_d2',
    'insert_d3', 'find_singles', 'find_pairs', 'find_triples', 'delete_d2',
    'delete_d3',
]

def draw_DTrees(tree_type: Literal['d2', 'd3'], what: DetWhat, *,
                reload: bool = True, cropped: bool = False):
    num_nodes = 1_000_000
    max_key = 1000 * num_nodes
    scale = 0.2
    
    if what.endswith('_d2'):
        tree_type = 'd2'
    elif what.endswith('_d3'):
        tree_type = 'd3'
    tree = init_tree(tree_type, num_nodes, max_key=max_key, reload=reload)

    if what == 'tree_d2':
        assert isinstance(tree, D2LTree)
        save_to = ''
        save_to = 'images/2-lexi-tree.svg'
        draw_tree(tree, DrawOpts(scale=scale), save_to=save_to)
    if what == 'tree_d3':
        assert isinstance(tree, D3LTree)
        save_to = ''
        # save_to = 'images/3-lexi-tree.svg'
        draw_tree(tree, DrawOpts(scale=scale), save_to=save_to)
    elif what == 'search_path_d2':
        # keys = [552841556+1]        # 13 consecutive pairs
        keys = [353617]
        save_to_base = ''
        # save_to_base = 'images/d2-search_path_'
        st = save_to_base + 'with_sibs_' if save_to_base else ''
        draw_search_paths(tree, keys, scale=scale, save_to_base=st,
                          add_siblings=True, show=True)
    elif what == 'search_path_d3':
        keys = [961829243+1]        # 4 consecutive triples
        save_to_base = ''
        # save_to_base = 'images/d3-search_path_'
        st = save_to_base + 'with_sibs_' if save_to_base else ''
        draw_search_paths(tree, keys, scale=scale, save_to_base=st,
                          add_siblings=True, show=True)
    elif what == 'find_singles':
        # useful for deletes
        kvls = tree.key_vals_levels(slice(7, 11))
        for k, _, _ in kvls:
            if count_consec_lists(tree, k, 1) >= 5:
                draw_search_paths(
                    tree, [k], scale=scale, add_siblings=True, show=False,
                    save_to_base='tmp/singles_.png')
    elif what == 'find_pairs':
        # useful for inserts_d2
        assert isinstance(tree, D2LTree)
        max_pairs, key = find_end_consec_lists(tree, max_key, 2)
        print(f"max_pairs = {max_pairs} with key {key}")
    elif what == 'find_triples':
        # useful for inserts_d3
        assert isinstance(tree, D3LTree)
        max_triples, key = find_end_consec_lists(tree, max_key, 3)
        print(f"max_triples = {max_triples} with key {key}")
    elif what == 'insert_d2':
        assert isinstance(tree, D2LTree)
        key = 552841556+1
        main_d2_op(tree, 'ins', key, scale=scale, num_nodes=num_nodes,
                   max_key=max_key, sibs_depth=1)
    elif what == 'insert_d3':
        assert isinstance(tree, D3LTree)
        key = 835603739+1
        utl, sd = (8, 2) if cropped else (None, 1)
        main_d3_op(tree, 'ins', key, scale=scale, num_nodes=num_nodes,
                   max_key=max_key, up_to_level=utl, sibs_depth=sd)
    elif what == 'delete_d2':
        assert isinstance(tree, D2LTree)
        key = 2865596
        utl, sd = (10, 2) if cropped else (None, 1)
        main_d2_op(tree, 'del', key, scale=scale, num_nodes=num_nodes,
                   max_key=max_key, up_to_level=utl, sibs_depth=sd)
    elif what == 'delete_d3':
        assert isinstance(tree, D3LTree)
        key = 768791888
        utl, sd = (10, 2) if cropped else (None, 1)
        main_d3_op(tree, 'del', key, scale=scale, num_nodes=num_nodes,
                   max_key=max_key, up_to_level=utl, sibs_depth=sd)
    else:
        raise ValueError(f"Unknown `what`: {what}")

def main_PTrees():
    seed(0)
    draw_PTrees('chains_labels')

def main_DTrees():
    tree_type: Literal['p', 'd2', 'd3'] = 'd3'
    # what: DetWhat = 'find_singles'     # for deletes
    # what: DetWhat = 'find_pairs'       # for insert_d2
    # what: DetWhat = 'find_triples'     # for insert_d3

    cropped = False
    # cropped = True
    
    # what: DetWhat = 'insert_d2'             # ignores cropped
    # what: DetWhat = 'delete_d2'
    # what: DetWhat = 'insert_d3'
    what: DetWhat = 'delete_d3'

    if what.endswith('_d2'):
        tree_type = 'd2'
    elif what.endswith('_d3'):
        tree_type = 'd3'
    s0 = 3 if tree_type == 'd3' else 1
    seed(s0)
    draw_DTrees(tree_type, what, cropped=cropped)

if __name__ == "__main__":
    # main_PTrees()
    main_DTrees()

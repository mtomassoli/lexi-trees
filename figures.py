from __future__ import annotations
from typing import Tuple
from matplotlib import pyplot as plt

_new_id = 0
_figures: dict[Tuple[float, float, int | None], int] = {}

def set_figure(figsize: Tuple[float, float], dpi: int | None):
    global _new_id
    id = _figures.get((*figsize, dpi))
    if id is None:
        f = plt.figure(_new_id, figsize=figsize, dpi=dpi, clear=True)
        _figures[(*figsize, dpi)] = _new_id
        _new_id += 1
    else:
        f = plt.figure(id, clear=True)      # switches back to figure #id
    return f

def savefig(fpath: str, dpi: int | None = None):
    if dpi is None:
        dpi = plt.gcf().dpi
    plt.savefig(fpath, dpi=dpi)

def showfig():
    f = plt.gcf()
    size = f.get_size_inches()
    dpi = f.dpi
    plt.show()
    plt.close()         # in case it's still open
    del _figures[(*size, dpi)]

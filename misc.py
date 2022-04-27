from __future__ import annotations
from enum import Enum
from typing import Final

# NOTE: `None` would be ambiguous.
class _Missing(Enum):
    missing = 0
class NotFound(Enum):
    not_found = 0
_missing: Final = _Missing.missing
notFound: Final = NotFound.not_found

def default(x, default):
    return x if x is not None else default

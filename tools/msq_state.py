from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from typing import List, Optional, Tuple

DEFAULT_N_BINS = 384


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s.strip())


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MSQState:
    size: int
    target_sum: int
    ruleset_id: str
    tiles: List[Optional[int]]  # row-major, None for blank
    locks: List[bool]  # same length as tiles

    def __post_init__(self):
        n = self.size * self.size
        if len(self.tiles) != n:
            raise ValueError(f"tiles must have length {n}")
        if len(self.locks) != n:
            raise ValueError(f"locks must have length {n}")


def canonical_string(state: MSQState, version: str = "v1") -> str:
    # MSQ|v1|N=3|T=15|R=RS-MSQ-0001|G=8,1,6,3,5,7,4,9,2|L=000000000
    g = []
    for t in state.tiles:
        g.append("_" if t is None else str(int(t)))
    l = "".join("1" if b else "0" for b in state.locks)
    return _norm(
        f"MSQ|{version}|N={state.size}|T={state.target_sum}|R={state.ruleset_id}|G={','.join(g)}|L={l}"
    )


def state_id_and_bin(state: MSQState, n_bins: int = DEFAULT_N_BINS) -> Tuple[str, int]:
    canon = canonical_string(state)
    hid = sha256_hex(canon)
    b = int(hid, 16) % n_bins
    return hid, b

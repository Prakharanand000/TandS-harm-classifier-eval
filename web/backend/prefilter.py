"""A tiny, dependency-free Bloom filter used as a tier-0 pre-filter.

In a real moderation pipeline the cheap check runs *before* the expensive model:
is this text in a denylist of known-bad terms? A Bloom filter answers "definitely
not present" or "possibly present" in O(k) hashes with tiny, fixed memory, so the
heavy classifier is only invoked when the cheap filter cannot rule the text out.
That is the genuine place a Bloom filter belongs in this system — a cost-tiered
front door, not architecture theater. False positives are possible (by design);
false negatives are not, which is the property a safety pre-filter wants.
"""
from __future__ import annotations

import hashlib
import math


class BloomFilter:
    def __init__(self, capacity: int = 1000, error_rate: float = 0.01):
        self.size = max(8, int(-capacity * math.log(error_rate) / (math.log(2) ** 2)))
        self.k = max(1, round(self.size / capacity * math.log(2)))
        self.bits = bytearray((self.size + 7) // 8)
        self.count = 0

    def _positions(self, item: str):
        h = hashlib.sha256(item.encode("utf-8")).digest()
        a = int.from_bytes(h[:8], "big")
        b = int.from_bytes(h[8:16], "big")
        for i in range(self.k):
            yield (a + i * b) % self.size

    def add(self, item: str) -> None:
        for p in self._positions(item):
            self.bits[p // 8] |= (1 << (p % 8))
        self.count += 1

    def __contains__(self, item: str) -> bool:
        return all(self.bits[p // 8] & (1 << (p % 8)) for p in self._positions(item))


# Mild proxy denylist (non-slur). In production this would be a large, governed
# term list loaded from storage; here it just demonstrates the tier-0 mechanism.
DENYLIST = {"idiot", "moron", "loser", "trash", "stupid", "pathetic",
            "worthless", "dumb", "scum", "filth", "clueless", "brainless"}

_bf = BloomFilter(capacity=1000, error_rate=0.01)
for _w in DENYLIST:
    _bf.add(_w)


def prefilter(text: str) -> dict:
    """Tier-0 check: does any token hit the Bloom denylist?"""
    toks = [t.strip(".,!?\"'").lower() for t in text.split()]
    hits = [t for t in toks if t and t in _bf]
    return {
        "tier0_hit": bool(hits),
        "matched": hits[:5],
        "bloom_bits": _bf.size,
        "bloom_hashes": _bf.k,
        "denylist_size": _bf.count,
        "note": ("Possible known-bad term(s) found; in production this routes "
                 "straight to review without spending a model call."
                 if hits else "No known-bad term; would fall through to the model."),
    }

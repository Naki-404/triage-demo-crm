"""Seed bands for the simulator. The bands are disjoint, so a row's seed says which split it may ever belong to.

train      1 000 000 – 1 899 999   training rows, few-shot material, background traffic
dev        1 900 000 – 1 999 999   model selection (same scenarios, new seeds)
test       2 000 000 – 2 799 999   the frozen 285 (main / invariance / contrast)
injection  2 800 000 – 2 899 999   injection rows of the test set

A scenario that needs more than one random stream derives the extra seeds with `derive_seed`, which keeps them
inside the band of the parent seed; `seed + 1` would walk into the next band at the boundary.
"""
from __future__ import annotations

import hashlib

BANDS: dict[str, tuple[int, int]] = {
    "train": (1_000_000, 1_899_999),
    "dev": (1_900_000, 1_999_999),
    "test": (2_000_000, 2_799_999),
    "injection": (2_800_000, 2_899_999),
}

TRAIN_SEED_MIN, TRAIN_SEED_MAX = BANDS["train"]
DEV_SEED_MIN, DEV_SEED_MAX = BANDS["dev"]
TEST_SEED_MIN, TEST_SEED_MAX = BANDS["test"]
INJECTION_SEED_MIN, INJECTION_SEED_MAX = BANDS["injection"]


def clamp_seed(seed: int, *, band: str) -> int:
    """Map an arbitrary seed into the band without colliding with the other bands."""
    low, high = BANDS.get(band, BANDS["test"])
    return low + (seed % (high - low + 1))


def band_of(seed: int) -> str | None:
    for name, (low, high) in BANDS.items():
        if low <= seed <= high:
            return name
    return None


def derive_seed(seed: int, scenario: str, attempt: int = 0) -> int:
    """A deterministic child seed in the same band as `seed` (for a second RNG stream or a retry)."""
    band = band_of(seed)
    if band is None:
        raise ValueError(f"seed {seed} is outside every band")
    digest = hashlib.sha256(f"{seed}:{scenario}:{attempt}".encode()).digest()
    return clamp_seed(int.from_bytes(digest[:8], "big"), band=band)

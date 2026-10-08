"""Standalone Kazakhstan IIN helpers for the load simulator (no app imports)."""
from __future__ import annotations

import random

W1 = list(range(1, 12))
W2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]


def check_digit(first11: str) -> int | None:
    digits = [int(c) for c in first11]
    total = sum(d * w for d, w in zip(digits, W1, strict=True)) % 11
    if total == 10:
        total = sum(d * w for d, w in zip(digits, W2, strict=True)) % 11
        if total == 10:
            return None
    return total


def needs_second_weights(first11: str) -> bool:
    digits = [int(c) for c in first11]
    return sum(d * w for d, w in zip(digits, W1, strict=True)) % 11 == 10


def _random_prefix(rng: random.Random) -> str:
    year = rng.randint(60, 99)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    century_sex = rng.choice([3, 4])
    serial = rng.randint(0, 9999)
    return f"{year:02d}{month:02d}{day:02d}{century_sex}{serial:04d}"


def generate_iin(rng: random.Random | None = None, *, second_weights: bool | None = None) -> str:
    rng = rng or random.Random()
    while True:
        prefix = _random_prefix(rng)
        if second_weights is not None and needs_second_weights(prefix) != second_weights:
            continue
        digit = check_digit(prefix)
        if digit is not None:
            return prefix + str(digit)


def with_wrong_check_digit(iin: str) -> str:
    return iin[:11] + str((int(iin[11]) + 1) % 10)


def rng_from_seed(seed: int) -> random.Random:
    return random.Random(seed)

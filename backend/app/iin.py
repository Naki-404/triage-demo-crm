"""Kazakhstan IIN (12 digits): birth date in positions 1–6 and a check digit.

The national algorithm uses weight set W1; when the weighted sum mod 11 equals 10,
the check digit is recomputed with weight set W2. If that also yields 10, no valid
check digit exists for the prefix.
"""
from __future__ import annotations

import random
import re

from . import faults

W1 = list(range(1, 12))
W2 = [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2]


class InvalidIINError(ValueError):
    pass


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


def _check_digit_first_weights_only(first11: str) -> int | None:
    """Legacy path used by one stand switch: no recomputation with W2."""
    digits = [int(c) for c in first11]
    total = sum(d * w for d, w in zip(digits, W1, strict=True)) % 11
    if total == 10:
        return None
    return total


def validate_iin(iin: str) -> None:
    if not re.fullmatch(r"\d{12}", iin or ""):
        raise InvalidIINError("IIN must contain 12 digits")
    month, day = int(iin[2:4]), int(iin[4:6])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        raise InvalidIINError("IIN contains an invalid birth date")
    prefix = iin[:11]
    expected = _check_digit_first_weights_only(prefix) if faults.iin_skips_second_weights() else check_digit(prefix)
    if expected is None or expected != int(iin[11]):
        raise InvalidIINError("Некорректный ИИН: checksum does not match")


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

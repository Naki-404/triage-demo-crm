"""IIN helpers — reuse CRM backend implementation when available."""
from __future__ import annotations

import random
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.iin import generate_iin, needs_second_weights, with_wrong_check_digit  # noqa: E402

__all__ = ["generate_iin", "needs_second_weights", "with_wrong_check_digit", "rng_from_seed"]


def rng_from_seed(seed: int) -> random.Random:
    return random.Random(seed)

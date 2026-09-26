"""Seed ranges for train vs test — keep disjoint to avoid leakage into phase 3–5."""

# Train / few-shot / background generators
TRAIN_SEED_MIN = 1_000_000
TRAIN_SEED_MAX = 1_999_999

# Test / main evaluation / invariance / contrast (held out)
TEST_SEED_MIN = 2_000_000
TEST_SEED_MAX = 2_999_999

# Injection scenarios use a dedicated band inside test
INJECTION_SEED_MIN = 2_800_000
INJECTION_SEED_MAX = 2_899_999


def clamp_seed(seed: int, *, band: str) -> int:
    """Map an arbitrary seed into the band without colliding train↔test."""
    if band == "train":
        span = TRAIN_SEED_MAX - TRAIN_SEED_MIN + 1
        return TRAIN_SEED_MIN + (seed % span)
    if band == "injection":
        span = INJECTION_SEED_MAX - INJECTION_SEED_MIN + 1
        return INJECTION_SEED_MIN + (seed % span)
    span = TEST_SEED_MAX - TEST_SEED_MIN + 1
    return TEST_SEED_MIN + (seed % span)

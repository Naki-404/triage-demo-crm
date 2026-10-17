from itertools import pairwise

from simulator.seeds import BANDS, band_of, clamp_seed, derive_seed


def test_bands_are_disjoint_and_ordered():
    spans = sorted(BANDS.values())
    for (_, high), (low, _) in pairwise(spans):
        assert high < low


def test_clamp_lands_in_band_for_every_band():
    for name, (low, high) in BANDS.items():
        for raw in (0, 1, 999_999, 2_000_001, 10**12):
            seed = clamp_seed(raw, band=name)
            assert low <= seed <= high and band_of(seed) == name


def test_clamp_never_collides_across_bands():
    for raw in range(0, 5000, 7):
        seeds = {name: clamp_seed(raw, band=name) for name in BANDS}
        assert len(set(seeds.values())) == len(BANDS)


def test_derive_seed_is_deterministic_and_stays_in_band():
    parent = clamp_seed(42, band="train")
    a = derive_seed(parent, "background_manager", 0)
    assert a == derive_seed(parent, "background_manager", 0)
    assert a != derive_seed(parent, "background_manager", 1)
    assert a != derive_seed(parent, "wrong_password", 0)
    assert band_of(a) == "train"
    test_parent = clamp_seed(42, band="test")
    assert band_of(derive_seed(test_parent, "x", 3)) == "test"


def test_derive_rejects_seed_outside_bands():
    try:
        derive_seed(5, "x")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass

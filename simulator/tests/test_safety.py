from simulator.safety import TargetNotAllowedError, assert_target_allowed, host_allowed
from simulator.seeds import TRAIN_SEED_MAX, TRAIN_SEED_MIN, clamp_seed


def test_host_whitelist():
    assert host_allowed("localhost")
    assert host_allowed("127.0.0.1")
    assert host_allowed("crm.csip.dev")
    assert host_allowed("demo.local")
    assert not host_allowed("evil.example.com")


def test_assert_blocks_remote_without_flag():
    try:
        assert_target_allowed("https://evil.example.com", i_own_this_target=False)
        assert False, "expected TargetNotAllowedError"
    except TargetNotAllowedError:
        pass


def test_assert_allows_with_ownership_flag():
    assert_target_allowed("https://evil.example.com", i_own_this_target=True)


def test_seed_bands_disjoint():
    assert clamp_seed(0, band="train") >= TRAIN_SEED_MIN
    assert clamp_seed(0, band="train") <= TRAIN_SEED_MAX
    t = clamp_seed(0, band="test")
    assert t >= 2_000_000
    assert clamp_seed(99, band="train") != clamp_seed(99, band="test") or TRAIN_SEED_MAX < 2_000_000

import pytest
from agent_canary import CanaryRouter, Decision


def test_zero_percent_always_stable():
    r = CanaryRouter(canary_percent=0.0)
    for i in range(100):
        assert r.decide(sticky_key=f"user-{i}") == Decision.STABLE


def test_full_percent_always_canary():
    r = CanaryRouter(canary_percent=1.0)
    for i in range(100):
        assert r.decide(sticky_key=f"user-{i}") == Decision.CANARY


def test_sticky_routing_is_stable():
    r = CanaryRouter(canary_percent=0.5)
    decisions = [r.decide(sticky_key="user-42") for _ in range(20)]
    assert len(set(decisions)) == 1  # Always the same


def test_invalid_percent_rejected():
    with pytest.raises(ValueError):
        CanaryRouter(canary_percent=-0.1)
    with pytest.raises(ValueError):
        CanaryRouter(canary_percent=1.5)


def test_update_percent():
    r = CanaryRouter(canary_percent=0.0)
    r.update_percent(0.5)
    assert r.canary_percent == 0.5
    with pytest.raises(ValueError):
        r.update_percent(2.0)


def test_distribution_roughly_correct():
    """At 25%, ~25% of distinct sticky keys should land in canary (large sample)."""
    r = CanaryRouter(canary_percent=0.25)
    canary_count = sum(
        1 for i in range(2000)
        if r.decide(sticky_key=f"user-{i}") == Decision.CANARY
    )
    # Allow generous tolerance due to MD5 hashing
    assert 400 <= canary_count <= 600

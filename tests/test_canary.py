import pytest
from agent_canary import AgentCanary, AutoAction, Rollout, Stage


def _make(canary_pct=0.0, min_dur=0, min_samp=10):
    rollout = Rollout(stages=[
        Stage(canary_pct, min_duration_seconds=min_dur, min_samples=min_samp, success_threshold=0.99),
        Stage(1.0, min_duration_seconds=0, min_samples=0),
    ])
    return AgentCanary(
        stable_version="v1.0.0",
        canary_version="v1.1.0",
        rollout=rollout,
    )


def test_routes_to_stable_when_zero_percent():
    ac = _make(canary_pct=0.0)
    versions = {ac.route(sticky_key=f"u-{i}") for i in range(50)}
    assert versions == {"v1.0.0"}


def test_records_per_version_metrics():
    ac = _make(canary_pct=0.0)
    ac.record("v1.0.0", success=True, latency_ms=10)
    ac.record("v1.1.0", success=False, latency_ms=200)
    assert ac.metrics("v1.0.0").total == 1
    assert ac.metrics("v1.1.0").total == 1
    assert ac.metrics("v1.0.0").success_rate == 1.0
    assert ac.metrics("v1.1.0").success_rate == 0.0


def test_unknown_version_rejected():
    ac = _make()
    with pytest.raises(ValueError):
        ac.record("v9.9.9", success=True, latency_ms=10)


def test_auto_decide_promotes_when_healthy():
    ac = _make(canary_pct=0.1, min_dur=0, min_samp=10)
    # Simulate healthy canary traffic
    for _ in range(100):
        ac.record("v1.1.0", success=True, latency_ms=10)
    for _ in range(100):
        ac.record("v1.0.0", success=True, latency_ms=10)
    assert ac.auto_decide() == AutoAction.PROMOTE


def test_auto_decide_rolls_back_when_unhealthy():
    ac = _make(canary_pct=0.1, min_dur=0, min_samp=10)
    # Stable is healthy
    for _ in range(100):
        ac.record("v1.0.0", success=True, latency_ms=10)
    # Canary is much worse than stable
    for _ in range(60):
        ac.record("v1.1.0", success=False, latency_ms=10)
    for _ in range(40):
        ac.record("v1.1.0", success=True, latency_ms=10)
    # 40% canary success vs 100% stable - far below safety margin
    assert ac.auto_decide() == AutoAction.ROLLBACK


def test_apply_promote_advances_router():
    ac = _make(canary_pct=0.1, min_dur=0, min_samp=10)
    for _ in range(100):
        ac.record("v1.1.0", success=True, latency_ms=10)
    for _ in range(100):
        ac.record("v1.0.0", success=True, latency_ms=10)
    ac.apply(AutoAction.PROMOTE)
    assert ac.rollout.current_percent == 1.0


def test_apply_rollback_zeros_canary():
    ac = _make(canary_pct=0.5)
    ac.apply(AutoAction.ROLLBACK)
    # All routing should now go stable
    versions = {ac.route(sticky_key=f"u-{i}") for i in range(50)}
    assert versions == {"v1.0.0"}


def test_status_returns_full_snapshot():
    ac = _make()
    ac.record("v1.0.0", success=True, latency_ms=10)
    s = ac.status()
    assert s["stable_version"] == "v1.0.0"
    assert s["canary_version"] == "v1.1.0"
    assert "stable_metrics" in s
    assert "canary_metrics" in s


def test_same_version_rejected():
    rollout = Rollout(stages=[Stage(0.5), Stage(1.0)])
    with pytest.raises(ValueError):
        AgentCanary(stable_version="v1", canary_version="v1", rollout=rollout)

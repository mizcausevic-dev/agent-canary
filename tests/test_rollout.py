import time
import pytest
from agent_canary import Rollout, Stage, VersionMetrics


def _populate(metrics: VersionMetrics, total: int, success_rate: float = 1.0) -> None:
    successes = int(total * success_rate)
    failures = total - successes
    for _ in range(successes):
        metrics.record(success=True, latency_ms=10)
    for _ in range(failures):
        metrics.record(success=False, latency_ms=10)


def test_standard_progression():
    r = Rollout.standard()
    assert r.current_percent == 0.01
    assert len(r.stages) == 5
    assert r.stages[-1].percent == 1.0


def test_promote_advances_stage():
    r = Rollout(stages=[Stage(0.1), Stage(0.5), Stage(1.0)])
    assert r.current_percent == 0.1
    r.promote()
    assert r.current_percent == 0.5
    r.promote()
    assert r.current_percent == 1.0
    # Cannot promote beyond final stage
    assert r.promote() is False


def test_rollback_resets():
    r = Rollout(stages=[Stage(0.1), Stage(0.5), Stage(1.0)])
    r.promote()
    r.promote()
    r.rollback()
    assert r.current_stage_idx == 0
    assert r.current_percent == 0.1


def test_can_promote_blocked_by_duration():
    r = Rollout(stages=[Stage(0.1, min_duration_seconds=60, min_samples=10), Stage(1.0)])
    m = VersionMetrics()
    _populate(m, 100, success_rate=1.0)
    assert r.can_promote(m) is False  # Just started, hasn't soaked


def test_can_promote_blocked_by_min_samples():
    r = Rollout(stages=[Stage(0.1, min_duration_seconds=0, min_samples=100), Stage(1.0)])
    m = VersionMetrics()
    _populate(m, 5, success_rate=1.0)
    assert r.can_promote(m) is False


def test_can_promote_blocked_by_success_rate():
    r = Rollout(stages=[
        Stage(0.1, min_duration_seconds=0, min_samples=10, success_threshold=0.99),
        Stage(1.0),
    ])
    m = VersionMetrics()
    _populate(m, 100, success_rate=0.85)
    assert r.can_promote(m) is False


def test_can_promote_blocked_by_p95():
    r = Rollout(stages=[
        Stage(0.1, min_duration_seconds=0, min_samples=10, max_p95_ms=100),
        Stage(1.0),
    ])
    m = VersionMetrics()
    for _ in range(100):
        m.record(success=True, latency_ms=500)
    assert r.can_promote(m) is False


def test_can_promote_when_all_gates_pass():
    r = Rollout(stages=[
        Stage(0.1, min_duration_seconds=0, min_samples=10, success_threshold=0.99, max_p95_ms=100),
        Stage(1.0),
    ])
    m = VersionMetrics()
    _populate(m, 100, success_rate=1.0)
    assert r.can_promote(m) is True


def test_invalid_stages_rejected():
    with pytest.raises(ValueError):
        Rollout(stages=[])
    with pytest.raises(ValueError):
        Rollout(stages=[Stage(0.5), Stage(0.1)])  # Decreasing percent

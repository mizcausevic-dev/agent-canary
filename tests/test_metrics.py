import pytest
from agent_canary import VersionMetrics


def test_empty_metrics_defaults():
    m = VersionMetrics()
    assert m.total == 0
    assert m.success_rate == 1.0
    assert m.p95_ms == 0.0


def test_records_success_and_failure():
    m = VersionMetrics()
    m.record(success=True, latency_ms=100)
    m.record(success=True, latency_ms=200)
    m.record(success=False, latency_ms=500)
    assert m.total == 3
    assert m.successes == 2
    assert m.failures == 1
    assert abs(m.success_rate - 2/3) < 1e-9


def test_percentiles():
    m = VersionMetrics()
    for i in range(100):
        m.record(success=True, latency_ms=i)
    assert 49 <= m.p50_ms <= 51
    assert 94 <= m.p95_ms <= 96
    assert 98 <= m.p99_ms <= 100


def test_invalid_percentile():
    m = VersionMetrics()
    with pytest.raises(ValueError):
        m.percentile(2.0)
    with pytest.raises(ValueError):
        m.percentile(-0.1)


def test_window_size_caps_latencies():
    m = VersionMetrics(window_size=10)
    for i in range(50):
        m.record(success=True, latency_ms=i)
    # Counters track all events; latency window drops old data
    assert m.total == 50
    # Last 10 values are 40..49, so p50 should be in that range
    assert 40 <= m.p50_ms <= 50


def test_snapshot():
    m = VersionMetrics()
    m.record(success=True, latency_ms=100)
    snap = m.snapshot()
    assert snap["total"] == 1
    assert snap["success_rate"] == 1.0
    assert "p95_ms" in snap

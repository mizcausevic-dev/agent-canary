"""Per-version metrics: success rate, latency percentiles."""
from __future__ import annotations
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class VersionMetrics:
    """Thread-safe rolling-window metrics for a single agent/model version."""
    window_size: int = 1000
    successes: int = 0
    failures: int = 0
    _latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=1000), init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        # Re-initialize deque with correct maxlen from window_size
        self._latencies = deque(maxlen=self.window_size)

    def record(self, success: bool, latency_ms: float) -> None:
        with self._lock:
            if success:
                self.successes += 1
            else:
                self.failures += 1
            self._latencies.append(float(latency_ms))

    @property
    def total(self) -> int:
        with self._lock:
            return self.successes + self.failures

    @property
    def success_rate(self) -> float:
        with self._lock:
            total = self.successes + self.failures
            if total == 0:
                return 1.0
            return self.successes / total

    def percentile(self, p: float) -> float:
        """Return the latency percentile (p in [0, 1])."""
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p must be in [0.0, 1.0], got {p}")
        with self._lock:
            if not self._latencies:
                return 0.0
            sorted_l = sorted(self._latencies)
            idx = int(len(sorted_l) * p)
            return sorted_l[min(idx, len(sorted_l) - 1)]

    @property
    def p50_ms(self) -> float:
        return self.percentile(0.50)

    @property
    def p95_ms(self) -> float:
        return self.percentile(0.95)

    @property
    def p99_ms(self) -> float:
        return self.percentile(0.99)

    def snapshot(self) -> dict:
        with self._lock:
            total = self.successes + self.failures
            success_rate = self.successes / total if total > 0 else 1.0
        return {
            "successes": self.successes,
            "failures": self.failures,
            "total": total,
            "success_rate": success_rate,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
        }

"""Staged rollout state machine: 1% -> 5% -> 25% -> 50% -> 100%."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .metrics import VersionMetrics


@dataclass
class Stage:
    """A single rollout stage with promotion criteria."""
    percent: float
    min_duration_seconds: float = 300.0  # 5 min default soak
    min_samples: int = 100
    success_threshold: float = 0.99  # 99% success required to promote
    max_p95_ms: Optional[float] = None  # None = no latency gate

    def __post_init__(self) -> None:
        if not 0.0 <= self.percent <= 1.0:
            raise ValueError(f"Stage.percent must be in [0.0, 1.0], got {self.percent}")
        if not 0.0 <= self.success_threshold <= 1.0:
            raise ValueError(f"success_threshold must be in [0.0, 1.0]")


@dataclass
class Rollout:
    """
    Stage-based rollout. Default progression: 1% -> 5% -> 25% -> 50% -> 100%.
    Promotion is driven by min duration + min samples + success rate + p95 latency.
    """
    stages: List[Stage]
    current_stage_idx: int = 0
    started_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.stages:
            raise ValueError("Rollout requires at least one stage")
        # Stages must monotonically increase in percent
        prev = -1.0
        for s in self.stages:
            if s.percent < prev:
                raise ValueError(f"Stages must be non-decreasing in percent, got {s.percent} after {prev}")
            prev = s.percent

    @classmethod
    def standard(cls) -> "Rollout":
        """A reasonable default progression."""
        return cls(stages=[
            Stage(percent=0.01, min_duration_seconds=300, min_samples=50,  success_threshold=0.99),
            Stage(percent=0.05, min_duration_seconds=600, min_samples=200, success_threshold=0.99),
            Stage(percent=0.25, min_duration_seconds=900, min_samples=500, success_threshold=0.99),
            Stage(percent=0.50, min_duration_seconds=1200, min_samples=1000, success_threshold=0.99),
            Stage(percent=1.00, min_duration_seconds=0,    min_samples=0,    success_threshold=0.99),
        ])

    @property
    def current_stage(self) -> Stage:
        return self.stages[self.current_stage_idx]

    @property
    def current_percent(self) -> float:
        return self.current_stage.percent

    @property
    def is_complete(self) -> bool:
        return self.current_stage_idx >= len(self.stages) - 1 and self.current_percent >= 1.0

    def time_in_stage(self) -> float:
        return time.time() - self.started_at

    def can_promote(self, canary_metrics: VersionMetrics) -> bool:
        stage = self.current_stage
        if self.is_complete:
            return False
        if self.time_in_stage() < stage.min_duration_seconds:
            return False
        if canary_metrics.total < stage.min_samples:
            return False
        if canary_metrics.success_rate < stage.success_threshold:
            return False
        if stage.max_p95_ms is not None and canary_metrics.p95_ms > stage.max_p95_ms:
            return False
        return True

    def promote(self) -> bool:
        if self.current_stage_idx < len(self.stages) - 1:
            self.current_stage_idx += 1
            self.started_at = time.time()
            return True
        return False

    def rollback(self) -> None:
        """Reset to stage 0 (effectively kills the canary)."""
        self.current_stage_idx = 0
        self.started_at = time.time()

"""AgentCanary: facade tying decision + rollout + metrics together."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from .decision import CanaryRouter, Decision
from .metrics import VersionMetrics
from .rollout import Rollout


class AutoAction(str, Enum):
    PROMOTE = "promote"
    ROLLBACK = "rollback"
    HOLD = "hold"


@dataclass
class AgentCanary:
    """
    Tracks two versions, routes traffic by stage percent, records per-version
    metrics, and recommends promote/rollback/hold decisions.
    """
    stable_version: str
    canary_version: str
    rollout: Rollout
    rollback_safety_margin: float = 0.05  # canary tolerated to be 5pp worse before rollback
    rollback_min_samples: int = 50

    _router: CanaryRouter = field(init=False)
    _metrics: Dict[str, VersionMetrics] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.stable_version == self.canary_version:
            raise ValueError("stable and canary versions must differ")
        self._router = CanaryRouter(canary_percent=self.rollout.current_percent)
        self._metrics = {
            self.stable_version: VersionMetrics(),
            self.canary_version: VersionMetrics(),
        }

    def route(self, sticky_key: Optional[str] = None) -> str:
        """Return the version string to dispatch this request to."""
        decision = self._router.decide(sticky_key=sticky_key)
        return self.canary_version if decision == Decision.CANARY else self.stable_version

    def record(self, version: str, success: bool, latency_ms: float) -> None:
        if version not in self._metrics:
            raise ValueError(f"Unknown version: {version}")
        self._metrics[version].record(success=success, latency_ms=latency_ms)

    def metrics(self, version: str) -> VersionMetrics:
        if version not in self._metrics:
            raise ValueError(f"Unknown version: {version}")
        return self._metrics[version]

    def auto_decide(self) -> AutoAction:
        """Recommend promote / rollback / hold based on current metrics."""
        canary = self._metrics[self.canary_version]
        stable = self._metrics[self.stable_version]

        # Rollback gate: canary materially worse than stable on success rate
        if canary.total >= self.rollback_min_samples and stable.total > 0:
            if canary.success_rate < stable.success_rate - self.rollback_safety_margin:
                return AutoAction.ROLLBACK

        # Promotion gate: rollout-defined criteria met
        if self.rollout.can_promote(canary):
            return AutoAction.PROMOTE

        return AutoAction.HOLD

    def apply(self, action: AutoAction) -> None:
        """Execute the recommended action."""
        if action == AutoAction.PROMOTE:
            self.rollout.promote()
            self._router.update_percent(self.rollout.current_percent)
            # Reset canary metrics for the new stage's evaluation window
            self._metrics[self.canary_version] = VersionMetrics()
        elif action == AutoAction.ROLLBACK:
            self.rollout.rollback()
            self._router.update_percent(0.0)
        # HOLD is a no-op

    def status(self) -> dict:
        return {
            "stable_version": self.stable_version,
            "canary_version": self.canary_version,
            "current_percent": self.rollout.current_percent,
            "stage_idx": self.rollout.current_stage_idx,
            "stages_total": len(self.rollout.stages),
            "is_complete": self.rollout.is_complete,
            "time_in_stage_s": self.rollout.time_in_stage(),
            "stable_metrics": self._metrics[self.stable_version].snapshot(),
            "canary_metrics": self._metrics[self.canary_version].snapshot(),
        }

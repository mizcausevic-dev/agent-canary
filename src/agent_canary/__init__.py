"""agent-canary: progressive rollout, shadow mode, and auto-rollback for AI agents."""
from .decision import Decision, CanaryRouter
from .metrics import VersionMetrics
from .rollout import Stage, Rollout
from .shadow import ShadowDeployment
from .canary import AgentCanary, AutoAction

__version__ = "0.1.0"
__all__ = [
    "Decision", "CanaryRouter", "VersionMetrics",
    "Stage", "Rollout", "ShadowDeployment",
    "AgentCanary", "AutoAction",
]

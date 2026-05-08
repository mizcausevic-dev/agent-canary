"""Routing decision: stable vs canary, with sticky-key consistent hashing."""
from __future__ import annotations
import hashlib
import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Decision(str, Enum):
    STABLE = "stable"
    CANARY = "canary"


@dataclass
class CanaryRouter:
    """
    Decides whether a request goes to stable or canary.

    canary_percent in [0.0, 1.0]. With a sticky_key, routing is deterministic
    per user/session - a user assigned to canary STAYS on canary even as the
    percent grows. This eliminates the worst class of canary bugs: flapping.
    """
    canary_percent: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.canary_percent <= 1.0:
            raise ValueError(f"canary_percent must be in [0.0, 1.0], got {self.canary_percent}")

    def decide(self, sticky_key: Optional[str] = None) -> Decision:
        if sticky_key is not None:
            bucket = self._bucket(sticky_key)
            return Decision.CANARY if bucket < self.canary_percent else Decision.STABLE
        return Decision.CANARY if random.random() < self.canary_percent else Decision.STABLE

    @staticmethod
    def _bucket(key: str) -> float:
        """Map any string to a stable [0.0, 1.0) bucket via MD5."""
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) / 0x100000000

    def update_percent(self, percent: float) -> None:
        if not 0.0 <= percent <= 1.0:
            raise ValueError(f"percent must be in [0.0, 1.0], got {percent}")
        self.canary_percent = percent

"""Shadow deployment: mirror traffic to a candidate version at zero user impact."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ShadowDeployment:
    """
    Calls stable_fn synchronously and returns its result to the caller.
    Fires shadow_fn in a background thread - errors are swallowed, latency
    of shadow calls does NOT block the user response.

    Optionally compares results via `comparator(stable_result, shadow_result)`.
    """
    stable_fn: Callable[..., Any]
    shadow_fn: Callable[..., Any]
    comparator: Optional[Callable[[Any, Any], None]] = None
    max_workers: int = 4
    _executor: Optional[ThreadPoolExecutor] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def call(self, *args: Any, **kwargs: Any) -> Any:
        stable_result = self.stable_fn(*args, **kwargs)
        assert self._executor is not None
        self._executor.submit(self._run_shadow, stable_result, args, kwargs)
        return stable_result

    def _run_shadow(self, stable_result: Any, args: tuple, kwargs: dict) -> None:
        try:
            shadow_result = self.shadow_fn(*args, **kwargs)
            if self.comparator is not None:
                try:
                    self.comparator(stable_result, shadow_result)
                except Exception:
                    pass  # Comparator errors must never affect production
        except Exception:
            pass  # Shadow exec errors must never affect production

    def shutdown(self, wait: bool = True) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None

import time
import threading
from agent_canary import ShadowDeployment


def test_returns_stable_result():
    sd = ShadowDeployment(
        stable_fn=lambda x: f"stable:{x}",
        shadow_fn=lambda x: f"shadow:{x}",
    )
    try:
        assert sd.call("hello") == "stable:hello"
    finally:
        sd.shutdown()


def test_shadow_runs_in_background():
    shadow_called = threading.Event()

    def shadow_fn(x):
        shadow_called.set()
        return x

    sd = ShadowDeployment(
        stable_fn=lambda x: x,
        shadow_fn=shadow_fn,
    )
    try:
        sd.call(42)
        assert shadow_called.wait(timeout=2.0)
    finally:
        sd.shutdown()


def test_shadow_errors_are_swallowed():
    def boom(x):
        raise RuntimeError("shadow exploded")

    sd = ShadowDeployment(
        stable_fn=lambda x: f"ok:{x}",
        shadow_fn=boom,
    )
    try:
        # Stable still returns; shadow error MUST not propagate
        assert sd.call(1) == "ok:1"
        time.sleep(0.05)  # Let the shadow attempt run
    finally:
        sd.shutdown()


def test_comparator_invoked():
    seen = []

    def comparator(stable, shadow):
        seen.append((stable, shadow))

    sd = ShadowDeployment(
        stable_fn=lambda x: f"stable:{x}",
        shadow_fn=lambda x: f"shadow:{x}",
        comparator=comparator,
    )
    try:
        sd.call(7)
        time.sleep(0.1)
        assert seen == [("stable:7", "shadow:7")]
    finally:
        sd.shutdown()


def test_comparator_errors_swallowed():
    def bad_comparator(stable, shadow):
        raise ValueError("comparator broken")

    sd = ShadowDeployment(
        stable_fn=lambda x: x,
        shadow_fn=lambda x: x,
        comparator=bad_comparator,
    )
    try:
        # Should still return cleanly
        assert sd.call(99) == 99
        time.sleep(0.05)
    finally:
        sd.shutdown()

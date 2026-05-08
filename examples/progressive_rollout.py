"""End-to-end example: progressive rollout from 1% to 100% with auto-decisions."""
import random
import time

from agent_canary import AgentCanary, AutoAction, Rollout, Stage


def stable_agent(prompt: str) -> str:
    """Simulated stable v1.0.0 - 99% success, ~50ms latency."""
    if random.random() < 0.01:
        raise RuntimeError("rare stable failure")
    return f"v1.0.0 response: {prompt[:30]}"


def canary_agent(prompt: str) -> str:
    """Simulated canary v1.1.0 - 99.5% success, ~40ms latency (slight win)."""
    if random.random() < 0.005:
        raise RuntimeError("rare canary failure")
    return f"v1.1.0 response: {prompt[:30]}"


def call_with_metrics(canary: AgentCanary, version: str, prompt: str) -> str:
    fn = canary_agent if version == "v1.1.0" else stable_agent
    start = time.perf_counter()
    success = True
    try:
        result = fn(prompt)
    except Exception:
        success = False
        result = "ERROR"
    latency_ms = (time.perf_counter() - start) * 1000
    canary.record(version, success=success, latency_ms=latency_ms)
    return result


def main() -> None:
    # Aggressive rollout for demo - in prod these durations would be 5-30+ minutes
    rollout = Rollout(stages=[
        Stage(percent=0.01, min_duration_seconds=0, min_samples=20, success_threshold=0.95),
        Stage(percent=0.10, min_duration_seconds=0, min_samples=20, success_threshold=0.95),
        Stage(percent=0.50, min_duration_seconds=0, min_samples=20, success_threshold=0.95),
        Stage(percent=1.00, min_duration_seconds=0, min_samples=0,  success_threshold=0.95),
    ])

    canary = AgentCanary(
        stable_version="v1.0.0",
        canary_version="v1.1.0",
        rollout=rollout,
    )

    print(f"Starting at {canary.rollout.current_percent*100:.0f}% canary")

    # Simulate ~500 requests across the rollout
    for i in range(500):
        version = canary.route(sticky_key=f"user-{i % 200}")
        call_with_metrics(canary, version, f"prompt #{i}")

        # Every 50 requests, make a promote/hold/rollback decision
        if (i + 1) % 50 == 0:
            action = canary.auto_decide()
            print(f"  After {i+1} requests: action={action.value}, percent={canary.rollout.current_percent*100:.0f}%")
            canary.apply(action)
            if canary.rollout.is_complete:
                print("Rollout COMPLETE - canary is now 100%")
                break

    print("\nFinal status:")
    s = canary.status()
    print(f"  Stage: {s['stage_idx']+1}/{s['stages_total']} @ {s['current_percent']*100:.0f}%")
    print(f"  Stable v1.0.0: {s['stable_metrics']['total']} reqs, "
          f"{s['stable_metrics']['success_rate']*100:.1f}% success")
    print(f"  Canary v1.1.0: {s['canary_metrics']['total']} reqs, "
          f"{s['canary_metrics']['success_rate']*100:.1f}% success")


if __name__ == "__main__":
    main()

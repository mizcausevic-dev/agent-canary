# agent-canary 🚦

> Progressive rollout, shadow mode, and auto-rollback for AI agents.
> Sticky-percent routing with promote/rollback gates driven by real metrics.

[![CI](https://github.com/mizcausevic-dev/agent-canary/actions/workflows/ci.yml/badge.svg)](https://github.com/mizcausevic-dev/agent-canary/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-alpha-orange)

---

## Why

Every team rolling a new agent or model version into production lives in fear
of the same thing: cutting over 100% of traffic and finding out at 3 AM that
something subtle broke. The fix is universally agreed on - **progressive
rollout** - and universally hand-rolled, badly.

**agent-canary ships the staged rollout / shadow / auto-rollback you keep
meaning to build.**

- Sticky % routing: a user assigned to canary STAYS on canary
- Shadow mode: mirror traffic to v1.1 at zero user impact
- Stage gates: 1% -> 5% -> 25% -> 50% -> 100% with success-rate + latency thresholds
- Auto-rollback: canary materially worse than stable? Done. Zero %.

## What

Five primitives, zero runtime dependencies:

| Component | Purpose |
|---|---|
| `CanaryRouter` | Sticky-key % routing via consistent hashing (MD5) |
| `VersionMetrics` | Thread-safe rolling-window success rate + latency percentiles |
| `Stage` / `Rollout` | Staged FSM with min duration / min samples / success / p95 gates |
| `ShadowDeployment` | Mirror calls to a candidate fn in a background thread, swallow shadow errors |
| `AgentCanary` | Facade tying decision + rollout + metrics + auto-decisions |

## Architecture

```
                  +---------------------+
                  |   AgentCanary       |
                  |  (single facade)    |
                  +----------+----------+
                             |
            +----------------+----------------+
            |                |                |
            v                v                v
    +-------------+  +--------------+  +---------------+
    |CanaryRouter |  |  Rollout     |  |VersionMetrics |
    |(sticky %)   |  |  (FSM gates) |  |(per-version)  |
    +------+------+  +------+-------+  +-------+-------+
           |                |                  |
           v                v                  v
    decide(key) ->  can_promote(metrics)?  record(ok, ms)
    "stable" or     PROMOTE / HOLD /       success rate,
    "canary"        ROLLBACK               p50/p95/p99
```

## Install

```bash
pip install agent-canary
```

Or from source:

```bash
git clone https://github.com/mizcausevic-dev/agent-canary
cd agent-canary
pip install -e ".[dev]"
pytest
```

## Quickstart

### Progressive rollout with auto-decisions

```python
from agent_canary import AgentCanary, AutoAction, Rollout

canary = AgentCanary(
    stable_version="agent-v1.0.0",
    canary_version="agent-v1.1.0",
    rollout=Rollout.standard(),  # 1% -> 5% -> 25% -> 50% -> 100%
)

# In your request handler:
def handle(user_id: str, prompt: str):
    version = canary.route(sticky_key=user_id)
    start = time.perf_counter()
    try:
        result = call_agent(version, prompt)
        canary.record(version, success=True,
                     latency_ms=(time.perf_counter()-start)*1000)
        return result
    except Exception:
        canary.record(version, success=False,
                     latency_ms=(time.perf_counter()-start)*1000)
        raise

# In a periodic background task (every minute or so):
def evaluate():
    action = canary.auto_decide()
    if action != AutoAction.HOLD:
        print(f"Applying: {action.value}")
    canary.apply(action)
```

### Shadow mode (zero user impact)

```python
from agent_canary import ShadowDeployment

def diff_compare(stable_result, shadow_result):
    if stable_result != shadow_result:
        log.info("divergence", extra={"stable": stable_result, "shadow": shadow_result})

shadowed = ShadowDeployment(
    stable_fn=stable_agent.invoke,
    shadow_fn=canary_agent.invoke,
    comparator=diff_compare,
)

# Stable result is what user sees. Canary runs in the background.
result = shadowed.call(prompt)
```

### Custom rollout stages

```python
from agent_canary import Rollout, Stage

aggressive = Rollout(stages=[
    Stage(percent=0.05, min_duration_seconds=300,  min_samples=200, success_threshold=0.99),
    Stage(percent=0.50, min_duration_seconds=600,  min_samples=500, success_threshold=0.99, max_p95_ms=400),
    Stage(percent=1.00, min_duration_seconds=0,    min_samples=0,   success_threshold=0.99),
])
```

## Buyer

- **Platform Engineering** - drop-in canary infrastructure for agent fleets
- **SRE** - blast-radius control for model and prompt deployments
- **ML Platform / MLOps** - works for ANY versioned dispatchable: prompt, model, full agent

## Pairs With

- [`agent-router`](https://github.com/mizcausevic-dev/agent-router) - decides WHICH version exists; agent-canary decides WHO sees which
- [`rate-limit-shield`](https://github.com/mizcausevic-dev/rate-limit-shield) - per-version quotas during canary
- [`identity-mesh`](https://github.com/mizcausevic-dev/identity-mesh) - identity-based canary cohorts (e.g. only research-* agents)
- [`agentobserve`](https://github.com/mizcausevic-dev/agentobserve) - emit `canary.status()` snapshots into your observability stack

## Roadmap

- [ ] Persistent state backend (Redis) for multi-pod deployments
- [ ] Cohort-based routing (identity, region, tier)
- [ ] Statistical significance gates (CUPED, sequential testing)
- [ ] Prometheus / OpenTelemetry exporter
- [ ] PyPI release

## Doctrine

> *"Two truths in production: every deploy is a canary you didn't notice,
> and the only safe rollout is one you can roll back."*

Three rules:

1. **Sticky routing.** A user assigned to canary STAYS on canary - flapping is worse than slow rollouts.
2. **Shadow before rollout.** Mirror traffic at zero user impact. Find the breakages before you cut over.
3. **Auto-rollback wins.** Don't trust humans to wake up at 3 AM. Trust the gate.

## License

MIT - see [LICENSE](./LICENSE).

---

Built by [Mirza Causevic](https://github.com/mizcausevic-dev) - Part of the
[mizcausevic-dev](https://github.com/mizcausevic-dev) AI platform engineering portfolio.

# Why We Built This

**agent-canary** started from a recurring operating problem in platform governance. Teams were collecting more data and more system state, but the decision layer around that data was still fragile under pressure. Teams could collect raw signals, but still struggle to answer the harder questions under pressure: what is actually drifting, who owns the next move, and how much business or control risk is building underneath the technical state.

In this case the pressure showed up around policy drift, observability blind spots, latency pressure, and fragmented control evidence. That sounds specific, but the underlying failure mode was familiar. A team would have multiple tools in place, each doing a piece of the job. There might be observability, validation, ticketing, dashboards, static analysis, workflow software, or spreadsheet-based reporting. None of that meant the operating problem was actually solved. What was usually missing was a clear translation layer between system behavior and accountable action.

That was the opening for **agent-canary**. The repo was designed around a simple idea: operators need more than visibility. They need evidence, priorities, and next actions that make sense under pressure. That is why the project is framed as platform governance rather than as a generic app demo. The point is not just to show that data can be rendered or APIs can be wired together. The point is to show what a practical control surface looks like when the audience is platform, security, and reliability teams.

Existing tools missed the mark for understandable reasons. The available tooling landscape - monitoring, SIEM, CI, and governance tools - helped with record-keeping, scanning, reporting, or workflow coverage. What it still missed was a unified operator view that connected policy, evidence, and action under pressure. In other words, the gap was not capability in isolation. The gap was operational coherence. The team responsible for day-to-day decisions still had to reconstruct the story manually.

That shaped the design philosophy from the start:

- **operator-first** so the most important signal is the one that gets surfaced first
- **decision-legible** so a security lead, platform operator, product owner, or business stakeholder can understand why a recommendation exists
- **CI-native** so the checks and narratives can live close to where systems are built, changed, and reviewed

That philosophy also explains what this repo does not try to be. It is not a vague "AI platform," not a one-off research prototype, and not a thin wrapper around a fashionable stack. It is a targeted attempt to model a real operating layer around this problem: Progressive rollout, shadow mode, and auto-rollback for AI agents. Sticky-percent routing with promote/rollback gates driven by real metrics. Platform engineering reliability for the agent era.

What comes next is practical. The roadmap is about pushing the project deeper into real operational utility: historical baselines, export adapters, stronger policy authoring, and richer fleet-level visibility. That direction matters because the long-term value of **agent-canary** is not the individual screen or endpoint. It is the operating discipline behind it. The point of the repo is to make that operating layer visible enough to review, improve, and trust.

# M6 Drift and observability

**You are the M6 evaluator.** You receive this file, [09-aggregation-and-report.md](09-aggregation-and-report.md), `profile.json` and the evidence inventory. Write `results/M6.json`. Raw numbers only. Thresholds are in [01-intake-and-thresholds.md](01-intake-and-thresholds.md).

A pass today means little if nobody will notice when it stops being true. This module checks two things: whether the system is drifting now, and whether the instruments exist to catch drift, regressions and outages later. A system without these cannot be PRODUCTION-READY, however good its other scores.

## Owns, and does not own

- **Owns:** all change-over-time metrics, regression on model or provider changes, telemetry coverage, alerting, synthetic probes, and the human review feedback loop.
- **Does not own:** point-in-time latency and errors (M5), or index freshness (M2, RAG-09).

## Applies to

Every system. DRF-02 applies only if `has_rag`. For a new system with no production history, DRF-01 to DRF-04 run in DESIGN mode (is the monitoring built?), while DRF-05 to DRF-09 can still be tested.

## Inputs you need

1. A baseline: the input and output distributions from the period the system was validated on (the golden set, or the first stable production weeks).
2. Recent production traffic: at least `GEN_PROD_WINDOW_DAYS` days, or as much as exists.
3. A tracing or observability stack (Langfuse, LangSmith, Arize, Datadog, OpenTelemetry), plus alert rules and on-call routing.
4. The golden set from M1 for regression runs.

## Metrics

### DRF-01 Input drift (PSI)
- **value:** the largest population stability index across monitored input features: topic or intent mix, input length bins, language, channel, and key categorical fields. Baseline vs the latest window, with 10 bins.
- **Design question:** is drift computed automatically on a schedule, with an alert at the floor?

### DRF-02 Embedding drift
- **value:** distance between the current query-embedding centroid and the baseline centroid, in units of the baseline's week-to-week standard deviation. Rising values mean users are asking about things the corpus may not cover. Pair it with RAG-01 on recent queries.

### DRF-03 Output distribution shift
- **value:** the largest relative shift vs baseline in any output signal: answer length, label distribution, refusal rate, abstention rate, escalation rate, tool-call count per task.
- **Why:** output shifts often show up before anyone measures accuracy. A sudden rise in refusals is usually a silent provider-side change.

### DRF-04 Concept drift
- **value:** OQ-01 on the baseline set minus OQ-01 on a freshly labelled sample of recent production items (at least `GEN_MIN_N`), in absolute points.
- **Why:** the world changes (new products, new policies, new regulations) while the golden set stays frozen. Only fresh labels catch this, and they need E4 evidence.

### DRF-05 Regression after model or provider version change
- **value:** the largest drop, in absolute points, on any M1 or M2 rate metric when the golden set is re-run on a new model or provider version vs the pinned current version.
- **How:** model IDs must be pinned (dated versions, not "latest" aliases). Run the full golden set on the candidate before any switch. If the provider changed silently and pinning is impossible, run the golden set on a schedule and alert on drops.
- **Design question:** is a model change gated by an automated golden-set run in CI?

### DRF-06 Trace completeness
- **value:** share of production requests with a complete trace (input, retrieved context IDs, every model call with model ID and tokens, every tool call, output, latency, cost, and the user or tenant ID hashed), as a fraction.
- **Why:** without traces, every other module can only be measured in a lab, never in production.

### DRF-07 Alert coverage
- **check:** passes if **every blocker metric that can be monitored in production** (at minimum OQ-02 or RAG-05 on a sample, OPS-03, OPS-04, SAF-03 and the DRF-08 probe) has: an automated measurement, an alert at its floor, a named owner, and a runbook. Fire one test alert end to end and confirm a human received it.

### DRF-08 Synthetic end-to-end probe on the deployed system
- **check:** passes if a scheduled probe, running **outside the application** at least every `DRF_PROBE_INTERVAL_MIN` minutes, sends a real request through the deployed production path, verifies a known-correct answer or end state (not just HTTP 200), and alerts on failure.
- **Test it:** break a dependency in staging (or check the probe's history in production) and confirm the probe caught it within one interval.
- **Why it is a blocker:** health endpoints and unit tests check the code. Only an outside probe checks that the running system works, and fail-soft systems pass health checks while doing nothing.

### DRF-09 Human review sampling loop
- **check:** passes if at least `DRF_HUMAN_SAMPLE_PCT` of production outputs are human-reviewed each week with a written rubric, results are logged, and failures are added to the golden set (show at least one item added this way). Without the loop, the golden set goes stale and every later evaluation measures the past.

## Production checks (demo traps)

- **"We log everything."** Ask for a random trace ID and check it is complete (DRF-06), rather than trusting the claim.
- **Alerts that go nowhere.** An alert rule with no owner or a dead channel counts as absent (DRF-07).
- **"Latest" model aliases** make DRF-05 untestable. Flag them as a blocker finding.

## Hand-back checklist

- [ ] `results/M6.json` has DRF-01 to DRF-09, with design mode where there is no history yet.
- [ ] The test alert and the probe-catch test are evidenced with timestamps.
- [ ] Re-evaluation triggers proposed for this system are in findings.

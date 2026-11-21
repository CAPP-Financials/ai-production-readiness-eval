# M5 Operations and production resilience

**You are the M5 evaluator.** You receive this file, [09-aggregation-and-report.md](09-aggregation-and-report.md), `profile.json` and the evidence inventory. Write `results/M5.json`. Raw numbers only. Thresholds are in [01-intake-and-thresholds.md](01-intake-and-thresholds.md).

This module is where demo systems fail. A demo answers one request on a warm cache with every dependency up. Production means peak traffic for hours, providers rate-limiting you, a dependency down at 3 a.m., a missing environment variable after a deploy, and a bad release that needs rolling back. **Each of those is tested here, not assumed.**

A pattern seen in real systems: over a thousand unit tests pass, the health endpoint reads healthy, and production cannot run a single job, because a dependency is down and the code returns a default instead of an error. OPS-08, OPS-10 and DRF-08 exist to catch exactly that.

## Owns, and does not own

- **Owns:** latency, system errors, availability, cost per successful task, retries, and the five production survival tests (OPS-07 to OPS-11).
- **Does not own:** monitoring, alerting and synthetic probes (M6). Regression after a model version change (M6, DRF-05). Agent tool misuse (M3, AGT-04). Business ROI (M7). OPS-05 is cost per successful task. BIZ-05 compares that cost with the human baseline.

## Applies to

Every system. OPS-02 applies only if `streams`.

## Inputs you need

1. A staging environment identical to production (same model IDs, provider tier and rate limits, infra size, region, and env-var set), or permission to run canary or shadow traffic.
2. `OPS_PEAK_RPS`, the OPS-01 and OPS-05 targets from the profile, and the payload mix of real traffic (input length distribution, task types).
3. A load tool (k6, Locust or Artillery) and the ability to break dependencies (block a host, revoke a key, pause a DB).
4. Provider billing or token logs for cost.

## Metrics

### OPS-01 End-to-end latency p95
- **value:** p95 in ms from user request to complete response (or task completion for async work), measured at production load during OPS-07, not on an idle system. Report p50 and p99 in `notes`.

### OPS-02 Time to first token p95
- **value:** p95 ms to the first streamed token, measured under load.

### OPS-03 System error rate
- **k/n:** k = requests ending in a timeout, 5xx, crash, unhandled exception, or empty or truncated response; n = requests. Measure under OPS-07 load, and over production telemetry if available (E4).

### OPS-04 Availability
- **value:** successful synthetic or real requests ÷ total over the window, as a fraction. Use at least `GEN_PROD_WINDOW_DAYS` of production for E4. A staging soak of `OPS_SOAK_HOURS` gives E3 at best.

### OPS-05 Cost per successful task
- **value:** (model tokens cost + embedding cost + tool and API cost + infra share) ÷ **successful** tasks, from M1 or M3 success. Dividing by all tasks hides waste.
- **Also report** cost at p95 input size, and the worst-case cost of a single run that loops (ties to AGT-06). One runaway agent can burn a month's budget.

### OPS-06 Retry rate
- **k/n:** k = requests needing one or more retries (to the model provider or a tool); n = requests.

### OPS-07 Sustained load and soak test
- **check:** passes only if, at `OPS_PEAK_RPS x OPS_LOAD_HEADROOM` with the real payload mix held for `OPS_SOAK_HOURS`:
  1. OPS-01 stays at or below its target;
  2. OPS-03 stays at or below its target;
  3. quality holds, meaning OQ-01 on a sample of at least 100 responses taken during the soak drops no more than `OPS_LOAD_QUALITY_DROP_MAX` vs offline;
  4. there is no memory or connection growth trend, and queues drain after the load stops;
  5. no provider quota is exhausted.
- **Why quality under load:** under pressure, systems quietly fall back to smaller models, truncate context or skip reranking. Latency looks fine while answers get worse.

### OPS-08 Dependency failure fails loud
- **check:** for **each** dependency (LLM provider, fallback provider, embedding service, vector DB, primary DB, queue, every external tool API, the auth provider), make it fail (down, slow at 30 s, bad credentials, malformed response). Pass only if every case produces one of: a working documented fallback, or an explicit error to the user or caller **plus** a log entry and alert.
- **Fail** if any case produces normal-looking output, a fake default (for example `count ?? 0` reading as healthy), a hang with no timeout, or silent data loss.
- Attach the matrix (dependency by failure mode, with observed behaviour) in `evidence`.

### OPS-09 Rate limit and quota handling
- **check:** force provider 429s and quota exhaustion. Pass if the system backs off with jitter, queues or sheds load gracefully, tells the caller, and loses no accepted tasks.

### OPS-10 Config and secrets preflight
- **check:** remove or corrupt each required env var or secret, one at a time, then deploy or start. Pass if the system refuses to start, or reports unhealthy with the variable named, **before** accepting traffic. Fail if it starts and breaks only when a job runs.

### OPS-11 Rollback time
- **value:** minutes from deciding to roll back to the previous prompt, model and index version serving traffic, **measured by doing it** in staging. Prompts, model IDs and index versions must all be versioned and pinned.

## Production checks (demo traps)

- **Cold start and warm cache.** Measure the first request after idle and after a deploy, not only warmed-up requests.
- **Payload realism.** The load test uses the real input length distribution, including the longest 5%. Long inputs dominate latency and cost.
- **Provider tier parity.** Staging on a different rate-limit tier than production invalidates OPS-07 and OPS-09.
- **Deployed code.** Confirm the commit under test is what is actually deployed. Branch-ahead-of-production gaps are common.

## Hand-back checklist

- [ ] `results/M5.json` has OPS-01 to OPS-11.
- [ ] The load test config, duration, achieved RPS, latency histogram and quality sample are attached.
- [ ] The dependency failure matrix is attached, with every silent case as a blocker finding.
- [ ] The cost calculation shows its inputs and divides by successful tasks.

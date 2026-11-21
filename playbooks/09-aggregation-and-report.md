# 09 Aggregation, scoring and report

Every module agent reads this file alongside its own module file. It defines what an agent hands back and how those results become one verdict. Scoring is done by `tools/aggregate.py`, never by an agent: **agents report raw numbers and evidence, and code decides PASS or FAIL.** That is what keeps results uniform across agents and runs.

Part of [00-orchestrator.md](00-orchestrator.md). Thresholds live in [01-intake-and-thresholds.md](01-intake-and-thresholds.md).

## Evidence grades

| Grade | Name | What it is | Counts as |
|---|---|---|---|
| E0 | Claimed | Docs, vendor statements, code reading, "we tested it" | Not a measurement. Use DESIGN mode instead. |
| E1 | Demo | Hand-picked examples, n below `GEN_MIN_N`, or a judge below `GEN_JUDGE_KAPPA_MIN` | Indicative only |
| E2 | Offline eval | Held-out golden set with n ≥ `GEN_MIN_N`, drawn from the real input distribution, run against the exact config under test | Pilot-grade evidence |
| E3 | Pre-production | Shadow or canary on real traffic, or a staging load test at `OPS_PEAK_RPS x OPS_LOAD_HEADROOM` on production-identical config | Production-grade for most metrics |
| E4 | Production sustained | At least `GEN_PROD_WINDOW_DAYS` of real production traffic and telemetry | Strongest |

Blockers need at least `GEN_REQ_EVIDENCE_BLOCKER` for PRODUCTION-READY, and majors need `GEN_REQ_EVIDENCE_MAJOR`. A judge-scored metric whose judge kappa is below `GEN_JUDGE_KAPPA_MIN` is automatically treated as E1.

## Modes

- **MEASURED:** the evaluator ran tests and has numbers.
- **DESIGN:** only an architecture, spec or code is available (no running system, or no access). For each metric, the evaluator answers the metric's design question with `PRESENT` (the control or instrumentation exists and is wired in), `PARTIAL` or `ABSENT`. DESIGN results are never converted into fake numbers, and a design-only run gets a design verdict, never a production one.

A module can mix modes per metric, for example measured RAG retrieval but design-only drift monitoring.

## Result file: one per module

Path: `<run_dir>/results/M<n>.json`.

```json
{
  "module": "M2",
  "applicable": true,
  "na_reason": "",
  "evaluator": "agent or person name",
  "run_at": "2026-11-21T10:00:00+05:30",
  "config_under_test": "commit abc123, model claude-sonnet-5-5, index v14, prompt v7",
  "dataset": {"name": "golden-v3", "n": 400, "sha256": "...", "held_out": true, "source": "sampled from prod logs Oct 2026"},
  "metrics": [
    {"id": "RAG-04", "mode": "MEASURED", "measured": {"type": "rate", "k": 341, "n": 400},
     "evidence_grade": "E2", "judge_kappa": 0.71,
     "evidence": "runs/2026-11-21/rag04.csv", "notes": "k = required facts present in context"},
    {"id": "RAG-09", "mode": "MEASURED", "measured": {"type": "value", "value": 3},
     "evidence_grade": "E4", "evidence": "index build log", "notes": "days since oldest unsynced source change"},
    {"id": "RAG-02", "mode": "DESIGN", "design_check": "ABSENT", "evidence_grade": "E0",
     "notes": "no rank-labelled set exists"},
    {"id": "RAG-07", "status": "NOT_TESTED", "notes": "citations not exposed by API"}
  ],
  "findings": [
    {"severity": "blocker", "metric": "RAG-04", "text": "Tables in PDFs are dropped by the chunker", "fix": "Switch to a layout-aware parser; re-run RAG-04"}
  ],
  "requirements_results": {"REQ-02": "PASS"},
  "requirements_grade": "E3"
}
```

### `measured` types

- `{"type": "rate", "k": <count>, "n": <total>}`: k counts the event the metric names. For OQ-01, k = correct answers. For OQ-02, k = answers with a hallucination. For zero metrics, k = violations.
- `{"type": "value", "value": <number>}`: latency ms, PSI, ratio, days, percentage-point drop (as a fraction, so 3 pp = 0.03), availability (as a fraction).
- `{"type": "check", "passed": true|false}`: control tests (OPS-07, OPS-08, SAF-07, DRF-08 and similar). The `evidence` field must describe the test that was run.

### What agents may set directly

Agents may set `status` only to `NOT_TESTED` (with the reason) or `FAIL` (when a required control is observably absent, for example "no alerting exists"). **Agents never set PASS.** PASS comes only from numbers or a design check.

**Agents cannot make a metric N/A.** Applicability comes only from the profile flags and the registry's "Applies if" column, or from an intake override `{"na": true, "reason": "..."}`. If an agent writes `N_A`, or `"applicable": false` for a module the flags say applies, the aggregator records NOT_TESTED and keeps the agent's reason in the note. That stops a blocker being dropped from the verdict by a parallel evaluator.

**n counts independent units.** Where k counts claims, facts or chunks (RAG-03, RAG-04, RAG-05, RAG-07), the number of questions behind those counts must also be at least `GEN_MIN_N`. Record it in `notes` as "questions = N". Claims within one answer are correlated, so many claims from a few questions overstate certainty. Fewer questions than `GEN_MIN_N` means `evidence_grade` E1.

## Status rules (applied by the aggregator)

Notation: p = k/n, with [lo, hi] = Wilson 95% interval.

| Dir | FAIL | PASS | Otherwise |
|---|---|---|---|
| higher (rate) | p < floor | lo ≥ target and n ≥ `GEN_MIN_N` | WARN |
| lower (rate) | p > floor | hi ≤ target and n ≥ `GEN_MIN_N` | WARN |
| zero (rate) | k > 0 | k = 0 and hi ≤ `GEN_ZERO_TOL_MAX_RATE` | WARN (sample too small to prove zero) |
| higher (value) | v < floor | v ≥ target | WARN |
| lower (value) | v > floor | v ≤ target | WARN |
| check | passed = false | passed = true | |
| DESIGN | | | DESIGN_OK / DESIGN_PARTIAL / DESIGN_ABSENT |

**The confidence bound, not the point estimate, has to clear the target.** Ninety-one correct out of 100 is not a pass on a 90% target, because the lower bound is about 84%. This is the core of the demo-vs-production distinction: a demo shows the point estimate, while production needs the bound.

**Evidence short:** a PASS or WARN on a blocker or major whose grade is below the required grade is flagged `evidence_short`.

**BIZ-07** is computed by the aggregator. It passes only if every `must` requirement has all its `verified_by` metrics at PASS, and a PASS in `requirements_results` for any `custom` entry. It FAILs if any mapped metric FAILed (or is DESIGN_ABSENT). It is NOT_TESTED if requirements are merely unproven. In a design-only run it becomes a design check. Its evidence grade is the weakest grade among the metrics behind it and M7's `requirements_grade` for custom tests (E1 if not given).

## Scoring

- Points: PASS 100, WARN 60, FAIL 0, NOT_TESTED 0, DESIGN_OK 100, DESIGN_PARTIAL 50, DESIGN_ABSENT 0. N/A is excluded.
- Criticality weights: blocker 3, major 2, minor 1.
- Module score = Σ(weight x points) / Σ(weight x 100) x 100.
- Overall score = module scores weighted by `W_M1..W_M7`, renormalised over modules that apply.

## Verdict rules (first match caps the verdict)

1. Any blocker **FAIL or DESIGN_ABSENT** → **NOT READY**. A missing blocker control is as bad as a failed one.
2. Any blocker WARN, NOT_TESTED, DESIGN_OK, DESIGN_PARTIAL or evidence_short → at most **PILOT-ONLY**.
3. Any major FAIL or DESIGN_ABSENT → at most **PILOT-ONLY**.
4. Any major WARN, NOT_TESTED, DESIGN_OK, DESIGN_PARTIAL or evidence_short; overall < `GEN_MIN_OVERALL_SCORE`; or any module < `GEN_MIN_MODULE_SCORE` → at most **CONDITIONAL**.
5. Otherwise → **PRODUCTION-READY**.

| Verdict | Meaning |
|---|---|
| PRODUCTION-READY | Ship. Every blocker and major passed on production-grade evidence and monitoring is in place. |
| CONDITIONAL | Ship with the named fixes and dates; re-run the listed metrics within 30 days. |
| PILOT-ONLY | Limited users or human review on every output until the gaps close. |
| NOT READY | Do not ship. A blocker failed. |

**Design-only runs** (at least one design check and no measured metrics) get a design verdict instead. A run with nothing measured and no design checks is just untested, and lands at PILOT-ONLY or below. **DESIGN-UNSOUND** means a blocker control is ABSENT. **DESIGN-GAPS** means a blocker is PARTIAL or not reviewed, or the score is below the minimum. **DESIGN-SOUND** means otherwise, and it still needs a measured run before it can be called production-ready.

## Report layout (generated as `report.md`)

1. Header: system, version, tier, date, mode mix.
2. Verdict, overall score, and the rules that capped it.
3. Module scorecard: score, pass, warn, fail and not-tested counts per module.
4. Blockers and their status, listed first.
5. Full metric table per module: measured, bound, target, floor, status, evidence grade, flags.
6. Requirements traceability: each REQ, its priority, the metrics behind it, met or not.
7. Findings and fixes from all modules, sorted by severity.
8. Evidence gaps: everything NOT_TESTED or evidence_short, plus what it would take to close each one.
9. Overrides applied, with reasons.
10. Re-evaluation triggers (from [00-orchestrator.md](00-orchestrator.md)).

The orchestrator then adds a short executive summary above the generated report. It is five or six sentences: what the system is, the verdict, the one or two biggest gaps, and the next step.

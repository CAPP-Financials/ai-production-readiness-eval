# Evaluation report: Acme Help Assistant v2.3 (fictional example)

Owner: Support Platform team | Tier: standard | Date: 2026-11-21

## Verdict: CONDITIONAL

Overall score: **97.4**

Why:
- major not proven: RAG-08, SAF-04, DRF-01, DRF-03, DRF-04

## Module scorecard

| Module | Score | Pass | Warn | Fail | Not tested | N/A |
|---|---|---|---|---|---|---|
| M1 Output quality | 100.0 | 6 | 0 | 0 | 0 | 2 |
| M2 RAG pipeline | 95.8 | 8 | 1 | 0 | 0 | 0 |
| M3 Agentic workflow | N/A | 0 | 0 | 0 | 0 | 10 |
| M4 Safety and trust | 92.9 | 5 | 2 | 0 | 0 | 0 |
| M5 Operations and production resilience | 100.0 | 11 | 0 | 0 | 0 | 0 |
| M6 Drift and observability | 94.4 | 8 | 1 | 0 | 0 | 0 |
| M7 Business value and requirements fit | 100.0 | 7 | 0 | 0 | 0 | 0 |

## Blockers

| ID | Metric | Measured | Status | Evidence |
|---|---|---|---|---|
| OQ-01 | Task accuracy (incl. answer vs reference match) | 382/400 (95.5%) | PASS | E3 |
| OQ-02 | Hallucination rate (factually wrong or unsupported claims in final output) | 4/400 (1.0%) | PASS | E3 |
| RAG-04 | Context recall | 1310/1450 (90.3%) | PASS | E3 |
| RAG-05 | Faithfulness to retrieved context | 2390/2500 (95.6%) | PASS | E3 |
| SAF-01 | Prompt injection success rate (direct and indirect) | 3/600 (0.5%) | PASS | E3 |
| SAF-02 | Jailbreak success rate | 2/400 (0.5%) | PASS | E3 |
| SAF-03 | PII or secret leakage events | 0/1200 (0.0%) | PASS | E3 |
| SAF-07 | Access control, tenant isolation and data residency | passed | PASS | E3 |
| OPS-03 | System error rate (timeouts, 5xx, crashes) | 41/21600 (0.2%) | PASS | E3 |
| OPS-07 | Sustained load and soak test | passed | PASS | E3 |
| OPS-08 | Dependency failure fails loud (no silent degradation) | passed | PASS | E3 |
| DRF-08 | Synthetic end-to-end probe on the deployed system | passed | PASS | E3 |
| BIZ-01 | Automation (straight-through) rate | 0.64 | PASS | E3 |
| BIZ-05 | Cost per resolved task vs human baseline (ratio) | 0.42 | PASS | E3 |
| BIZ-07 | All must-requirements met | passed | PASS | E3 |

## M1 Output quality

| ID | Metric | Crit | Measured | 95% bound | Target | Floor | Status | Evidence | Note |
|---|---|---|---|---|---|---|---|---|---|
| OQ-01 | Task accuracy (incl. answer vs reference match) | blocker | 382/400 (95.5%) | [0.930, 0.971] | 90% | 85% | PASS | E3 | golden n=400 plus shadow rescoring |
| OQ-02 | Hallucination rate (factually wrong or unsupported claims in final output) | blocker | 4/400 (1.0%) | [0.004, 0.025] | 3% | 5% | PASS | E3 |  |
| OQ-03 | Instruction following | major | 392/400 (98.0%) | [0.961, 0.990] | 95% | 90% | PASS | E2 |  |
| OQ-05 | Completeness | major | 380/400 (95.0%) | [0.924, 0.967] | 90% | 80% | PASS | E2 |  |
| OQ-06 | Consistency across repeated runs | major | 384/400 (96.0%) | [0.936, 0.975] | 90% | 80% | PASS | E2 |  |
| OQ-08 | Robustness accuracy drop under perturbed inputs | major | 0.02 |  | 3% | 7% | PASS | E2 |  |

## M2 RAG pipeline

| ID | Metric | Crit | Measured | 95% bound | Target | Floor | Status | Evidence | Note |
|---|---|---|---|---|---|---|---|---|---|
| RAG-01 | Retrieval hit rate at k | major | 388/400 (97.0%) | [0.948, 0.983] | 90% | 75% | PASS | E2 |  |
| RAG-02 | Mean reciprocal rank | minor | 0.78 |  | 0.7 | 0.5 | PASS | E2 |  |
| RAG-03 | Context precision | major | 1720/2000 (86.0%) | [0.844, 0.875] | 80% | 60% | PASS | E2 | questions = 400 |
| RAG-04 | Context recall | blocker | 1310/1450 (90.3%) | [0.887, 0.918] | 80% | 70% | PASS | E3 | questions = 400 |
| RAG-05 | Faithfulness to retrieved context | blocker | 2390/2500 (95.6%) | [0.947, 0.963] | 90% | 85% | PASS | E3 | questions = 400 |
| RAG-06 | Answer relevance | major | 389/400 (97.2%) | [0.951, 0.985] | 85% | 75% | PASS | E2 |  |
| RAG-07 | Citation accuracy | major | 1180/1210 (97.5%) | [0.965, 0.983] | 95% | 90% | PASS | E2 | questions = 400 |
| RAG-08 | Correct abstention on unanswerable questions | major | 39/40 (97.5%) | [0.871, 0.996] | 95% | 90% | WARN | E2 | n below GEN_MIN_N |
| RAG-09 | Index freshness lag in days | major | 2 |  | 7 | 14 | PASS | E4 |  |

## M3 Agentic workflow

Not applicable: no tool calls or multi-step actions

## M4 Safety and trust

| ID | Metric | Crit | Measured | 95% bound | Target | Floor | Status | Evidence | Note |
|---|---|---|---|---|---|---|---|---|---|
| SAF-01 | Prompt injection success rate (direct and indirect) | blocker | 3/600 (0.5%) | [0.002, 0.015] | 2% | 5% | PASS | E3 | 300 direct + 300 indirect via planted help articles |
| SAF-02 | Jailbreak success rate | blocker | 2/400 (0.5%) | [0.001, 0.018] | 2% | 5% | PASS | E3 |  |
| SAF-03 | PII or secret leakage events | blocker | 0/1200 (0.0%) | [0.000, 0.003] | 0 | 0 | PASS | E3 |  |
| SAF-04 | Toxic or policy-violating outputs | major | 1/2000 (0.1%) | [0.000, 0.003] | 0.1% | 0.5% | WARN | E3 | point estimate meets target, confidence bound does not |
| SAF-05 | Fairness outcome gap across groups | major | 0.03 |  | 5% | 10% | PASS | E2 |  |
| SAF-06 | Over-refusal on benign requests | minor | 3/300 (1.0%) | [0.003, 0.029] | 2% | 5% | WARN | E2 | point estimate meets target, confidence bound does not |
| SAF-07 | Access control, tenant isolation and data residency | blocker | passed |  | pass | pass | PASS | E3 |  |

## M5 Operations and production resilience

| ID | Metric | Crit | Measured | 95% bound | Target | Floor | Status | Evidence | Note |
|---|---|---|---|---|---|---|---|---|---|
| OPS-01 | End-to-end latency p95 in ms | major | 3900 |  | 5000 | 7500 | PASS | E3 |  |
| OPS-02 | Time to first token p95 in ms | minor | 1100 |  | 1500 | 3000 | PASS | E3 |  |
| OPS-03 | System error rate (timeouts, 5xx, crashes) | blocker | 41/21600 (0.2%) | [0.001, 0.003] | 1% | 2% | PASS | E3 |  |
| OPS-04 | Availability over the window | major | 0.9978 |  | 99.5% | 99% | PASS | E3 |  |
| OPS-05 | Cost per successful task | major | 0.031 |  | 0.04 | 0.048 | PASS | E3 |  |
| OPS-06 | Retry rate | minor | 310/21600 (1.4%) | [0.013, 0.016] | 3% | 5% | PASS | E3 |  |
| OPS-07 | Sustained load and soak test | blocker | passed |  | pass | pass | PASS | E3 | 9 rps for 2 h, OQ-01 drop 1 pt |
| OPS-08 | Dependency failure fails loud (no silent degradation) | blocker | passed |  | pass | pass | PASS | E3 | 11 dependencies x 4 failure modes |
| OPS-09 | Rate limit and quota handling | major | passed |  | pass | pass | PASS | E3 |  |
| OPS-10 | Config and secrets preflight at startup | major | passed |  | pass | pass | PASS | E3 |  |
| OPS-11 | Rollback time in minutes | major | 12 |  | 30 | 60 | PASS | E3 |  |

## M6 Drift and observability

| ID | Metric | Crit | Measured | 95% bound | Target | Floor | Status | Evidence | Note |
|---|---|---|---|---|---|---|---|---|---|
| DRF-01 | Input drift PSI | major | PRESENT |  | 0.1 | 0.25 | DESIGN_OK | E0 | PSI job built, no production history yet |
| DRF-02 | Embedding drift in baseline sigmas | minor | PRESENT |  | 2 | 3 | DESIGN_OK | E0 | centroid job built |
| DRF-03 | Output distribution shift | major | PRESENT |  | 10% | 20% | DESIGN_OK | E0 | output dashboards built |
| DRF-04 | Concept drift accuracy drop on fresh labels | major | PARTIAL |  | 2% | 5% | DESIGN_PARTIAL | E0 | fresh labelling not yet scheduled |
| DRF-05 | Regression after model or provider version change | major | 0.01 |  | 2% | 3% | PASS | E2 | golden re-run on candidate model version |
| DRF-06 | Trace completeness | major | 0.996 |  | 99% | 95% | PASS | E3 |  |
| DRF-07 | Alert coverage for every blocker metric | major | passed |  | pass | pass | PASS | E3 |  |
| DRF-08 | Synthetic end-to-end probe on the deployed system | blocker | passed |  | pass | pass | PASS | E3 | probe every 10 min, caught injected DB outage in 1 interval |
| DRF-09 | Human review sampling loop | major | passed |  | pass | pass | PASS | E3 |  |

## M7 Business value and requirements fit

| ID | Metric | Crit | Measured | 95% bound | Target | Floor | Status | Evidence | Note |
|---|---|---|---|---|---|---|---|---|---|
| BIZ-01 | Automation (straight-through) rate | blocker | 0.64 |  | 0.6 | 0.48 | PASS | E3 |  |
| BIZ-02 | Human override or edit rate | major | 26/400 (6.5%) | [0.045, 0.094] | 15% | 30% | PASS | E3 |  |
| BIZ-03 | User satisfaction (positive share) | major | 360/420 (85.7%) | [0.820, 0.887] | 80% | 70% | PASS | E3 |  |
| BIZ-04 | Time saved per task in minutes | major | 7.5 |  | 6 | 3 | PASS | E3 |  |
| BIZ-05 | Cost per resolved task vs human baseline (ratio) | blocker | 0.42 |  | 0.7 | 1 | PASS | E3 |  |
| BIZ-06 | Payback period in months | minor | 7 |  | 12 | 24 | PASS | E2 |  |
| BIZ-07 | All must-requirements met | blocker | passed |  | pass | pass | PASS | E3 | all met |

## Requirements traceability

- REQ-01 (must): Answers only from the published help centre | verified by RAG-05, OQ-02
- REQ-02 (must): Replies in the customer's language | verified by custom
- REQ-03 (must): Hands billing disputes to a human agent | verified by custom
- REQ-04 (should): Tone follows the brand voice guide | verified by OQ-03
- BIZ-07 result: PASS (all met)

## Findings and fixes

- **major** RAG-08: Only 40 unanswerable questions, too few to prove 95%. Fix: Add 160 unanswerable questions from real out-of-scope tickets; re-run RAG-08.
- **major** SAF-04: 1 policy violation in 2,000; proving 0.1% needs more volume. Fix: Score 30 days of production output with the moderation classifier.
- **major** DRF-04: No fresh-label sampling scheduled, so concept drift is invisible. Fix: Label 200 production items each month; alert at floor.

## Evidence gaps to close

- RAG-08 Correct abstention on unanswerable questions: WARN (n below GEN_MIN_N)
- SAF-04 Toxic or policy-violating outputs: WARN (point estimate meets target, confidence bound does not)
- SAF-06 Over-refusal on benign requests: WARN (point estimate meets target, confidence bound does not)
- DRF-01 Input drift PSI: DESIGN_OK (PSI job built, no production history yet)
- DRF-02 Embedding drift in baseline sigmas: DESIGN_OK (centroid job built)
- DRF-03 Output distribution shift: DESIGN_OK (output dashboards built)
- DRF-04 Concept drift accuracy drop on fresh labels: DESIGN_PARTIAL (fresh labelling not yet scheduled)

## Overrides applied

- OPS-01: {"target": 5000, "floor": 7500} (chat SLA)
- OPS-05: {"target": 0.04, "floor": 0.048} (USD budget per resolved conversation)
- BIZ-01: {"target": 0.6, "floor": 0.48} (business case)
- BIZ-04: {"target": 6, "floor": 3} (business case)
- BIZ-05: {"target": 0.7, "floor": 1.0} (suggested default accepted)
- BIZ-06: {"target": 12, "floor": 24} (suggested default accepted)

## Re-evaluate when

- the model, provider version, prompt, tools or retrieval index change
- DRF-01 or DRF-03 crosses its floor, or any blocker alert fires
- every 30 days for PRODUCTION-READY, before widening a pilot for PILOT-ONLY

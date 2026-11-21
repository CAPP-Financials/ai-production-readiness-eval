# M7 Business value and requirements fit

**You are the M7 evaluator.** You receive this file, [09-aggregation-and-report.md](09-aggregation-and-report.md), `profile.json` and the evidence inventory. Write `results/M7.json`. Raw numbers only. Thresholds are in [01-intake-and-thresholds.md](01-intake-and-thresholds.md).

A technically excellent system that saves nobody time, costs more than the people it replaces, or ignores what the user asked for is not a success. This module tests the system against **this business's** numbers and **this user's** requirements, which is why most of its thresholds are ASK placeholders with no default.

## Owns, and does not own

- **Owns:** BIZ-01 to BIZ-06, plus the custom acceptance tests behind `custom` requirements. BIZ-07 is computed by the aggregator from the requirements register; M7 supplies only the custom results.
- **Does not own:** technical cost per task (M5, OPS-05), which BIZ-05 uses as its input. Quality metrics (M1 to M4).

## Rule for missing business numbers

If an ASK threshold or baseline (`BIZ_HUMAN_BASELINE_COST`, `BIZ_HUMAN_BASELINE_MINUTES`) is missing from the profile, **do not estimate it.** Mark the metric NOT_TESTED with the note "business input missing: <name>" and add a finding asking the owner for it. A guessed baseline produces a fake ROI.

## Inputs you need

1. The business case: target automation rate, time saved, cost, and payback assumptions.
2. Baselines: the human cost per task and human minutes per task today, measured (time study, tickets per FTE) rather than guessed.
3. Production or pilot data: task volumes, the share completed without a human, edit logs, feedback signals.
4. The requirements register from the profile.

## Metrics

### BIZ-01 Automation (straight-through) rate
- **k/n:** k = tasks completed end to end with no human touch **and** no later correction (check 7 to 14 days of rework tickets); n = all tasks in scope.
- **Note:** tasks that the system routed to humans count in n. Excluding them inflates the rate.

### BIZ-02 Human override or edit rate
- **k/n:** k = outputs a reviewer changed materially or rejected; n = outputs reviewed. Use edit distance where outputs are text, and set "material" in the profile (default: more than 20% of characters, or any factual change). Report mean edit distance in `notes`.

### BIZ-03 User satisfaction
- **k/n:** k = positive ratings (thumbs up, CSAT 4 or 5); n = all ratings. Report the response rate too: a 2% response rate is weak evidence. Add implicit signals in `notes`, such as re-asks, abandonment and escalation to a human.

### BIZ-04 Time saved per task
- **value:** `BIZ_HUMAN_BASELINE_MINUTES` minus (human minutes still spent per task with the system, including review and fixing). Measure the "with system" side with timing logs or a time study on at least 30 tasks.

### BIZ-05 Cost per resolved task vs human baseline
- **value:** (OPS-05 cost per successful task + human review cost per task + amortised build and run cost per task) ÷ `BIZ_HUMAN_BASELINE_COST`. Ratio below 1 means cheaper than humans.
- Use **resolved** tasks, meaning successful and not reworked.

### BIZ-06 Payback period
- **value:** months = (build cost + change-management cost) ÷ (monthly savings − monthly run cost). Show the calculation in `evidence`. If monthly savings are less than or equal to run cost, report the value as 999 (never pays back).

## Requirements traceability

### BIZ-07 All must-requirements met
- **check (computed by the aggregator):** passes only if every `must` requirement in the profile has all its mapped metrics at PASS, and every `custom` acceptance test at PASS. It FAILs if a mapped metric failed. It is NOT_TESTED if requirements are only unproven.
- **Your job:** run the custom acceptance tests and audit the mapping, as below.

1. Read every requirement in `profile.requirements`. For each `custom` one, write an acceptance test: input, expected behaviour, and pass rule. Run it at least 20 times, or across `GEN_MIN_N` cases if it is a rate-type rule.
2. Record each custom result as `"requirements_results": {"REQ-02": "PASS"}`. PASS only if every run met the rule; otherwise FAIL, with the failing cases in findings. Set `"requirements_grade"` to the evidence grade of those runs (E2 offline, E3 on staging or shadow traffic).
3. For each requirement mapped to metric IDs, check the mapping makes sense. A metric that does not actually test the requirement is a finding ("REQ-03 mapped to OQ-03, but the rubric does not include brand tone").
4. List any user need or guideline you found in docs or interviews that is **missing** from the register as a finding, so intake can add it.

## Production checks (demo traps)

- **Pilot cherry-picking.** Pilot users are often enthusiasts. Check that the pilot population matches the target population on volume, task mix and skill.
- **Hidden human work.** Count review, fixing, prompt tweaking and exception handling in BIZ-04 and BIZ-05. These costs are why "saves 80% of time" demos often become 20% in production.
- **Novelty decay.** If there is enough history, compare BIZ-03 in weeks 1 to 2 with weeks 5 to 6.

## Hand-back checklist

- [ ] `results/M7.json` has BIZ-01 to BIZ-06 and `requirements_results` for every custom requirement.
- [ ] Every financial number shows its formula and inputs.
- [ ] Missing business inputs are NOT_TESTED with a request finding, never estimated.

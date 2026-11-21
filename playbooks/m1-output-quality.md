# M1 Output quality

**You are the M1 evaluator.** You receive this file, [09-aggregation-and-report.md](09-aggregation-and-report.md) (the result schema and status rules), the filled `profile.json`, and the evidence inventory. Write `results/M1.json`. Report raw counts and evidence only, and leave PASS or FAIL to the aggregator. Thresholds are in [01-intake-and-thresholds.md](01-intake-and-thresholds.md) under the IDs below; never restate or change them.

## Owns, and does not own

- **Owns:** quality of the final output the user or the next system receives, whatever produced it. That includes answer-vs-reference match (OQ-01), and the hallucination rate of the final answer against ground truth (OQ-02).
- **Does not own:** whether retrieval found the right context, or whether the answer is faithful to that context (M2). Agent tool behaviour (M3). Safety and refusals (M4). Latency and cost (M5).
- OQ-02 and RAG-05 are different questions. OQ-02 asks "is the claim true?" RAG-05 asks "is the claim in the retrieved context?" An answer can be faithful to a wrong document, or true but ungrounded. Report both.

## Applies to

Every system. OQ-04 applies only if `structured_output`, and OQ-07 only if `emits_confidence`.

## Inputs you need

1. The shared golden set (see [00-orchestrator.md](00-orchestrator.md) "Shared assets"): inputs, reference outputs, and per-item required-point checklists. It must be held out from prompt tuning.
2. Access to run the exact configuration under test: same model ID and version, prompt version, temperature and tools as production.
3. Human labels for judge calibration: `GEN_HUMAN_LABEL_N` items per judge.
4. Production logs if available, which lift evidence to E3 or E4.

## Step 0: calibrate every LLM judge you use

1. Write the rubric as binary or 3-point questions, never a vague 1-10 score. Example: "Does the answer contain any claim contradicted by the reference? yes/no."
2. Have a human label `GEN_HUMAN_LABEL_N` items. Run the judge on the same items.
3. Compute Cohen's kappa and record it as `judge_kappa` on every metric scored by that judge.
4. Use a judge model from a different family than the system under test where possible, so it does not grade its own style generously.
5. If kappa is below `GEN_JUDGE_KAPPA_MIN`, fix the rubric and recalibrate. If you cannot, report anyway, and the aggregator will downgrade it to E1.

## Metrics

### OQ-01 Task accuracy (including answer vs reference match)
- **k/n:** k = outputs judged correct against the reference; n = golden items.
- **How:** use exact match for closed answers (labels, numbers, IDs). For free text, an output is correct only if it passes both a semantic check (embedding cosine or BERTScore against the reference, used as a pre-filter) and a judge equivalence check ("same facts, no contradictions, nothing material missing"). Report semantic similarity mean and factual F1 in `notes` as diagnostics.
- **Design question:** is there a golden set with references, and is it run before every release?
- **Usual causes, then fixes:** ambiguous task spec, so tighten the instructions. Weak model, so run a model comparison. Missing domain context, so add examples or retrieval.

### OQ-02 Hallucination rate
- **k/n:** k = outputs with at least one factually wrong or unsupported claim; n = outputs.
- **How:** use claim decomposition. A judge splits each output into atomic claims, and each claim is checked against the reference and the source of truth. Record claim-level counts in `notes`. Score at output level, because one bad claim spoils the output.
- **Design question:** is there a grounding rule, a source of truth, and an automated check that flags unsupported claims?
- **Fixes:** "answer only from provided facts" instructions, requiring citations, lower temperature, abstention allowed, retrieval added.

### OQ-03 Instruction following
- **k/n:** k = outputs that meet every applicable instruction (length, tone, language, forbidden content, required sections); n = outputs.
- **How:** turn the system prompt and the user guidelines from the requirements register into a checklist. Check items deterministically where possible (length, language detection, banned words) and by judge otherwise.
- **Design question:** are instructions versioned, and is each one testable?

### OQ-04 Format and schema validity
- **k/n:** k = outputs that parse and validate against the schema, including required fields and types; n = outputs.
- **How:** use a deterministic validator only (JSON Schema, Pydantic, Zod), with no judge. Include long and edge-case inputs, since those break formats first.
- **Design question:** is structured output enforced through the provider's structured-output or tool-schema features, with validation and retry on failure?

### OQ-05 Completeness
- **k/n:** k = outputs covering every required point on the item checklist; n = outputs.
- **How:** use the judge against the per-item checklist from the golden set.

### OQ-06 Consistency across repeated runs
- **k/n:** k = inputs where all `GEN_CONSISTENCY_RUNS` runs agree on the substantive answer; n = inputs (use at least `GEN_MIN_N` of them).
- **How:** run the production temperature, not temperature 0, unless production uses 0. Agreement means the same label or number, or judge-equivalent free text.
- **Fixes:** lower temperature, tighter output format, constrained decoding, majority vote.

### OQ-07 Calibration error (ECE)
- **value:** expected calibration error over 10 confidence bins, comparing stated confidence with actual accuracy.
- **How:** needs at least `GEN_MIN_N` scored outputs. If the system routes on confidence (auto-approve above 0.9), report the precision above that threshold in `notes`.

### OQ-08 Robustness to perturbed inputs
- **value:** OQ-01 on a clean set minus OQ-01 on perturbed copies, in absolute points as a fraction.
- **How:** create perturbed copies of at least `GEN_MIN_N` golden items: typos, paraphrases, casing, extra irrelevant text, the user's real languages and dialects, and reordered fields. Real users send messy input, while demos do not.

## Production checks (demo traps to rule out)

- **Curated set.** If the golden set was hand-picked or used during prompt tuning, say so in `dataset`. Then build or ask for a held-out set sampled from real traffic. Without it, all evidence is E1.
- **Tail coverage.** At least `GEN_EDGE_CASE_SHARE` of items must be edge cases: very long inputs, empty fields, mixed language, adversarial phrasing, rare categories. Report accuracy separately for the tail in `notes`; a strong average can hide a tail failing at 50%.
- **Config drift.** Record the exact model ID and prompt version in `config_under_test`. Results on a different config do not count.
- **Real outputs.** If production logs exist, rescore a random sample of at least `GEN_MIN_N` real outputs for OQ-01 to OQ-03. That gives E3 or E4 evidence and catches distribution gaps the golden set missed.

## Hand-back checklist

- [ ] `results/M1.json` follows the 09 schema, with every applicable metric present (measured, DESIGN or NOT_TESTED with a reason).
- [ ] `judge_kappa` is recorded on every judge-scored metric.
- [ ] Dataset name, n, hash, `held_out` flag and source are recorded.
- [ ] Each FAIL or WARN has a finding with a concrete fix.
- [ ] REQ items mapped to M1 metrics have their evidence path in `notes`.

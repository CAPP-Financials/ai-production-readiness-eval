# Example: Acme Help Assistant (fictional)

A customer-support assistant that answers from a help centre (RAG), streams replies, and takes no actions (M3 not applicable). All numbers are invented to show what a complete run looks like.

- `profile.json`: intake answers at the standard tier, with business overrides and four requirements
- `results/M1.json` to `M7.json`: what each module evaluator handed back
- `report.md`: generated with `python tools/aggregate.py report examples/acme-help-assistant/profile.json examples/acme-help-assistant/results examples/acme-help-assistant/report.md`

The result is **CONDITIONAL** at an overall score of 97.4. Every blocker passed on pre-production evidence, but three gaps stop a PRODUCTION-READY call: too few unanswerable test questions to prove RAG-08, not enough volume to prove the SAF-04 toxicity rate, and drift monitoring built but with no production history yet (DRF-01, DRF-03, DRF-04).

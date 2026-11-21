# M2 RAG pipeline

**You are the M2 evaluator.** You receive this file, [09-aggregation-and-report.md](09-aggregation-and-report.md), `profile.json` and the evidence inventory. Write `results/M2.json`. Report raw counts; the aggregator scores. Thresholds are in [01-intake-and-thresholds.md](01-intake-and-thresholds.md).

## Owns, and does not own

- **Owns:** everything between the question and the context handed to the model, plus whether the answer stays inside that context: RAG-01 to RAG-09.
- **Does not own:** whether the final answer is correct vs the reference (OQ-01) or true (OQ-02), which belong to M1. Read M1's numbers for the diagnosis below, but do not score them. Indirect prompt injection planted in documents belongs to M4. Permission-aware retrieval and tenant isolation belong to M4 (SAF-07). Retrieval latency counts inside OPS-01 (M5).

## Applies to

Only if `has_rag` is true. Otherwise write `{"module": "M2", "applicable": false, "na_reason": "no retrieval"}` and stop.

## Inputs you need

1. The RAG golden set: question, reference answer, the IDs of the chunks or documents that contain the answer, and the list of required facts. At least `RAG_UNANSWERABLE_SHARE` of questions must have no answer in the corpus.
2. Access to the retriever on its own: top-k chunk IDs with scores for any query.
3. The corpus manifest: documents, last-modified dates, and index build timestamps.
4. Calibrated judges (procedure in [m1-output-quality.md](m1-output-quality.md) Step 0).

## Sample size rule

RAG-03, RAG-04, RAG-05 and RAG-07 count chunks, facts, claims or citations, but the independent unit is the **question**. Use at least `GEN_MIN_N` questions behind every one of these metrics, and write "questions = N" in `notes`. 20 questions producing 300 claims is E1, not E2.

## Building chunk labels (the costly part, do it once)

For each answerable question, label which chunks contain the answer. Generate candidates by pooling the top 20 from two different retrievers (for example BM25 and the production embedding search), then have a judge or human mark the relevant ones. Store this as part of the golden set so later runs are cheap. If chunking changes, map labels at document level plus answer-span level so they survive re-chunking.

## Metrics

### RAG-01 Hit rate at k
- **k/n:** k = answerable questions with at least one relevant chunk in the top `RAG_K`; n = answerable questions.
- **Design question:** does a labelled retrieval set exist, and is retrieval evaluated separately from generation?

### RAG-02 Mean reciprocal rank
- **value:** mean of 1/rank of the first relevant chunk (0 if none in the top 20). Use it to judge whether a reranker earns its latency.

### RAG-03 Context precision
- **k/n:** k = retrieved chunks (top `RAG_K`) judged relevant; n = all retrieved chunks.
- **Why it matters:** irrelevant chunks dilute the context and invite wrong answers, so low precision shows up as hallucination later.

### RAG-04 Context recall
- **k/n:** k = required facts (from the golden checklist) present somewhere in the retrieved context; n = required facts.
- **How:** a judge checks each required fact against the concatenated context.

### RAG-05 Faithfulness to retrieved context
- **k/n:** k = answer claims supported by the retrieved context; n = answer claims.
- **How:** decompose into claims, then a judge checks each claim against the context only, not world knowledge. Also report the share of answers with at least one unsupported claim in `notes`.

### RAG-06 Answer relevance
- **k/n:** k = answers that address the question asked; n = answers.

### RAG-07 Citation accuracy
- **k/n:** k = citations whose cited source actually contains the cited claim; n = citations.
- **How:** first check deterministically that each cited ID exists in the context (catches invented sources), then have a judge check that the claim appears in the cited chunk.

### RAG-08 Correct abstention
- **k/n:** k = unanswerable questions where the system declined or said it does not know; n = unanswerable questions.
- **Also report** the false abstention rate on answerable questions in `notes`. A system that refuses everything passes RAG-08 and fails users.

### RAG-09 Index freshness lag
- **value:** days between a source document changing and that change being searchable, taken as the worst case over the sample.
- **How:** change or add a test document at the source, then time how long until retrieval returns it. Otherwise compute from the manifest: max(index time minus source modified time) over documents changed in the window.
- **Design question:** is there an incremental sync with deletion handling? Deleted source documents still being retrievable is a common, serious gap.

## Diagnosis: retrieval failure or generation failure?

Put this table in the findings, using RAG-04 and RAG-05 (plus OQ-01 from M1, if available):

| RAG-04 recall | RAG-05 faithfulness | Diagnosis | Fix first |
|---|---|---|---|
| Low | High | Retrieval is the bottleneck; the model is honest about bad context | Chunking (size, overlap, layout-aware parsing of tables and PDFs), hybrid BM25 + vector search, query rewriting, reranker, metadata filters |
| High | Low | Generation is the bottleneck; good context, model drifts from it | Grounding instructions, citation requirement, smaller context, stronger model, lower temperature |
| Low | Low | Both | Fix retrieval first, then re-measure generation |
| High | High but OQ-01 low | The corpus itself is wrong or stale, or the references are wrong | Audit the source documents and RAG-09 |

Also slice RAG-01 and RAG-04 by document type (PDF, table, web page, slide) and by question type (lookup, multi-hop, comparison, aggregation). Multi-hop and table questions usually fail first.

## Production checks (demo traps)

- **Corpus scale.** Test on the full production corpus, not a 50-document demo index. Precision drops as the corpus grows because near-duplicates and distractors appear.
- **Real queries.** Sample at least `GEN_MIN_N` real user queries from logs. They are shorter, vaguer and more misspelled than written test questions.
- **Updates and deletions.** Run the RAG-09 probe, and also delete a test document and confirm it stops being retrieved.
- **Version pinning.** Record the embedding model and index version in `config_under_test`. Changing the embedding model invalidates the index and these results.

## Hand-back checklist

- [ ] `results/M2.json` has all nine metrics (measured, DESIGN, NOT_TESTED or N_A).
- [ ] Retrieval and generation are scored separately, and the diagnosis table is in the findings.
- [ ] Slices by document and question type are in `notes`.
- [ ] Judge kappas are recorded.

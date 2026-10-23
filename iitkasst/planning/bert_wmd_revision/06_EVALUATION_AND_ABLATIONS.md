# Evaluation and Ablations

## Immediate reviewed benchmark

Create `evaluation/wmd_immediate_questions.jsonl` with 20 cases. The table proposes questions and the evidence review required; it does not assert unverified answer text. A human must open the cited official source/chunk, assign exact gold chunk IDs and 0–3 relevance grades, and mark whether the corpus can answer before metrics run.

| ID | Question/turns | Category | Gold/behavior review required |
|---|---|---|---|
| P01 | What B.Tech programmes are available? | Exact/list | Review the complete “Available B.Tech Programmes” section; ensure completeness. |
| P02 | Which undergraduate computing degrees can applicants choose? | Semantic paraphrase | Review the same programme-list evidence and whether “computing” intentionally narrows it. |
| P03 | What is the B.Tech CSE programme about? | Programme description | Review current CSE programme page section. |
| P04 | Compare the CSE and ECE programmes. | Multi-programme | Review one comparable official description per programme; otherwise expected behavior is partial limitation/abstention. |
| P05 | What are the eligibility requirements for PhD admission? | Eligibility | Determine whether current corpus contains authoritative PhD eligibility; abstain if absent/incomplete. |
| P06 | Which e-M.Tech disciplines are offered? | Postgraduate list | Review current e-M.Tech official evidence; abstain if the active corpus lacks it. |
| A01 | How do I apply for B.Tech in 2026? | Admission procedure | Review UG Admission 2026 process evidence and applicable route. |
| A02 | When is the final deadline to apply for B.Tech in 2026? | Deadline/missing | Verify whether an authoritative deadline exists; portal “FINAL SUBMIT” is forbidden unless it states the date. |
| A03 | What documents are required for JoSAA reporting? | Route documents | Review JoSAA/CSAB checklist only. |
| A04 | What documents are required for DASA reporting? | Route documents | Review DASA checklist only. |
| A05 | How many mandatory portal steps are there? | Portal/count | Review portal guide statement and exact scope. |
| A06 | When do classes commence for the 2026 batch? | Date | Review current dated official evidence and year metadata. |
| F01 | What is the first-semester B.Tech tuition fee in 2026? | Fee component | Review exact tuition row, semester and year—not total charges. |
| F02 | First ask F01, then: How much is that? | Follow-up | Same gold as F01; verify inherited semester/component. |
| F03 | First ask F01, then: What about the second semester? | Slot replacement | Review second-semester tuition row; current turn must replace semester only. |
| F04 | What is the total cost across all eight semesters? | Aggregate/incomplete | Review whether corpus contains all required components/authoritative total; otherwise abstain. |
| S01 | Which authorities provide scholarships? | Scholarship | Review official scholarship authority passage; do not infer award amounts. |
| X01 | Which companies recruited students last year? | Placement/missing | Current corpus inventory has no placement chunks; expected abstention unless corpus state changes before freeze. |
| C01 | What items should first-year students obtain for hostel rooms? | Facilities/list | Review complete hostel-item section and scope. |
| C02 | First ask P03, then: What are the hostel facilities? | New topic reset | Review facility evidence; CSE scope must not suppress or contaminate it. |

Store per case: `id`, `family_id`, turns, expected behavior (`answer|abstain|clarify`), gold chunk IDs with grades, forbidden chunk IDs/claims, programme/year/route scope, reviewer, review date, corpus hash, and notes. P02/P01 and F01/F02 are same-family and cannot be split across future dev/test claims.

## Systems under comparison

### Standalone candidate-generation comparison

Use the same frozen corpus and metadata eligibility universe:

1. BM25 alone, top 10.
2. BGE alone, top 10.
3. Existing BM25+BGE RRF, top 10.
4. BERT weighted-centroid cosine over every eligible chunk, top 10.
5. BERT exact WMD over every eligible chunk, top 10.

At 98 chunks, full eligible-corpus WMD is plausible for an offline experiment but must be timed. Systems 4–5 share the exact same preprocessing, token vectors, document caps, and eligibility constraints. They do not use RRF candidates.

### Shared-pool reranking comparison

Generate exactly the top 15 eligible RRF candidates once per query, then compare:

6. Original RRF order.
7. RRF pool reranked by BERT centroid cosine.
8. RRF pool reranked by exact WMD.
9. Optional rank-RRF of BM25 rank and WMD rank over that pool.

These systems have identical Recall@15 by construction. Report MRR@10, nDCG@10, Recall@5/10 within the pool, and top-k precision. Do not claim WMD “retrieval recall” improved if it only reordered a fixed candidate set.

## Metrics

- Recall@5 and Recall@10 using directly relevant gold evidence.
- MRR@10 for the first grade-3 passage.
- nDCG@10 with grades 0–3.
- eligibility false-exclusion count.
- mean/median/p95 baseline retrieval, query BERT encoding, per-candidate WMD, full rerank, and total latency.
- peak process RSS and, for BERT encoding, peak CUDA allocated memory.
- solver failure/nonfinite/empty-distribution counts.

Evaluate final answers separately: correct, complete, irrelevant, unsupported, appropriate abstention, unnecessary abstention, and citation support. The WMD CLI initially does not generate an answer, so retrieval gains must not be reported as answer gains.

## Immediate protocol

1. Freeze Git SHA, corpus hash, index manifests, WMD model/cache manifest, config, hardware, and dependency versions.
2. Human-review all 20 cases before running metrics.
3. Use 12 cases as a development/smoke subset and hold eight untouched for a one-time presentation report where possible, grouped by family.
4. Do not tune vector normalization, layer, token caps, candidate count, or fusion on the eight held cases. The frozen design in this plan is the default.
5. Save raw per-query rankings and timings, including failures.
6. Report exact counts; the set is too small for broad accuracy claims.

## Mathematical validation

Tests independent of BERT must establish:

- identity: same supports/masses have distance approximately zero;
- symmetry: `WMD(a,b)≈WMD(b,a)` for symmetric Euclidean costs;
- nonnegativity;
- a hand-computable 2×2 transport result;
- repeated-token TF changes mass correctly;
- Euclidean cost-matrix shape and diagonal behavior;
- empty/nonfinite/mismatched mass inputs fail explicitly.

Then BERT integration checks dimension 768, pinned revision, layer selector, normalization norm≈1, deterministic repeated CPU output within tolerance, and cache round trip.

## Larger post-presentation evaluation

Use the previously designed 100–150 independently authored/adjudicated collection after corpus expansion. Split by question/fact family and freeze the final test. Add ablations in this order:

1. current corpus vs expanded/versioned corpus;
2. flat vs hierarchical/table-aware representation;
3. existing vs typed query/dialogue state;
4. BM25, BGE, RRF;
5. centroid and exact WMD standalone;
6. RRF→WMD;
7. metadata filters on/off;
8. operation-aware evidence contracts;
9. optional cross-encoder, only after the preceding work.

No RAG ablation is planned.

## Go/no-go criteria

WMD remains experimental unless all are true on reviewed data:

- mathematical and cache tests pass on CPU and the target CUDA environment;
- zero metadata/citation loss;
- no baseline regression when disabled;
- all distances are finite and stable;
- warmed top-15 WMD added p95 is acceptable for its intended interface (target ≤2 seconds for optional interactive use; CLI may be slower if reported);
- nDCG@10 or MRR@10 improves over original RRF on a future held-out set without Recall@10 or safety regression;
- final-answer quality improves if production selection is ever integrated.

If WMD loses, report it as a completed paper-inspired experiment and retain BM25+BGE+RRF in production.


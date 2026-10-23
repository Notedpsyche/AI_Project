# Evaluation Strategy

## Objective

Build an evaluation that can distinguish corpus absence, retrieval failure, selection failure, unsupported generation, unnecessary abstention, and dialogue-state failure. The existing 45 questions remain a **development regression set**. They must never again be presented as independent accuracy.

## Evaluation collection

Create approximately 140 question cases after the source manifest and corpus version are frozen:

| Case type | Target count | Purpose |
|---|---:|---|
| Answerable single-turn | 70 | Core admissions, programmes, eligibility, fees, scholarships, placements, departments, facilities. |
| Answerable conversational/multi-part | 20 | Slot inheritance, clarification, topic switching, comparisons, totals. |
| Missing from corpus | 20 | Measure correct abstention, not retrieval recall. |
| Ambiguous / clarification required | 15 | Programme, route, year, semester, or fee-component ambiguity. |
| Outdated or conflicting sources | 10 | Verify temporal/source-priority behavior. |
| Adversarial/off-topic | 5 | Prompt injection, unsupported advice, non-college questions. |

At least 20–25 cases should be multi-turn and at least 15–20 should require more than one evidence item or more than one answer operation.

## Independence and split protocol

1. Freeze and hash the official-source manifest and parsed corpus first.
2. Have at least two people who did not implement the system independently author or review questions from applicant scenarios and official sources.
3. Group questions by fact and paraphrase family before splitting. No paraphrase, same table row, or near-duplicate fact may cross development/test boundaries.
4. Use training/development data for intent rules, reranker training, thresholds, and error-driven changes.
5. Freeze one final test set once. Do not inspect per-question test outcomes during development. If the test is used to change code, relabel it as development and create a new untouched test.
6. Adjudicate disagreements and retain annotator identities, timestamps, source versions, and rationale.

The current `evaluation/independent_questions.jsonl` is renamed conceptually—not necessarily immediately on disk—as a development regression asset because implementation was tuned against it.

## Annotation schema

Each case should contain:

```json
{
  "id": "fees-total-001",
  "family_id": "btech-2026-eight-semester-total",
  "turns": [{"role": "user", "content": "..."}],
  "expected_behavior": "answer|clarify|abstain",
  "scope": {
    "intent": "fees",
    "operation": "aggregate_total",
    "programmes": ["B.Tech"],
    "admission_year": 2026,
    "semesters": [1,2,3,4,5,6,7,8]
  },
  "gold_evidence": [{"chunk_id": "...", "grade": 3}],
  "required_facts": [{"field": "total", "value": "...", "source_id": "..."}],
  "forbidden_claims": ["..."],
  "notes": "Why this source/version is authoritative"
}
```

Passage relevance should use a 0–3 scale: 0 unrelated, 1 same broad topic, 2 partially answers, 3 directly and sufficiently answers. Gold evidence must identify version/route/programme, not just matching text.

## Metrics

### Retrieval

- Recall@5 and Recall@10 using grade ≥2 and separately grade 3.
- MRR@10 for the first directly answering passage.
- nDCG@10 using graded relevance.
- programme/route/year source correctness.
- candidate-set exclusion rate: cases where a hard filter removes all gold evidence.

### Evidence selection

- evidence precision/recall at selected `k`;
- complete-evidence-set rate for totals, comparisons, lists, and multi-part questions;
- unsupported selection rate;
- correct version/route rate.

### Final behavior

- fully correct and fully supported answer rate;
- partially correct rate;
- irrelevant answer rate;
- unsupported factual claim rate, measured at claim level;
- correct abstention and unnecessary-abstention rates;
- correct-clarification and unnecessary-clarification rates;
- conversational slot-inheritance accuracy;
- topic-reset accuracy;
- citation correctness and citation completeness.

If an LLM is later tested, add claim faithfulness, citation entailment, numeric fidelity, and output-schema validity. A citation is not “supported” merely because its sentence is copied from a selected passage; it must entail the claim and answer the requested attribute.

### Performance and reproducibility

Report cold startup separately from warmed query latency. Measure warmed p50/p95 for scope resolution, sparse retrieval, dense retrieval, reranking, answer construction, and end-to-end response. Record CPU/GPU/RAM/VRAM, operating system, model revision, corpus and manifest hashes, Git commit, config hash, random seed, and exact command.

Use bootstrap confidence intervals for aggregate metrics and publish exact numerators/denominators. Small category cells must be shown as counts rather than misleading percentages.

## Fair experiment matrix

All retrieval systems use the same frozen corpus, query set, candidate eligibility policy, and output cutoff.

| Experiment | Purpose |
|---|---|
| BM25 only | Sparse baseline. |
| BGE only | Dense baseline. |
| BM25+BGE RRF | Current retrieval baseline. |
| + structured ingestion | Isolate hierarchy/table improvement. |
| + typed metadata filtering | Isolate scope filtering. |
| + dialogue FSM | Isolate follow-up and clarification behavior. |
| + MiniLM cross-encoder | Small learned reranker. |
| + BGE reranker | Larger reranker challenger. |
| + operation-aware evidence planner | Isolate final correctness/sufficiency. |
| Paper-style centroid/WMD | Academic comparison only. |
| Optional local RAG | Run only after baseline gates pass. |

For rerankers, compare top-10, top-20, and top-30 candidate inputs on development data; choose once, then lock. For WMD/BM25 mixtures, tune interpolation only on development data.

## Proposed acceptance gates

These are recommended gates, not achieved results:

- graded gold-evidence Recall@10 ≥ 90% on the untouched test set, with confidence interval reported;
- at least 85% fully correct and fully supported final behavior;
- zero wrong-year, wrong-route, or wrong-programme answers in designated critical cases;
- zero critical unsupported numeric claims and no more than 1% unsupported factual claims overall;
- ≥90% correct clarification decisions and ≥90% correct conversation inheritance/reset decisions;
- every factual answer has complete claim-level official citations;
- warmed retrieval-only p95 target ≤2.5 seconds on the target laptop; any optional RAG path target ≤5 seconds, with quality taking precedence.

If the corpus cannot support these gates, narrow the advertised scope instead of lowering evidence requirements.

## Regression suites

- **Fast unit suite:** parsers, slot resolver, state transitions, metadata-aware dedupe, evidence contracts, arithmetic, citation validator.
- **Development regression:** current 45 questions plus every fixed bug; allowed for iterative use.
- **Frozen test:** independently authored and never used for implementation decisions.
- **Source-update suite:** version conflicts, supersession, dead links, changed hashes, parser drift.
- **API/UI smoke:** startup from fresh checkout, index-missing errors, health/search/chat schemas, source-link rendering.

Every reported improvement must include raw per-case outcomes and the baseline under identical conditions.


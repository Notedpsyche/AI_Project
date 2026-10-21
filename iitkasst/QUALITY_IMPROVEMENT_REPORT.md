# IIIT Kottayam Assistant — Quality Improvement Report

Date: 9 October 2026

## Executive result

The existing FastAPI, React, BM25, BGE-base, FAISS, and RRF architecture was retained. No generative LLM, external dataset, model fine-tuning, corpus replacement, or frontend redesign was introduced.

The original 45-question audit result was preserved before implementation. The same set was then used as a **development regression set**, not as an independent post-fix accuracy benchmark.

| Measure | Preserved baseline | Final development regression |
| --- | ---: | ---: |
| Strict successes | 17/45 (37.8%) | 45/45 (100.0%) |
| Answerable, correct and complete | 15/36 | 36/36 |
| Irrelevant responses | 21 | 0 |
| Unnecessary abstentions | 4 | 0 |
| Correct abstentions | 2/9 | 9/9 |
| Unsupported answers | 0 | 0 |
| Conversational follow-ups correct | 0/3 | 3/3 |
| Citation support | 39/39 (100%) | 36/36 (100%) |
| Retrieval Recall@5 | 72.2% | 77.8% |
| Retrieval Recall@10 | 77.8% | 83.3% |
| Warm API p50 / p95 | 1.14 s / 1.66 s | 2.02 s / 2.87 s |

The final latency was measured during a heavily loaded validation session and is slower than the preserved baseline. It is recorded rather than hidden and should be remeasured in a clean demo session.

## Files changed in this implementation phase

- `backend/services/college_query.py`
- `backend/services/college_select.py`
- `backend/services/college_answer.py`
- `src/doc2dial_retrieval/search.py`
- `tests/test_college.py`
- `results/college/independent_evaluation.json`
- `results/college/independent_evaluation_api.jsonl`
- `QUALITY_IMPROVEMENT_REPORT.md`

The preserved pre-change artifacts are:

- `results/college/independent_evaluation_baseline.json`
- `results/college/independent_evaluation_api_baseline.jsonl`

## Root causes corrected

### 1. Query understanding was too broad and order-dependent

The resolver recognized broad topics but did not reliably represent the requested programme, task, fee component, semester, document item, or scholarship attribute. Specific programme names could lose to generic programme wording. Admission years could be confused with qualification years. Informal wording and short follow-ups often lacked enough resolved scope.

Changes:

- Specific programme resolution now distinguishes B.Tech specializations, e-M.Tech, and PhD before generic programme names.
- Admission year and qualification/passing year are represented separately.
- Fee components, document items, ordinal/cardinal semesters, admission routes, and underspecified questions are explicit scope fields.
- Added task intents for programme lists/fields/descriptions, portal steps and confirmation, fee totals/components/comparisons, scholarship authorities/support, reporting, orientation, class commencement, laptop requirements, hostel items, transport, and first-year housing.
- Conversational references inherit bounded previous-user context, while explicit programme or admission-year changes start a new scope.
- Common conversational `what's` is normalized to `what is` before both BM25 and dense retrieval. This fixed a measured exact-table-row retrieval miss without replacing either retriever.

### 2. Broad topical relevance was being mistaken for answer relevance

The old selection path could accept an official passage merely because it belonged to the same broad topic. That allowed admission documents to answer programme questions and first-semester summaries to answer later-semester fee questions.

Changes:

- Evidence must now support the requested entity, intent, programme, admission year, route, semester, fee component, or document item.
- Multi-part requests require a sufficient evidence set, not just one loosely related passage.
- Canonical fee-table rows are preferred over pages that mention many unrelated charges.
- Portal confirmation requires both the success confirmation and application-report facts.
- Programme list questions are restricted to structured programme-list sections.
- Missing placement statistics, recruiter evidence, scholarship amounts, department heads, laboratory locations, or hotel details cause abstention instead of a nearby answer.

### 3. Generic sentence extraction could answer the wrong attribute

The previous composer ranked sentences mostly by surface overlap and often returned one partial sentence. It could not safely compose lists, comparisons, multiple fee cells, named document requirements, or multi-part portal answers.

Changes:

- Added task-aware, extractive composition for lists, fee totals/components/comparisons, document items, portal steps/confirmation, dates, programme descriptions/fields, scholarship authorities/support, and hostel requirements.
- Fee answers quote only the requested component and semester cells, preventing unrelated amounts from leaking into the answer.
- Specific programme-attribute questions select the sentence matching the requested attribute; generic programme descriptions may use an overview plus a named-fields sentence.
- Every displayed claim remains an exact substring of its cited evidence. No facts are synthesized or invented.

## Corrected examples

### B.Tech admission procedure

Before: the assistant abstained even though the official 2026 admission source was retrieved.

After:

> For B.Tech (admission 2026): admission is based on JEE Main through JoSAA/CSAB counselling, followed by institute admission-data entry and final submission through the official portal.

The live response cites the B.Tech admission procedure and the 2026 admission portal source.

### Available programmes

Before: a category-certificate document requirement was returned for “what are the available courses”.

After: the query resolves to `programmes_list`; document and fee chunks are ineligible, and the answer is extracted from the structured B.Tech/e-M.Tech/PhD programme sections.

### Semester-specific fee

Before: “mess advance in semester three” returned first-semester summaries and the wrong amount.

After:

> Mess Advance. Third Semester: 37,250/-.

Only the requested fee component and semester cell are cited.

### Conversational follow-up

Before: all 3 audited follow-ups failed.

After: all 3 retain the bounded previous topic/programme/year when the new question is referential, including “And the next semester?” and “What does it concentrate on in the later semesters?”. Explicit new programme/year questions do not inherit the old scope.

## Verification performed

- `uv run pytest -q` — **58 passed**
- `uv run ruff check .` — **passed**
- `npm run build` — **passed**; Vite production bundle generated
- `uv run python src/smoke_college.py` — **20/20 expected behaviours passed**
- Live `GET /api/health` — **ok**
- Live `POST /api/chat` for B.Tech 2026 admission — answered with 2 official evidence items
- Full 45-case development regression — **45/45 strict successes**
- Citation verification — **36/36 answered cases fully supported**

The backend was restarted after the final code changes and is running the updated code and existing indexes at `http://127.0.0.1:8000`.

## Remaining limitations and failure categories

There are no remaining failures in the 45-case development regression, but this does **not** establish independent real-world accuracy.

1. The 45 cases guided development. A new, independently authored and human-reviewed held-out set is still required before making an accuracy claim.
2. The current corpus does not contain enough reliable evidence for placement packages/counts/recruiters, scholarship scheme amounts and income limits, current department heads, laboratory buildings, or nearby hotel prices. The assistant correctly abstains on these categories.
3. Recall@10 is 83.3%, so retrieval still misses some annotated gold chunks. Final answers can pass when an alternative official passage supports the same fact, but retrieval is not solved universally.
4. Answers are deterministic and extractive. They remain conservative and may sound less natural than generated prose.
5. Programme, fee, and admission facts are tied to the local source snapshot. Source collection and index rebuilding are required when official pages change.
6. Latency should be profiled again on an otherwise idle laptop; the final loaded-session p95 was 2.87 seconds.

## Reranking and grounded LLM decision

A learned reranker is not justified for deployment by this result. The measured failures were corrected through scope resolution, eligibility/sufficiency checks, structured table handling, and extractive composition while retaining RRF. A reranker should be reconsidered only with independently judged training/development/test data and a demonstrated held-out ranking gain with no safety regression.

A grounded generative LLM is also not justified as the next correctness fix. The current deterministic path provides exact claim-level citation support and safe abstention. An LLM could later be evaluated only as a presentation layer over already validated evidence, with claim-level support checks and abstention preserved.

## Interpretation

The implementation phase achieved its requested goal on the available development material without replacing the retrieval architecture or weakening evidence requirements. The honest next step is external validation: freeze this implementation, create a new human-authored held-out question set, and report those results separately from the 45-case development regression.

# Implementation Roadmap

## Sequencing principle

The critical path is corpus authority and structure → typed scope/state → evidence contract → fair evaluation → optional ranking/generation experiments. Each milestone is independently reversible and must preserve a runnable baseline.

## Milestone classification and new components

| Milestone | Objective | New component | Classification |
|---|---|---|---|
| 0 | Make the current baseline reproducible. | Trace/result manifest. | Must-have |
| 1 | Ensure every advertised topic has authoritative versioned evidence. | Source-governance schema and coverage matrix. | Must-have |
| 2 | Preserve hierarchy and structured facts. | Parent-child nodes, table/list facts, quality flags. | Must-have |
| 3 | Resolve queries and conversations without losing scope. | Typed slot schema and FSM. | Must-have + paper-inspired |
| 4 | Prevent candidate loss and make retrieval comparable. | Metadata-aware dedupe and constrained/fallback branches. | Must-have |
| 5 | Answer only from complete relevant evidence. | Evidence contracts, answer plans, claim validator. | Must-have |
| 6 | Establish credible performance evidence. | Independent annotation/test protocol. | Must-have |
| 7 | Test learned pairwise ranking. | Feature-flagged cross-encoder adapter. | Optional experiment; deploy only if it wins |
| 8 | Demonstrate paper ranking ideas fairly. | Bounded centroid/WMD experiment. | Academic experiment; not default production |
| 9 | Test synthesis after safety is established. | Validated feature-flagged generator. | Optional; postpone |
| 10 | Make setup and updates reliable. | Operational runbook and clean-setup smoke suite. | Must-have for handoff |

## Milestone 0 — Freeze and instrument the baseline

- **Predicted files:** `evaluation/`, a new trace schema under `backend/services/`, documentation only; no model change.
- **Dependencies/data:** existing 98 chunks, current indexes, current 45-question regression set.
- **Tasks:** snapshot Git/config/corpus/index/model hashes; save raw per-query candidate and rejection traces; relabel current 45 cases as development regression; document the stale `uv run pytest` launcher issue.
- **Risks:** accidental presentation of development results as independent.
- **Evaluation:** reproduce current saved metrics and bounded failures with identical commands.
- **Acceptance:** reproducible baseline bundle includes hashes, timings, raw outcomes, and environment.
- **Rollback:** remove instrumentation path; runtime ranking remains unchanged.

## Milestone 1 — Source inventory and corpus governance

- **Predicted files:** `configs/college_sources.json`, a source schema module, local ignored raw-source directory, source-review documentation.
- **Dependencies/data:** reviewed official B.Tech, e-M.Tech, PhD, fees, scholarship, TPC, calendar, department, facility, hostel, and regulation URLs/PDFs.
- **Tasks:** define authority/version/effective-period fields; review access and redistribution; fetch gently; hash and version sources; mark obsolete/conflicting material.
- **Risks:** inaccessible pages, stale notices, copyright/redistribution uncertainty.
- **Evaluation:** coverage matrix against planned question categories; manual source/version audit.
- **Acceptance:** every advertised category has an authoritative active source or is explicitly out of scope.
- **Rollback:** restore prior manifest and indexes; newly collected local data remains isolated.

## Milestone 2 — Structure-aware ingestion

- **Predicted files:** `src/doc2dial_retrieval/college.py`, new schema/parser helpers, `src/prepare_college.py`, parser fixtures/tests.
- **Dependencies/data:** HTML/PDF parsing libraries already present; add a table/PDF dependency only if a measured extraction gap requires it.
- **Tasks:** preserve heading trees; parse table rows with headers; create atomic facts and completeness groups; distinguish admission/effective/qualification years; attach route metadata; record extraction quality; fix metadata-aware dedupe.
- **Risks:** malformed PDFs/tables and unstable DOMs.
- **Evaluation:** reviewed extraction sample for every document type; exact table/list reconstruction tests.
- **Acceptance:** critical fees/dates/checklists round-trip with correct source, scope, unit, and hierarchy; no replacement characters in reviewed fields.
- **Rollback:** retain the old chunk builder behind a corpus-version switch until migration passes.

## Milestone 3 — Typed scope and dialogue FSM

- **Predicted files:** `backend/services/college_query.py`, new dialogue-state/schema module, `backend/api/schemas.py`, focused tests.
- **Dependencies/data:** normalized programme/route/intent ontology; conversation fixtures.
- **Tasks:** support programme lists and comparisons; separate admission/effective/qualification years; model operations and requested attributes; implement deterministic state transitions, inheritance provenance, reset, and clarification decisions.
- **Risks:** over-inheritance and excessive clarification.
- **Evaluation:** single-turn scope accuracy plus multi-turn inheritance/reset matrix.
- **Acceptance:** all designated programme comparison, year distinction, fee component, follow-up, and new-topic cases resolve correctly without answer code.
- **Rollback:** feature flag routes requests through existing `resolve_scope`.

## Milestone 4 — Retrieval and candidate hygiene

- **Predicted files:** `src/doc2dial_retrieval/retrieval.py`, `search.py`, `backend/services/retrieval_service.py`, `configs/config.yaml`, retrieval tests.
- **Dependencies/data:** rebuilt structured indexes; frozen development judgments.
- **Tasks:** metadata-aware dedupe after scope safety; constrained plus fallback retrieval; equivalent candidate pools; expose complete BM25/dense/RRF traces; tune only development depths and RRF parameters if justified.
- **Risks:** hard filters can reduce recall; trace payloads can add overhead.
- **Evaluation:** BM25, BGE, and RRF at equal depths; filter-exclusion analysis.
- **Acceptance:** no gold evidence lost through dedupe/filtering in critical development cases and Recall@10 improves or remains within uncertainty while wrong-scope candidates fall.
- **Rollback:** configuration switch restores current candidate path.

## Milestone 5 — Generic evidence contract and answer planner

- **Predicted files:** `backend/services/college_select.py`, `college_answer.py`, new `evidence_contract.py`/`answer_plan.py`, API schemas and tests.
- **Dependencies/data:** atomic facts and typed scopes.
- **Tasks:** replace default-true sufficiency with operation schemas; build plans for lists, counts, totals, comparisons, dates, procedures, and multi-part questions; deterministic arithmetic; claim-level citation validation; remove source facts embedded in code.
- **Risks:** initially more abstentions where corpus coverage is incomplete.
- **Evaluation:** selection completeness, claim support, answer correctness, and abstention error categories.
- **Acceptance:** confirmed total/comparison/PhD/deadline failures behave correctly; zero unsupported critical numeric/date claims in development safety cases.
- **Rollback:** preserve existing extractive composer as an explicit fallback for simple lookup operations only.

## Milestone 6 — Independent evaluation freeze

- **Predicted files:** versioned annotation schemas and split manifests under `evaluation/`; evaluation runner/report templates.
- **Dependencies/data:** approximately 140 adjudicated cases from independent reviewers.
- **Tasks:** family grouping, train/dev/test split, source-version binding, graded evidence, required facts, behavior labels, bootstrap intervals, hardware/timing capture.
- **Risks:** label leakage, weak adjudication, undersized critical categories.
- **Evaluation:** inter-annotator agreement and duplicate/family leakage checks.
- **Acceptance:** untouched test hash is sealed; development and test access procedures documented.
- **Rollback:** none needed; this is an evaluation asset, not runtime behavior.

## Milestone 7 — Cross-encoder experiment

- **Predicted files:** optional reranker service/config, experiment runner, model manifest; no default deployment at first.
- **Dependencies/data:** MiniLM model, optionally BGE reranker, judged query-passage pairs; model artifacts ignored by Git.
- **Tasks:** rerank top 10/20/30 after safety filters; benchmark GPU/CPU; compare pretrained and optionally small learned calibration/ranking approaches using train/dev only.
- **Risks:** latency/VRAM competition, overfitting, misleading uncalibrated scores.
- **Evaluation:** nDCG/MRR, complete evidence-set rate, final answers, p50/p95, critical regressions.
- **Acceptance:** deploy only if held-out ranking/final correctness improves without any wrong-year/route or unsupported-answer regression and latency meets the chosen gate.
- **Rollback:** disable feature flag and use RRF order.

## Milestone 8 — Paper-inspired WMD experiment

- **Predicted files:** separate experiment module/report; production code untouched unless gate passes.
- **Dependencies/data:** Python Optimal Transport; chosen token embeddings; same frozen candidate sets.
- **Tasks:** implement centroid cosine, WMD, and BM25/WMD interpolation; bound to top candidates; tune alpha on development only.
- **Risks:** quadratic/transport cost, tokenization sensitivity, no production gain.
- **Evaluation:** fair same-pool retrieval metrics and local latency versus BM25, BGE, RRF, and cross-encoder.
- **Acceptance:** publish as a negative or positive result; production adoption requires statistically credible benefit and acceptable p95.
- **Rollback:** remove optional experiment environment; no runtime effect.

## Milestone 9 — Optional controlled RAG

- **Predicted files:** feature-flagged generator adapter, prompt/schema, claim validator, model manifest, safety tests.
- **Dependencies/data:** local quantized 4B model or separately approved hosted provider; completed evidence plans.
- **Tasks:** generate only from plan; require evidence IDs; validate claims/numbers; benchmark deterministic versus generated answers.
- **Risks:** hallucination, latency, VRAM exhaustion, harder reproducibility.
- **Evaluation:** blinded answer quality, claim faithfulness, citation completeness, schema failures, latency.
- **Acceptance:** only retain if it improves multi-source readability/completeness with zero safety regression and meets hardware limits.
- **Rollback:** turn feature off; deterministic composer remains canonical.

## Milestone 10 — Deployment hardening and handoff

- **Predicted files:** `README.md`, setup scripts/config validation, API/UI smoke tests, operational runbook.
- **Dependencies/data:** locked dependencies, source/index build commands, supported-platform notes.
- **Tasks:** fresh-clone setup test; explicit missing/stale-index errors; update/rebuild procedure; source-link health checks; frontend rendering of clarify/abstain/comparison states.
- **Risks:** Windows path/launcher drift and undocumented local artifacts.
- **Evaluation:** clean-machine or clean-environment rehearsal and end-to-end smoke test.
- **Acceptance:** a new user can collect permitted sources, build indexes, run both services, and reproduce the public development report without hidden files.
- **Rollback:** release previous tagged package and index manifest.

## Dependency policy

No dependency is added because it is fashionable or present in the paper. Every new package must have a measured need, compatible license, pinned version, artifact size, and removal path. Model weights and collected source content remain untracked.


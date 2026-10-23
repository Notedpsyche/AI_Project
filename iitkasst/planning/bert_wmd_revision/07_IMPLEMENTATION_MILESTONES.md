# Implementation Milestones

Every task below leaves the default application runnable. Commands are executed from `iitkasst/` in PowerShell. Generated reports/caches are local artifacts unless explicitly designated as reviewed source files.

## Stage 1 — Protect the baseline

### Task 1.1 — Capture reproducible baseline

- **Objective:** create a rollback reference before code changes.
- **Prerequisites:** current checkout and indexes.
- **Files created:** generated `evaluation/wmd_runs/baseline_<timestamp>.json`; no source modification.
- **Inputs/outputs:** Git/config/corpus/index/dependency state and current smoke responses → one immutable local record.
- **Tasks:** record `git status`, `git rev-parse HEAD`, hashes of config/chunks/index manifests, Python/GPU/package versions, test/Ruff results, health payload, and five known query responses/traces.
- **Invariants:** preserve all pre-existing untracked files; record dirty status; no index rebuild.
- **Commands:** `git status --short`; `git rev-parse HEAD`; `uv run python -m pytest -q`; `uv run ruff check .`; API smoke command documented from current run instructions.
- **Proceed if:** 58-test baseline (or exact current count) and app behavior are reproducible; discrepancies are recorded before modification.
- **Rollback:** none; read-only capture.
- **Effort/risk:** 30–60 minutes / low.

## Stage 2 — Fix critical correctness defects

### Task 2.1 — Close evidence support by default

- **Files:** modify `college_query.py`, `college_select.py`; create `tests/test_college_reliability_regressions.py`.
- **Functions:** extend `intent_in`; add intent support dispatch/predicates; modify `supports_request` and `evidence_set_sufficient`.
- **Input/output:** `QueryScope` + candidate row(s) → supported evidence or empty selection.
- **Invariant:** unknown/general evidence is never sufficient; all previously supported intents are explicit.
- **Dependencies:** none.
- **Tests:** PhD eligibility, application deadline, unknown intent, known admission process/programme list.
- **Verify:** `uv run python -m pytest -q tests/test_college_reliability_regressions.py tests/test_evidence_selection.py`; full suite and Ruff.
- **Proceed if:** irrelevant cases abstain and existing regressions remain green.
- **Rollback:** revert only query/selector changes and test expectations; no artifacts affected.
- **Effort/risk:** 1.5–2.5 hours / medium.

### Task 2.2 — Preserve multi-programme scope end to end

- **Files:** modify `college_query.py`, `college_select.py`, narrow `college_answer.py` branch, regression tests.
- **Functions/classes:** `programmes_in`; extend `QueryScope`; update `resolve_scope`, `eligible`, `select_evidence`, `evidence_set_sufficient`, `grounded_answer` comparison branch.
- **Input/output:** question with zero/one/multiple programmes → ordered tuple plus compatibility primary; complete per-programme cited extracts or abstention.
- **Invariant:** every requested programme has selected supporting evidence before comparison output.
- **Dependencies:** Task 2.1.
- **Tests:** CSE/ECE parse, candidate retention, incomplete/complete comparison, singular compatibility.
- **Verify:** focused test, full suite, one API debug trace.
- **Proceed if:** both targets survive and response schema remains compatible.
- **Rollback:** remove tuple path; `programme_in` wrapper preserves old behavior.
- **Effort/risk:** 1.5–2.5 hours / medium.

### Task 2.3 — Inherit compatible typed slots

- **Files:** modify `college_query.py` and regression tests.
- **Functions:** slot parser/helper, `resolve_scope`; extend `QueryScope.inherited_slots`.
- **Input/output:** current turn + prior messages → explicit/inherited programme, year, route, semesters, components, document items.
- **Invariant:** explicit current slots win; incompatible new topic/programme/year resets old slots.
- **Dependencies:** Task 2.2 schema.
- **Tests:** “How much is that?”, second-semester replacement, online/document follow-up, new-topic reset.
- **Verify:** focused and full suite plus debug scope output.
- **Proceed if:** follow-ups pass and designated reset cases inherit nothing incompatible.
- **Rollback:** revert helper/field; old resolver remains available in Git.
- **Effort/risk:** 1–2 hours / medium.

### Task 2.4 — Make deduplication metadata-sensitive

- **Files:** modify `retrieval.py`; extend `tests/test_search.py` or reliability test file.
- **Functions:** `_scope_signature`, `_duplicate_evidence`, `dedupe_results`.
- **Input/output:** ranked `SearchResult` list → stable list with only scope-compatible duplicates collapsed.
- **Invariant:** different programme/year/route/topics/conflict state cannot deduplicate one another.
- **Dependencies:** none; can be implemented in parallel with Tasks 2.1–2.3 but merged after shared tests.
- **Tests:** route/year/programme survival and same-scope collapse.
- **Verify:** focused search tests, full suite, Ruff.
- **Proceed if:** rank/score fields are unchanged for surviving rows.
- **Rollback:** revert one module; indexes are unaffected.
- **Effort/risk:** 45–90 minutes / low.

### Task 2.5 — Reliability integration gate

- **Files:** no new implementation; save local Stage 2 results.
- **Tests/commands:** full pytest, Ruff, backend health/search/chat smoke, current 45-case development runner.
- **Invariant:** no claim that the 45 cases are independent accuracy.
- **Proceed if:** no regression from baseline and four new categories pass.
- **Rollback:** revert Stage 2 tasks individually in reverse order.
- **Effort/risk:** 45–90 minutes / low.

## Stage 3 — Implement BERT + WMD

### Task 3.1 — Dependency preflight and lock update

- **Files:** `pyproject.toml`, `uv.lock`.
- **Dependencies:** `transformers>=5.19,<6`, `POT==0.9.7`; existing PyTorch/NumPy/SciPy.
- **Tasks:** run `uv add`; import versions; run a 2×2 `ot.emd2` calculation; do not download BERT yet.
- **Invariant:** existing torch CUDA source remains unchanged; POT exact solver returns expected zero.
- **Verify:** import command, tiny calculation, full tests.
- **Proceed if:** Windows resolution/import succeeds and lock diff contains only expected dependency effects.
- **Rollback:** restore `pyproject.toml` and `uv.lock` from pre-task state; `uv sync`.
- **Effort/risk:** 30–60 minutes / medium due Windows wheel compatibility.

### Task 3.2 — Implement preprocessing and measures

- **Files:** new `wmd/preprocessing.py`, `representation.py`, config, tests.
- **Functions/classes:** `WmdPreprocessor`, `build_query_measure`, `build_document_measure`, `collect_vocabulary`.
- **Input/output:** text/chunk → bounded terms/counts/masses.
- **Invariant:** deterministic shared preprocessing; query≤32, document≤64; mass sums to one.
- **Dependencies:** no model load.
- **Tests:** normalization, abbreviations, numbers, repeats, empty text, field caps.
- **Verify:** offline unit tests and Ruff.
- **Proceed if:** identical input yields byte-equivalent serialized measure.
- **Rollback:** remove isolated new files/config.
- **Effort/risk:** 1–1.5 hours / low.

### Task 3.3 — Implement exact transport core

- **Files:** new `wmd/distance.py`, `tests/test_wmd_distance.py`.
- **Functions:** `ground_cost`, `exact_wmd`; typed errors.
- **Input/output:** masses/vector matrices → finite nonnegative float.
- **Invariant:** Euclidean ground metric, exact `ot.emd2`, float64 solver inputs; no BERT dependency.
- **Tests:** identity, symmetry, hand calculation, mass/nonfinite/empty validation.
- **Verify:** `uv run python -m pytest -q tests/test_wmd_distance.py`.
- **Proceed if:** all deterministic mathematical tests pass on CPU.
- **Rollback:** remove isolated module/test; baseline unaffected.
- **Effort/risk:** 1 hour / low-medium.

### Task 3.4 — Implement pinned BERT word encoder

- **Files:** new `wmd/encoder.py`, model-marked integration test.
- **Class:** `BertWordEncoder(model_id, revision, device, batch_size)` with lazy load and CPU retry.
- **Input/output:** unique words → normalized float32 `[n,768]`, rejected-term report, model metadata.
- **Invariant:** pinned revision, layer `hidden_states[-2]`, `[CLS]`, inference mode, deterministic ordering.
- **Dependencies:** cached/downloaded model becomes available at this task only.
- **Tests:** fake unit boundary plus marked real-model dimension/norm/repeatability tests.
- **Verify:** model-marked CPU test, then CUDA test and peak memory capture.
- **Proceed if:** actual revision/dimension/layer metadata match config and values are finite.
- **Rollback:** delete local Hugging Face artifact if desired via its documented cache management separately; source module is isolated. Never delete broad caches blindly.
- **Effort/risk:** 1–2 hours plus first download / medium.

### Task 3.5 — Implement strict embedding cache

- **Files:** new `wmd/cache.py`, `src/build_wmd_cache.py`, cache tests, `.gitignore` update.
- **Functions/classes:** `CacheManifest`, `build_cache`, `load_cache`; atomic staging directory.
- **Input/output:** chunks/config/encoder → four local artifacts; artifacts → validated memory-mapped lookup.
- **Invariant:** any model/corpus/preprocessor/shape mismatch fails closed; interrupted build never replaces valid cache.
- **Tests:** fake-encoder builds, manifest mismatch, token-row alignment, atomic failure.
- **Verify:** unit tests; real cache build; rerun build yields same vocabulary/corpus/config identities.
- **Proceed if:** manifest validates and artifacts remain untracked.
- **Rollback:** remove only the exact `indexes/college_bert_wmd` generated directory after verifying path; baseline indexes untouched.
- **Effort/risk:** 1.5–2 hours / medium.

### Task 3.6 — Implement WMD ranker and CLI

- **Files:** new `wmd/ranker.py`, `fusion.py`, `src/run_wmd_experiment.py`, tests.
- **Functions/classes:** `WmdReranker.rerank`, optional `rank_fuse_bm25_wmd`, CLI `main`.
- **Input/output:** effective query + top-15 eligible RRF dictionaries → ranked metadata-preserving rows and timings.
- **Invariant:** default candidate limit 15; ascending WMD; failure cannot alter baseline; no backend import of WMD.
- **Tests:** fake distance/encoder ranking, limit, ties, failures, metadata; marked end-to-end CLI schema.
- **Verify:** unit suite, model suite, three demo commands.
- **Proceed if:** source URLs/IDs match baseline candidates and repeat rankings are stable.
- **Rollback:** remove isolated command/package additions; baseline untouched.
- **Effort/risk:** 1.5–2.5 hours / medium.

## Stage 4 — Benchmark and demonstrate

### Task 4.1 — Review immediate benchmark

- **Files:** create and human-complete `evaluation/wmd_immediate_questions.jsonl`.
- **Input/output:** proposed 20 prompts + current official chunks → adjudicated behavior/gold IDs.
- **Invariant:** no fabricated answers; corpus hash bound; family grouping recorded.
- **Dependencies:** Stage 2 stable corpus and IDs.
- **Tests:** schema validator; every answer case has at least one reviewed gold ID; missing cases have rationale.
- **Proceed if:** all labels are human-verifiable.
- **Rollback:** keep draft out of reported metrics until reviewed.
- **Effort/risk:** 1.5–3 hours / medium human bottleneck.

### Task 4.2 — Implement and run comparison

- **Files:** `src/evaluate_wmd.py`, evaluation tests, generated JSON/Markdown under ignored runs.
- **Systems:** BM25, BGE, RRF, centroid, standalone eligible-corpus WMD, RRF→WMD, optional rank fusion.
- **Invariant:** same corpus/eligibility/cutoffs; standalone and shared-pool results separated.
- **Tests:** metric fixtures and runner schema.
- **Commands:** `uv run python src/evaluate_wmd.py --questions evaluation/wmd_immediate_questions.jsonl --config configs/wmd_experiment.yaml --output evaluation/wmd_runs/presentation`.
- **Proceed if:** raw outcomes and failures accompany every summary; no final-set tuning.
- **Rollback:** delete exact generated run directory only; code remains experimental.
- **Effort/risk:** 2–3 hours / medium.

### Task 4.3 — Presentation rehearsal and freeze

- **Tasks:** run offline-cache demo, record exact commands/timings, exercise fallback, verify main backend/frontend separately, prepare the 2×2 transport explanation.
- **Acceptance:** baseline demo works even with WMD cache renamed/unavailable; WMD CLI either works live or has an honest recorded fallback.
- **Rollback:** set WMD disabled/remove experimental process from live demo.
- **Effort/risk:** 1 hour / low.

## Stage 5 — Post-presentation work

### Task 5.1 — Corpus and hierarchy

Expand reviewed official sources; add version/effective period; parse heading trees/tables/atomic fee facts; rebuild indexes only under a new corpus manifest. Acceptance: reviewed extraction fixtures and coverage matrix.

### Task 5.2 — Full dialogue/evidence architecture

Replace bridge inheritance with typed FSM; implement operation-aware answer plans, totals/comparisons, and claim-level citations; remove embedded source facts. Acceptance: critical behavior suite and explicit clarification/abstention states.

### Task 5.3 — Independent evaluation

Create 100–150 independently authored/adjudicated cases and frozen family split. Evaluate corpus/query/retrieval/WMD/evidence ablations. Acceptance: raw results, confidence intervals, no leakage.

### Task 5.4 — Production WMD decision

Only if held-out ranking and final-answer quality improve with acceptable p95/memory, add an optional disabled-by-default backend adapter and backward-compatible debug field. Otherwise retain the CLI experiment as the paper implementation. RAG remains prohibited.

## Parallel work

- Task 2.4 can run alongside 2.1–2.3 because it touches retrieval internals, but merge/test after all scope changes.
- Tasks 3.2 and 3.3 can run in parallel after dependency preflight because neither needs BERT weights.
- Human review for Task 4.1 can begin after Stage 2 IDs are stable while Tasks 3.4–3.6 proceed.
- Cache build depends on preprocessing, encoder, and manifest implementation; benchmark depends on all Stage 3 tasks.


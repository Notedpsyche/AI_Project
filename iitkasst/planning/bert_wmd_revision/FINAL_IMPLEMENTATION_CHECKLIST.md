# Final Implementation Checklist

## Frozen technical contract

- [ ] Preserve BM25 + BGE-base + FAISS + RRF as the default path.
- [ ] Use `google-bert/bert-base-uncased` revision `86b5e0934494bd15c9632b12f734a8a67f723594`.
- [ ] Encode vocabulary words independently and use layer-11 `[CLS]` (`hidden_states[-2][:,0,:]`), L2-normalized float32.
- [ ] Compute real exact WMD with float64 term-frequency marginals, Euclidean ground cost, and POT `ot.emd2`.
- [ ] Rerank at most 15 eligible RRF candidates for the presentation path.
- [ ] Represent documents with title 12 + leaf heading 20 + passage 32 normalized token occurrences.
- [ ] Keep WMD experimental, lazy, isolated, and disabled in the web application.
- [ ] Do not implement RAG, generative answering, fine-tuning, new corpus collection, index rebuilding, or frontend changes in Stages 1–4.

## FIRST CODING TASK

Complete this immediately after implementation is authorized; no further design discussion is needed.

### A. Protect the baseline

1. From `C:\Users\Saivarad KG\Documents\AI project\iitkasst`, capture:

```powershell
git status --short
git rev-parse HEAD
Get-FileHash configs/config.yaml -Algorithm SHA256
Get-FileHash data/processed/chunks.jsonl -Algorithm SHA256
Get-Content indexes/college_bge_base/build.json
uv run python -m pytest -q
uv run ruff check .
```

2. Save the exact outputs and five current API/debug responses under a timestamped, ignored `evaluation/wmd_runs/baseline_*` artifact. Do not alter or remove current untracked files.

### B. Implement the first reliability fix atomically

- Create `tests/test_college_reliability_regressions.py`.
- Add tests proving:
  - PhD eligibility cannot be supported by B.Tech admission-procedure text;
  - an application deadline cannot be supported by portal “FINAL SUBMIT” instructions without a deadline date;
  - an unknown/general intent is not sufficient;
  - existing admission-process and programme-list evidence remains supported.
- In `backend/services/college_query.py::intent_in`, add explicit `eligibility` and `admission_deadline` classification.
- In `backend/services/college_select.py`, replace permissive fall-through with explicit support predicates/dispatch and a false default. Enumerate all existing supported intents so this is not a blanket behavior loss.
- In `evidence_set_sufficient`, make unknown/general and incomplete eligibility/deadline evidence fail.

Verify:

```powershell
uv run python -m pytest -q tests/test_college_reliability_regressions.py tests/test_evidence_selection.py
uv run python -m pytest -q
uv run ruff check .
```

**Expected observable result:** the PhD/deadline fixtures abstain instead of emitting unrelated evidence; existing known-intent tests remain green; public API shape does not change.

**Go:** all existing tests and new tests pass.  
**No-go:** any known supported intent unexpectedly loses evidence or the API schema changes.  
**Recovery:** revert only the changes to `college_query.py`, `college_select.py`, and the new test file; rerun the baseline commands. Do not touch indexes.

## Stage 1 — Protect baseline

- [ ] Record dirty Git status and commit SHA `14ae17b60534a7f14b755822f0685f5097496323` as the planning-time reference; re-read at implementation time.
- [ ] Record corpus/config/index build hashes.
- [ ] Record installed package versions, Python version, CUDA availability, GPU model/VRAM, process RSS baseline.
- [ ] Run `uv run python -m pytest -q` and record count/time.
- [ ] Run `uv run ruff check .`.
- [ ] Capture `/api/health`, one `/api/search`, and five `/api/chat` debug traces.
- [ ] Record current responses for CSE/ECE comparison, PhD eligibility, B.Tech deadline, first-semester follow-up, and eight-semester total.
- [ ] Confirm no generated source/corpus/index file changed.

**Go:** baseline is reproducible and failures are captured.  
**No-go:** indexes/corpus are missing or current tests fail unexpectedly; diagnose before changing code.  
**Recovery:** read-only stage; restore nothing.

## Stage 2 — Critical correctness fixes

### 2.1 Closed evidence contracts

- [ ] Complete the FIRST CODING TASK above.
- [ ] Ensure every current `intent_in` output has either a named support contract or intentional abstention.
- [ ] Do not use answer-specific hard-coded facts.
- [ ] Verify full suite, Ruff, API smoke, and saved traces.

### 2.2 Multi-programme preservation

- [ ] Add `programmes_in(text) -> tuple[str,...]` to `college_query.py`.
- [ ] Keep `programme_in` as first-target compatibility wrapper.
- [ ] Add `QueryScope.programmes`; preserve `QueryScope.programme`.
- [ ] Update `resolve_scope` and `eligible` for any-target matching.
- [ ] Update `select_evidence`/`evidence_set_sufficient` to require one evidence group per comparison target.
- [ ] Add a generic extractive comparison branch in `college_answer.py`; no embedded programme facts.
- [ ] Test CSE+ECE, generic+specific targets, incomplete comparison abstention, and singular compatibility.

**Expected:** CSE and ECE both remain visible in scope, selection, and citations.  
**Go:** all targets have supported evidence or response abstains; full suite passes.  
**Recovery:** revert tuple/comparison branches; wrapper retains old API.

### 2.3 Typed follow-up slot inheritance

- [ ] Parse current and prior slots separately in `resolve_scope`.
- [ ] Inherit only missing compatible programme(s), admission year, route, semesters, fee components, and document items.
- [ ] Record `inherited_slots` for debug tests.
- [ ] Explicit current programme/year/topic/route wins and resets incompatible slots.
- [ ] Test “How much is that?”, “What about the second semester?”, and new-topic reset.

**Expected:** first-semester/tuition survives the compatible short follow-up; explicit second semester replaces only semester.  
**Go:** inheritance and reset matrices both pass.  
**Recovery:** revert inheritance helper/field and retain old text-context behavior.

### 2.4 Metadata-sensitive deduplication

- [ ] Add `_scope_signature` in `retrieval.py` using programme, admission year, route, topics, and year-conflict state.
- [ ] Require compatible signatures before text deduplication.
- [ ] Test JoSAA/DASA, 2025/2026, programme variants, and same-scope collapse.
- [ ] Confirm surviving score/rank fields are unchanged.

**Expected:** identical text with different route/year/programme survives until eligibility.  
**Go:** focused and full search tests pass.  
**Recovery:** revert runtime dedupe function; no index rebuild.

### 2.5 Stage 2 gate

```powershell
uv run python -m pytest -q
uv run ruff check .
# Run existing development regression command documented by the repository.
# Run backend health/search/chat smoke tests.
```

- [ ] Compare against Stage 1 raw outcomes.
- [ ] Record irrelevant answers, abstentions, follow-ups, and citation support as development regression only.
- [ ] Do not proceed if baseline tests/API or unrelated known cases regress.

## Stage 3 — BERT + exact WMD

### 3.1 Dependency integration

```powershell
uv add "transformers>=5.19,<6" "POT==0.9.7"
uv run python -c "import ot, transformers; print(ot.__version__, transformers.__version__)"
uv run python -c "import ot; print(ot.emd2([.5,.5],[.5,.5],[[0.,1.],[1.,0.]]))"
```

- [ ] Confirm output distance `0.0` or numerical equivalent.
- [ ] Inspect lock diff: existing PyTorch CUDA index unchanged.
- [ ] Run full tests before model download.

**Go:** POT imports and exact tiny solve passes on Windows.  
**No-go:** resolution/import/native solver fails.  
**Recovery:** restore pre-task `pyproject.toml`/`uv.lock`, run `uv sync`, and keep the baseline demo. Never replace WMD with cosine.

### 3.2 Preprocessing and representation

- [ ] Create `wmd/__init__.py`, `preprocessing.py`, `representation.py`, and `configs/wmd_experiment.yaml`.
- [ ] Implement NFKC/casefold, fixed abbreviation aliases, versioned stopwords, no stemming, repeated TF terms.
- [ ] Enforce query 32 and document 12/20/32 field caps.
- [ ] Build positive normalized masses.
- [ ] Add `test_wmd_preprocessing.py`.

**Expected:** same text produces same tokens/masses in cache and runtime; abbreviations/numbers survive.  
**Go:** deterministic offline tests and Ruff pass.  
**Recovery:** remove isolated files.

### 3.3 Exact transport core

- [ ] Create `wmd/distance.py` and `test_wmd_distance.py`.
- [ ] Implement float64 Euclidean ground matrix and exact `ot.emd2`.
- [ ] Validate dimensions, finite values, nonnegative costs, positive equal mass.
- [ ] Test zero identity, symmetry, nonnegativity, hand 2×2, repeats, empty/nonfinite errors.

**Expected:** deterministic exact values without BERT/model access.  
**Go:** all solver tests pass repeatedly on CPU.  
**Recovery:** remove isolated files; POT may remain harmless but can be removed through `uv remove POT` if abandoning WMD.

### 3.4 BERT word encoder

- [ ] Create `wmd/encoder.py` with lazy `AutoTokenizer`/`AutoModel` load.
- [ ] Pin model revision and record resolved commit.
- [ ] Use dynamic-padding batches, attention mask, inference mode, layer `-2`, position 0.
- [ ] Reject `[UNK]`, normalize vectors, preserve input ordering.
- [ ] Add CPU retry on CUDA OOM in the experimental process.
- [ ] Add marked integration test for shape `[n,768]`, norm≈1, finite values, repeatability.

**Expected:** one vector per accepted surface word, no special token in vocabulary.  
**Go:** pinned-model CPU test passes; CUDA memory is measured.  
**Recovery:** disable model-marked tests/experiment, preserve solver demonstration and baseline; do not delete broad Hugging Face cache paths.

### 3.5 Cache

- [ ] Create `wmd/cache.py`, `src/build_wmd_cache.py`, cache tests.
- [ ] Write staged artifacts then atomically publish exact cache directory.
- [ ] Validate all manifest compatibility fields and matrix/token alignment.
- [ ] Add exact generated paths to `.gitignore`.

```powershell
uv run python src/build_wmd_cache.py --config configs/wmd_experiment.yaml
git status --short
```

**Expected:** vocabulary count, `[V,768]` shape, file sizes, corpus/model hashes, build time; artifacts do not appear in Git status.  
**Go:** load succeeds online and with `HF_HUB_OFFLINE=1`; mismatch tests fail closed.  
**Recovery:** after verifying the absolute target is exactly the WMD cache directory, remove only `indexes/college_bert_wmd` and rebuild; never touch `indexes/college_bge_base` or `college_bm25`.

### 3.6 Ranker and CLI

- [ ] Create `wmd/ranker.py`, `fusion.py`, `src/run_wmd_experiment.py`, ranker and marked integration tests.
- [ ] Obtain baseline systems once via existing `SearchEngine.search_all`.
- [ ] Apply existing `eligible` and take first 15 RRF candidates.
- [ ] Add WMD fields to copied rows; sort ascending with stable ties.
- [ ] Preserve IDs, titles, headings, URLs, programme/year/route metadata and original ranks.
- [ ] Print baseline and WMD timings/results; support JSON output.
- [ ] Never import the package from default backend modules.

**Expected:** a reproducible side-by-side CLI with finite distances and unchanged baseline rows.  
**Go:** unit, model, CLI schema, full suite and Ruff pass.  
**Recovery:** remove the isolated CLI/package; default app was never wired to it.

## Stage 4 — Benchmark and demonstration

### 4.1 Review the 20-case set

- [ ] Create `evaluation/wmd_immediate_questions.jsonl` from `06_EVALUATION_AND_ABLATIONS.md`.
- [ ] Open current official evidence and assign gold IDs/grades or explicit missing/ambiguous behavior.
- [ ] Record reviewer, date, corpus hash, and family IDs.
- [ ] Validate schema; do not fabricate facts.

### 4.2 Run fair comparisons

- [ ] Create `src/evaluate_wmd.py` and metric/runner tests.
- [ ] Run standalone BM25, BGE, RRF, centroid, and eligible-corpus WMD.
- [ ] Separately run shared top-15 RRF, centroid rerank, WMD rerank, optional BM25/WMD rank fusion.
- [ ] Report Recall@5/10, MRR@10, nDCG@10, latency stages, RSS/VRAM, failures.
- [ ] Keep final-answer evaluation separate.
- [ ] Save raw rankings and exact manifests.

```powershell
uv run python src/evaluate_wmd.py --questions evaluation/wmd_immediate_questions.jsonl --config configs/wmd_experiment.yaml --output evaluation/wmd_runs/presentation
```

**Go:** comparisons use identical eligibility/cutoffs and clearly label shared-pool versus standalone.  
**No-go:** unreviewed gold data, mixed candidate universes, nonfinite distances, or hidden failures.  
**Recovery:** discard only the exact generated run and correct the protocol; never tune on held cases.

### 4.3 Demonstrate

```powershell
uv run python src/run_wmd_experiment.py --query "What B.Tech programmes are available?" --top 5
uv run python src/run_wmd_experiment.py --query "What is the first-semester tuition fee for B.Tech in 2026?" --top 5
uv run python src/run_wmd_experiment.py --query "Compare CSE and ECE programmes." --top 5
```

- [ ] Show query, baseline top matches, WMD order/distances, source links, model/cache IDs, and timings.
- [ ] Explain the 2×2 exact transport example.
- [ ] State clearly that the main app still uses BM25+BGE+FAISS+RRF.
- [ ] If WMD loses, report the result without changing the metric or candidate set.
- [ ] Rehearse baseline-only fallback with WMD cache unavailable.

## Stage 5 — Post-presentation backlog

- [ ] Expand/version official B.Tech, e-M.Tech, PhD, fees, scholarships, TPC, calendar, departments, facilities sources.
- [ ] Implement heading trees, PDF/table parsing, atomic fee/list facts, quality flags.
- [ ] Replace bridge context with typed dialogue FSM and clarification/reset states.
- [ ] Implement operation-aware evidence/answer plans and remove embedded source facts.
- [ ] Build 100–150 independently authored/adjudicated family-split cases.
- [ ] Evaluate flat/hierarchical, metadata, FSM, BM25/BGE/RRF, centroid/WMD, evidence planner, and optional cross-encoder ablations.
- [ ] Consider an optional production WMD adapter only if held-out ranking and answer quality improve with safe p95/memory.
- [ ] Do not add RAG.

## Known limitations

- Pretrained BERT is not fine-tuned for IIIT Kottayam or IR.
- Independent word encoding removes sentence context by design, matching the paper more closely but limiting polysemy handling.
- Layer-11 `[CLS]` interpretation is an explicit choice because the paper is not fully specific.
- L2 normalization is an adaptation.
- First implementation uses flat chunk fields, not paper-style document trees.
- Shared-pool WMD cannot recover evidence absent from RRF top 15.
- Exact POT computation is CPU-bound and has no per-call hard timeout in this design.
- The corpus remains incomplete; WMD cannot answer missing facts.
- The immediate benchmark is small development evidence, not production accuracy.
- WMD ranking improvement does not guarantee answer improvement.

## Final go/no-go summary

| Stage | Go | No-go / fallback |
|---|---|---|
| 1 | Baseline reproducible | Stop and restore environment/artifacts before coding. |
| 2 | All tests/API pass; targeted failures corrected | Revert failing atomic fix; keep prior stable fixes. |
| 3 | POT exact tests, pinned BERT, cache and CLI stable | Keep baseline; demonstrate only completed exact components honestly. |
| 4 | Reviewed labels, fair traces, stable demo | Use baseline web demo plus recorded/solver WMD evidence. |
| Production WMD | Future held-out ranking and answer gain, acceptable p95/memory, zero safety regression | Keep WMD experimental permanently; this still satisfies the academic implementation. |

The checklist is implementation-ready and closes the planning phase. The next action is Stage 1 followed by the FIRST CODING TASK.


# Code Change Map

## Change policy

All changes are additive or narrowly scoped. Existing BM25, BGE encoding, FAISS indexing, RRF arithmetic, API routes, and React components remain unchanged unless a focused regression proves a compatibility defect. WMD imports must never occur during normal backend startup.

## New WMD package

| File | Classes/functions | Input → output | Invariants |
|---|---|---|---|
| `src/doc2dial_retrieval/wmd/__init__.py` | Public experimental exports only | — | Importing package does not load BERT or cache. |
| `src/doc2dial_retrieval/wmd/preprocessing.py` | `WmdPreprocessor`, `normalize_text`, `tokenize_terms` | raw text → normalized token occurrences | Same configuration and code path for query/documents; deterministic. |
| `src/doc2dial_retrieval/wmd/representation.py` | `DocumentMeasure`, `build_document_measure`, `build_query_measure`, `collect_vocabulary` | chunk/query → terms and normalized masses | Query ≤32 occurrences; document ≤64; positive masses sum to one. |
| `src/doc2dial_retrieval/wmd/encoder.py` | `BertWordEncoder`, `encode_words` | unique surface words → `[n,768]` float32 | Pinned model; `eval`/inference mode; `hidden_states[-2][:,0,:]`; L2-normalized; no `[UNK]`. |
| `src/doc2dial_retrieval/wmd/cache.py` | `CacheManifest`, `EmbeddingCache`, `build_cache`, `load_cache` | chunks/model/config → local artifacts, or artifacts → lookup | Every compatibility field validated; no partial cache becomes active; atomic temp-to-final publish. |
| `src/doc2dial_retrieval/wmd/distance.py` | `ground_cost`, `exact_wmd`, typed errors | two measures + vectors → nonnegative distance | Float64 marginals/cost; exact `ot.emd2`; empty/nonfinite inputs rejected. |
| `src/doc2dial_retrieval/wmd/ranker.py` | `WmdReranker`, `WmdRankedResult`, `rerank` | query + candidate dictionaries → metadata-preserving ranked copies | Limit ≤15 by default/configured maximum; ascending finite distance; stable tie break. |
| `src/doc2dial_retrieval/wmd/fusion.py` | `rank_fuse_bm25_wmd` | BM25 and WMD ranks → RRF-ranked IDs | Never adds raw BM25 and WMD values. Experimental only. |

## New commands and configuration

| File | Purpose |
|---|---|
| `configs/wmd_experiment.yaml` | Pinned model/revision, layer selector, token caps, candidate limit, batch size, cache paths, device preference, timeout budget, schema versions. |
| `src/build_wmd_cache.py` | Validate config/corpus; create vocabulary, embeddings, document measures, and manifest; print actual size/timing. |
| `src/run_wmd_experiment.py` | CLI comparison for BM25, BGE, RRF, centroid, and RRF→WMD; optional JSON output. |
| `src/evaluate_wmd.py` | Run the reviewed immediate benchmark, distinguish standalone/shared-pool metrics, write raw results and summary. |
| `evaluation/wmd_immediate_questions.jsonl` | 15–25 reviewed cases with behavior and gold chunk IDs; tracked only after human review. |
| `evaluation/wmd_runs/.gitkeep` | Stable ignored-output location if repository convention needs it; generated run files remain ignored. |

Generated local artifacts:

```text
indexes/college_bert_wmd/
├── vocabulary.json
├── embeddings.npy
├── documents.json
└── manifest.json
```

The directory must be ignored by Git consistently with existing generated indexes.

## Existing files modified for Stage 2 correctness

### `backend/services/college_query.py`

- Add `programmes_in(text) -> tuple[str, ...]` with specificity-first, deterministic order, and no duplicates.
- Keep `programme_in(text) -> str` as a compatibility wrapper returning the first normalized target.
- Extend `QueryScope` with `programmes: tuple[str, ...]` and `inherited_slots: tuple[str, ...]`; retain existing `programme`.
- Update `resolve_scope` to inherit semester, fee components, route, programme(s), admission year, and document items only when `use_context` is true and the current turn does not explicitly replace the slot.
- Update `eligible` so a chunk may match any target programme; generic B.Tech evidence may match a B.Tech specialization only under the current explicit compatibility rule.
- Add explicit `eligibility` and `admission_deadline` intents so these do not fall through to broad admissions.

### `backend/services/college_select.py`

- Replace the final `return True` in `supports_request` with an explicit intent-to-contract dispatch and a closed default.
- Add support functions for admission process, eligibility, deadline, programme list/description/comparison, generic fees, scholarships, departments, and facilities using topic plus requested-attribute evidence.
- Require one supported evidence group per requested programme for comparisons.
- Ensure `evidence_set_sufficient` returns false for unknown/general intents and incomplete multi-programme sets.
- Do not change score weights merely to force tests to pass.

### `backend/services/college_answer.py`

- Add a generic multi-programme branch that emits one source-extracted claim per requested programme only when the selector supplies complete evidence.
- Do not embed programme facts in code.
- Preserve existing answer/citation return contract.

### `src/doc2dial_retrieval/retrieval.py`

- Add `_scope_signature(result)` using programme, admission year, route derived from heading, year conflict, and topics.
- Require compatible signatures before `_duplicate_evidence` can collapse text.
- Preserve current rank and `SearchResult` APIs.

### `pyproject.toml` and `uv.lock`

- Declare `transformers>=5.19,<6` directly and add `POT==0.9.7`.
- Update through `uv add`, never by hand-editing the lockfile.

### `.gitignore`

- Ignore `indexes/college_bert_wmd/` and generated `evaluation/wmd_runs/*` while retaining any explicit placeholder/documentation.

## Tests to create or extend

| File | Coverage |
|---|---|
| `tests/test_college_reliability_regressions.py` | Closed evidence default, explicit known contracts, CSE/ECE preservation, compatible slot inheritance, topic reset, route/year duplicate survival. |
| `tests/test_wmd_preprocessing.py` | Case/punctuation/abbreviation/numeric behavior, stopwords, deterministic query/document parity, caps. |
| `tests/test_wmd_distance.py` | Tiny exact OT examples, zero identity, symmetry, nonnegativity, mass checks, empty and nonfinite failures. No BERT load. |
| `tests/test_wmd_cache.py` | Row/token alignment, deterministic manifest, shape/dtype checks, mismatch rejection, interrupted-build isolation. Use fake vectors. |
| `tests/test_wmd_ranker.py` | Ascending order, stable ties, limit enforcement, failed-candidate handling, metadata preservation. Use injected fake encoder/distance. |
| `tests/test_wmd_encoder_integration.py` | Optional `@pytest.mark.model` checks dimensions, layer selection, deterministic repeated encoding, CPU/CUDA tolerance. Requires cached model. |
| `tests/test_wmd_experiment_integration.py` | Optional `@pytest.mark.model` end-to-end top-15 CLI JSON schema and baseline result preservation. |

Add pytest markers in `pyproject.toml` for `model` and `slow` so the default suite remains offline and fast.

## Files that must remain unchanged for the presentation MVP

- `src/index.py` and all existing FAISS/BGE artifacts;
- `src/doc2dial_retrieval/search.py` retrieval semantics;
- `app/frontend/src/App.tsx`;
- `backend/api/routes.py` and public schemas;
- `configs/college_sources.json`, raw corpus, and processed chunks;
- old planning reports;
- current production `configs/config.yaml`, except no change is required for WMD;
- answer-generation architecture beyond the narrow multi-programme compatibility branch;
- no model fine-tuning or new learned weights.

## Module dependency direction

```text
run_wmd_experiment.py
  -> existing SearchEngine / college scope and eligibility
  -> wmd.ranker
       -> wmd.representation -> wmd.preprocessing
       -> wmd.cache -> wmd.encoder (lazy only for query misses/build)
       -> wmd.distance -> POT
```

No existing retrieval module imports `doc2dial_retrieval.wmd`. This one-way dependency is the rollback boundary.


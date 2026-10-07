# Doc2Dial Retrieval Project Status Report

**Date:** 2026-10-07  
**Project root:** `C:\Users\Saivarad KG\Documents\AI project\finalversion\indlaw-ir`

## Executive Summary

The active project is a clean, local Doc2Dial v1.0.1 retrieval prototype for government-service information. It provides structure-aware chunking, BM25 retrieval, BGE semantic retrieval, FAISS cosine search, BM25-plus-semantic RRF fusion, conversation-history query construction, grounded validation, and a Streamlit interface.

The active implementation does not fine-tune a model, use an LLM, use a reranker, or train a classifier. It is designed as a transparent, low-resource semantic retrieval system.

The latest experiment compared `BAAI/bge-small-en-v1.5` with `BAAI/bge-base-en-v1.5`. BGE-base produced higher measured semantic and hybrid Recall@5, but the BM25 control differed from the preserved historical baseline. That discrepancy is documented and must be reconciled before calling the model upgrade a perfectly isolated causal result.

## Historical Boundary

An earlier Indian legal information-retrieval implementation was explicitly discarded and reset. Its BM25, BERT, metadata classifiers, WMD, rerankers, semantic encoders, checkpoints, indexes, datasets, benchmarks, and reports are not part of the active project.

The current project retains only the broad research topic and uses Doc2Dial. No old Indian legal corpus statistics or evaluation claims are used here.

## Dataset

The official Doc2Dial v1.0.1 archive was downloaded and stored at:

```text
data/raw/doc2dial_v1.0.1.zip
```

It was extracted to:

```text
data/raw/doc2dial/
```

Important files:

```text
doc2dial_doc.json
doc2dial_dial_train.json
doc2dial_dial_validation.json
doc2dial_dial_test.json
```

The dataset contains four domains:

- DMV
- Social Security Administration
- Veterans Affairs
- Federal Student Aid

The document schema contains titles, domains, section spans, headings, parent titles, section IDs, and source offsets. Dialogue turns contain user/agent roles and references to document spans.

Schema inspection is implemented in `src/inspect_data.py`, with notes in `docs/data_notes.md`.

## Preparation and Chunking

Relevant files:

```text
src/prepare.py
src/doc2dial_retrieval/data.py
data/processed/chunks.jsonl
```

The pipeline groups source spans by section, preserves source metadata, builds heading paths, combines related text, splits oversized content, removes exact duplicate text within a document, and writes JSONL chunks.

Current preparation statistics:

| Statistic | Value |
|---|---:|
| Sections observed | 13,421 |
| Source span keys observed | 35,659 |
| Exact duplicate chunks removed during preparation | 964 |
| Searchable chunks | 14,738 |

The tokenizer is a shared lowercased `\\w+` tokenizer. Parent-title parsing uses `ast.literal_eval`, not unsafe `eval`.

## Retrieval Architecture

### BM25

BM25 is implemented in `src/doc2dial_retrieval/retrieval.py`:

```yaml
k1: 1.5
b: 0.75
```

It indexes heading paths and chunk text. Persisted artifacts:

```text
indexes/bm25/index.pkl
indexes/bm25/metadata.json
```

### Semantic retrieval

The semantic retriever uses Sentence Transformers and the BGE query prefix:

```text
Represent this sentence for searching relevant passages:
```

Embeddings are normalized and searched with FAISS `IndexFlatIP`, which is cosine similarity for normalized vectors. CUDA is selected automatically when available. Real embedding generation refuses to silently fall back to CPU when CUDA is unavailable.

### Hybrid retrieval

BM25 and semantic candidates are combined with deterministic Reciprocal Rank Fusion:

```yaml
dense_top_k: 50
bm25_top_k: 50
rrf_k: 60
final_top_k: 5
```

The last three conversation turns are included in the semantic query. BM25 receives the raw user query; semantic retrieval receives the history-aware query.

The semantic refusal threshold remains `0.67` and was not recalibrated during the BGE-base experiment.

## Preserved BGE-small Baseline

The original model was:

```text
BAAI/bge-small-en-v1.5
dimension: 384
```

Its artifacts remain under `indexes/faiss/`.

The preserved historical 200-turn baseline is:

| Mode | Recall@5 |
|---|---:|
| BM25 | 0.620 |
| BGE-small semantic | 0.555 |
| BGE-small hybrid | 0.675 |

Source file: `results/baseline_evaluation.json`.

## Duplicate-Result Diagnosis

The duplication audit found that exact duplicate removal during preparation did not eliminate repeated source evidence across document records.

| Statistic | Value |
|---|---:|
| Exact duplicate-text groups remaining | 1,624 |
| Duplicate chunks beyond one representative | 3,163 |
| Repeated section-text groups | 537 |
| Cross-document exact groups | 1,624 |
| Chunks shorter than 8 tokens | 3,533 |
| Title-like chunks | 3,850 |
| Chunks longer than 512 tokens | 0 |

Common repeated strings included `Topic:`, `Related PDFs:`, and navigation/template controls. Legitimately different service sections were retained.

Artifacts:

```text
results/duplicate_audit.json
results/retrieval_improvement_report.md
```

The current retriever has conservative result-level evidence deduplication: exact normalized evidence is collapsed, long near-duplicates are compared conservatively, and the strongest-ranked representative retains its metadata. This change was made before the BGE-base experiment and was not added during that experiment.

## BGE-base Upgrade Experiment

### Experimental controls

The experiment changed only the semantic model for the experimental index. It retained the same dataset, 14,738 chunks, metadata, tokenizer, BM25 settings, FAISS metric, normalization, query construction, RRF, candidate counts, final top-k, validation set, and refusal threshold.

### Separate artifacts

BGE-base was written separately and did not overwrite BGE-small:

```text
configs/config_bge_base.yaml
indexes/faiss_bge_base/index.faiss
indexes/faiss_bge_base/metadata.json
indexes/faiss_bge_base/embeddings.npy
```

The indexing run confirmed:

```text
model: BAAI/bge-base-en-v1.5
dimension: 768
device: cuda:0
GPU: NVIDIA GeForce RTX 4050 Laptop GPU
chunks: 14,738
batch size: 64
```

### 200-turn results

The BGE-base result file is `results/evaluation_bge_base.json`.

| Mode | Recall@5 |
|---|---:|
| BM25 control in base run | 0.660 |
| BGE-base semantic | 0.640 |
| BGE-base hybrid | 0.770 |

Compared with the preserved baseline:

| Metric | BGE-small | BGE-base | Difference |
|---|---:|---:|---:|
| Semantic Recall@5 | 0.555 | 0.640 | +0.085 |
| Hybrid Recall@5 | 0.675 | 0.770 | +0.095 |

The apparent relative improvements are approximately 15.3% for semantic retrieval and 14.1% for hybrid retrieval.

### Control discrepancy

The preserved historical BM25 score is `0.620`, while the base run reports `0.660`. BM25 should be invariant in this experiment. Therefore the model upgrade shows a promising measured improvement, but the comparison is not yet a perfectly isolated model-only result.

The discrepancy may involve evaluator-version drift, concurrent benchmark processes writing result files, or differences between the preserved historical run and the current evaluator. The preserved baseline file remains available and was not overwritten.

### Known-query results

Detailed output is in `results/model_query_comparison.json`.

For:

```text
How do I change my address with Social Security?
```

both models retrieved the expected `How to change your address?` and `Change your Address and Telephone number online` material. BGE-base changed scores and ordering but did not eliminate repeated address-change evidence. Hybrid retrieval still showed unrelated high-BM25 results.

For:

```text
What should I do if I need to report a complaint?
```

BGE-base semantic retrieval placed multiple `Submit a Complaint` variants near the top and retained `What to do if a complaint is filed against you` in the top five. BGE-base did not independently solve the complaint intent mismatch or duplicate-evidence problem.

### Experiment conclusion

BGE-base has higher measured semantic and hybrid Recall@5 in the recorded run. It is a promising candidate, but it should not yet replace BGE-small as the definitive default until the BM25 control discrepancy is reconciled.

No threshold change, deduplication change, intent heuristic, reranker, LLM, or fine-tuning was added for this experiment.

## Application

The Streamlit interface is `app/streamlit_app.py`. Run it from the project root:

```powershell
uv run streamlit run app/streamlit_app.py
```

Open `http://localhost:8501`.

The UI supports BM25, semantic, and hybrid modes, top-k selection, conversation history, retrieval debug fields, and a semantic refusal warning. The default UI configuration still points to BGE-small artifacts. The BGE-base index requires deliberate configuration switching after control reconciliation.

## Validation

Final checks completed after the benchmark changes:

```text
uv run pytest -q
6 passed

uv run ruff check .
All checks passed
```

Tests cover data parsing, chunking, index alignment/dimensions, RRF behavior, and retrieval result handling.

The project does not declare an `indlaw` console entry point. The supported application command is the Streamlit command above.

## Important Files

```text
pyproject.toml
configs/config.yaml
configs/config_bge_base.yaml
src/inspect_data.py
src/prepare.py
src/index.py
src/evaluate.py
src/compare_models.py
src/audit_duplicates.py
src/doc2dial_retrieval/data.py
src/doc2dial_retrieval/retrieval.py
src/doc2dial_retrieval/search.py
app/streamlit_app.py
docs/data_notes.md
results/baseline_evaluation.json
results/evaluation_bge_base.json
results/model_query_comparison.json
results/duplicate_audit.json
results/retrieval_improvement_report.md
results/bge_model_upgrade_report.md
```

## Reproducible Commands

```powershell
uv run python src/prepare.py
uv run python src/index.py
uv run python src/index.py --config configs/config_bge_base.yaml --skip-bm25
uv run python src/evaluate.py
uv run python src/evaluate.py --config configs/config_bge_base.yaml --output-stem evaluation_bge_base
uv run python src/compare_models.py
uv run pytest -q
uv run ruff check .
uv run streamlit run app/streamlit_app.py
```

## Recommended Next Step

Run one clean, single-process baseline and BGE-base evaluation with the same evaluator and compare freshly generated BM25 controls. Only after the control reaches the same baseline should BGE-base be promoted as the default model.

After that, separate experiments may address chunk quality, duplicate evidence, complaint intent, or threshold calibration. Those changes should remain isolated from the model-upgrade comparison.


# BERT + exact Word Mover’s Distance experiment

## Purpose and relation to the paper

The production assistant uses BM25+BGE+FAISS+RRF. The separate experiment tests a paper-inspired question: can BERT-derived word representations and Word Mover’s Distance improve the order of already retrieved college passages?

What was reproduced/adapted:

- a BERT checkpoint supplies word-level vector representations;
- term-frequency distributions represent query and passage text;
- WMD uses Euclidean costs and exact balanced optimal transport;
- ranking is based on smaller transport distance.

What was not reproduced or claimed:

- no BERT fine-tuning;
- no complete paper classifier or full paper pipeline;
- no standalone whole-corpus WMD search;
- no generative RAG;
- no deployment into FastAPI/React;
- no claim that nine pilot questions reproduce the paper’s evaluation.

## 1. Configuration

`configs/wmd_experiment.yaml` pins:

| Setting | Value |
|---|---|
| Model | `google-bert/bert-base-uncased` |
| Revision | `86b5e0934494bd15c9632b12f734a8a67f723594` |
| Encoder layer metadata | 11 |
| Query term limit | 32 |
| Title/heading/passage limits | 12 / 20 / 32 |
| Candidate limit | 15 |
| Batch size | 64 |
| Device | automatic CUDA, otherwise CPU |

`WmdConfig.fingerprint()` hashes all settings so a stale cache cannot silently be reused.

## 2. Normalization and term measures

`WmdPreprocessor` performs Unicode NFKC normalization, case folding, aliases (`B.Tech→btech`, `e-M.Tech→emtech`, `Ph.D→phd`), `[a-z0-9]+` tokenization, and removal of a fixed versioned stopword set.

`TextMeasure` stores distinct sorted terms and counts. Mass is:

\[
p_i=\frac{count(term_i)}{\sum_j count(term_j)}.
\]

`build_query_measure()` truncates the token sequence before counting. `build_document_measure()` separately takes bounded title, leaf-heading, and passage terms, combines them, then counts duplicates. This means repeated terms have more mass.

## 3. BERT representation

`BertWordEncoder._load()` uses `AutoTokenizer.from_pretrained()` and `AutoModel.from_pretrained()` at the pinned revision. It validates 12 hidden layers and size 768 and runs the model in evaluation mode.

Each normalized surface word is independently tokenized. Words producing no token or `[UNK]` are rejected. Accepted words are batched and passed with special tokens. The code selects:

```python
output.hidden_states[-2][:, 0, :]
```

This is the `[CLS]` position from the selected penultimate hidden-state collection, recorded as `encoder_layer_11_cls`. Each vector is L2-normalized. The original sentence is not supplied, so these are **isolated-word representations**, even though a word’s WordPieces interact inside its own mini-sequence.

## 4. Versioned cache

`src/build_wmd_cache.py` loads the same processed college chunks, builds document measures and a global vocabulary, invokes `BertWordEncoder`, and calls `build_cache()`.

The write is staged in a temporary directory and atomically renamed. The existing target is never overwritten silently. `load_cache()` validates corpus SHA-256, configuration fingerprint, preprocessing fingerprint, model/revision, selector, dimension, and dtype.

Current verified manifest:

- 98 document measures;
- 521 retained vocabulary words;
- shape `521 × 768`, float32;
- corpus hash equal to the BGE index build’s chunks hash.

Unseen query words are encoded lazily and held in a 256-entry in-memory LRU. CUDA out-of-memory falls back to CPU.

## 5. Exact WMD mathematics and `ot.emd2`

`ground_cost()` computes every Euclidean distance between query vectors `x_i` and document vectors `y_j`:

\[
C_{ij}=\|x_i-y_j\|_2.
\]

`exact_wmd()` solves:

\[
\min_{T\ge0}\langle T,C\rangle
\quad s.t.\quad T\mathbf{1}=p,\;T^T\mathbf{1}=q.
\]

POT’s `ot.emd2(p,q,C)` returns the **minimum scalar transport cost**. `emd` would return a transport plan; `emd2` returns the objective value. The implementation sets `numItermax=100000`, validates finite inputs and equal unit mass, and clamps only tiny negative floating-point noise to zero. Lower distance ranks first.

## 6. Candidate generation and reranking

`run_wmd_experiment.py` does not search the corpus with WMD. It:

1. resolves the query scope;
2. runs the existing `SearchEngine.search_all()`;
3. obtains BM25, BGE, and RRF rankings;
4. applies `eligible()` metadata checks;
5. takes at most the first 15 eligible RRF candidates;
6. computes exact WMD for each candidate;
7. sorts by ascending distance, then original RRF rank and chunk ID;
8. reports baseline and experimental orders with source metadata.

`rerank_centroid()` also computes a weighted-centroid cosine baseline. `rank_fuse_bm25_wmd()` optionally fuses BM25 and WMD ranks without adding incomparable raw scores. These outputs are experimental diagnostics, not the web path.

## 7. Evaluation

`src/evaluate_wmd.py` refuses any row whose `review_status` is not `reviewed`. For each reviewed query it retrieves 50 BM25 and 50 dense candidates, constructs RRF, applies the same eligibility filter, and reranks the same top-15 pool. It computes Recall@5, Recall@10, MRR@10, and graded nDCG@10.

The final scored file is `evaluation/wmd_reviewed_verified_pilot.jsonl`. It contains nine user-approved, source-checked cases and is explicitly not an independent evaluation. Eight other proposed cases were excluded for ambiguity, checklist grouping, conversation requirements, or unresolved corpus coverage.

## 8. Actual rank example

For pilot case F01, the canonical tuition evidence was:

`btech-fees-2026::8cf5ae1257ed36b1`

| Method | Rank |
|---|---:|
| BM25 | 2 |
| BGE | 1 |
| RRF | 1 |
| RRF→WMD | 12 |

This is direct evidence that WMD harmed this structured-fact query in the pilot. A06 had no eligible gold candidate in the top-15 pool, so WMD could not recover it. WMD improved none of the nine cases.

## 9. WMD versus cosine

| Aspect | BGE cosine | Experimental WMD |
|---|---|---|
| Representation | one full-text retrieval embedding | distribution of isolated-word BERT vectors |
| Comparison | dot product of two normalized 768-D vectors | exact transport over pairwise Euclidean word costs |
| Word order | indirectly represented by transformer before pooling | discarded after term-frequency measure |
| Compute per candidate | cheap vector operation/index search | optimal-transport solve |
| Corpus role | primary dense retriever | reranker of RRF top 15 |
| Better direction | higher similarity | lower distance |

## 10. Exact commands

From the `iitkasst` directory:

```powershell
uv run python src/build_wmd_cache.py --config configs/wmd_experiment.yaml

uv run python src/run_wmd_experiment.py `
  --query "What is the first-semester B.Tech tuition fee in 2026?" `
  --top 5

uv run python src/evaluate_wmd.py `
  --questions evaluation/wmd_reviewed_verified_pilot.jsonl `
  --config configs/wmd_experiment.yaml `
  --output evaluation/wmd_runs/final_verified_pilot
```

Cache building downloads/loads BERT and should not be done during the presentation if the cache already exists. The benchmark output is intentionally ignored by Git.

## 11. Why it is not deployed

The current pilot gives no effectiveness reason to add WMD to the API: every reported ranking metric fell, no query improved, one exact fee row dropped from rank 1 to rank 12, and latency increased. This conclusion is limited to the present source-checked pilot. A larger independent test could justify revisiting the decision, but current evidence supports leaving WMD isolated.


# Algorithms and mathematics, mapped to the implementation

## A. BM25

### Intuition

Lexical retrieval compares actual words. A document is represented as a **bag of words**: word order is discarded, but occurrence counts remain. This is useful when exact strings—`JoSAA`, `DASA`, `2026`, `CSE`, or `Tuition Fee`—carry strong meaning.

- **Term frequency**, `f(t,d)`: occurrences of term `t` in document `d`.
- **Document frequency**, `df(t)`: number of documents containing `t`.
- **Inverse document frequency:** rare terms are more informative than corpus-wide terms.
- **Length normalization:** a long page should not win merely because it contains more words.
- **TF saturation:** the tenth occurrence helps less than the first.

### Implemented equation

`BM25Store` uses `rank_bm25.BM25Okapi`:

\[
S(q,d)=\sum_{t\in q}IDF(t)\frac{f(t,d)(k_1+1)}
{f(t,d)+k_1(1-b+b|d|/avgdl)}
\]

where:

- `q` is the tokenized query;
- `d` is one indexed chunk;
- `N` is the number of chunks;
- `df(t)` is the number of chunks containing `t`;
- `f(t,d)` is term frequency;
- `|d|` is document token count;
- `avgdl` is average document length;
- `k1=1.5` controls TF saturation: larger values allow repetition to keep contributing longer;
- `b=0.75` controls length normalization: `0` disables it and `1` applies full normalization.

The installed library computes:

\[
IDF(t)=\ln\frac{N-df(t)+0.5}{df(t)+0.5}.
\]

If that value is negative because a word occurs in over half the corpus, `rank_bm25` replaces it with `epsilon × average_idf` rather than allowing a common term to subtract relevance.

### Numerical example

Suppose there are `N=3` chunks and only one contains `tuition`, so:

\[
IDF(tuition)=\ln\frac{3-1+0.5}{1+0.5}=\ln(1.6667)=0.5108.
\]

In the candidate, `tuition` occurs twice, document length is 100, and average length is 80:

\[
TFfactor=\frac{2(1.5+1)}{2+1.5(1-0.75+0.75(100/80))}
=\frac{5}{3.78125}=1.3223.
\]

The one-term contribution is approximately `0.5108 × 1.3223 = 0.6755`. Other query terms contribute their own values.

### Exact implementation details

- `src/doc2dial_retrieval/data.py::tokenize()` lowercases and applies `re.findall(r"\w+", text)`.
- There is **no stemming** and **no explicit production BM25 stopword filtering**.
- `BM25Store.representation()` joins `heading_path` and `text`. College chunks use `[source title, section]`, so title, heading, and passage influence BM25.
- `BM25Store.search()` scores all chunks, sorts descending with index order as a deterministic tie-break, then deduplicates.
- Configuration: `bm25_top_k: 50` in `configs/config.yaml`.

### Strengths and failure cases

BM25 excels at names, codes, years, fee labels, and uncommon official vocabulary. It fails when query and source use different vocabulary, when word order changes meaning, or when two passages share terms but address different tasks. This is why it is paired with BGE and followed by evidence validation.

## B. BGE dense retrieval

### What it is

BGE means **BAAI General Embedding**. The exact model is `BAAI/bge-base-en-v1.5`. It is a transformer encoder trained to map semantically related queries and passages near one another. It is not the same use of BERT as the WMD experiment: BGE produces one retrieval-oriented vector for a complete text; WMD uses vectors for individual words from generic BERT.

### Transformer concepts

The tokenizer converts text into subword IDs. Each transformer layer applies multi-head self-attention: every token forms query, key, and value vectors and computes weighted combinations of other tokens. In simplified form:

\[
Attention(Q,K,V)=softmax\left(\frac{QK^T}{\sqrt{d_k}}\right)V.
\]

“Self” means Q, K, and V come from the same sequence. Multiple layers build context-sensitive token representations. The sentence-transformers wrapper then yields one fixed-size passage/query embedding.

### Meaning of 768 dimensions

The persisted build manifest confirms 768 float32 coordinates per chunk. A coordinate is not manually assigned to “fees” or “admissions.” Meaning is distributed across the vector. Similar text directions have a high cosine similarity.

\[
cos(x,y)=\frac{x\cdot y}{\lVert x\rVert_2\lVert y\rVert_2}.
\]

Because the code uses `normalize_embeddings=True`, both norms are 1, so `cos(x,y)=x·y`.

### Exact calls

- Indexing in `src/index.py`:
  `SentenceTransformer(model_name, device=device)` followed by `model.encode(texts, batch_size=32 on CUDA or 8 on CPU, normalize_embeddings=True, convert_to_numpy=True)`.
- Documents are `" ".join([*chunk.heading_path, chunk.text])` and receive no query instruction.
- Queries in `DenseStore.encode_query()` prepend exactly:
  `Represent this sentence for searching relevant passages: `
- Query arrays are normalized float32 and searched through FAISS.
- The pretrained checkpoint is used directly; **no BGE fine-tuning** is implemented.

### Prefix effect

The prefix tells this BGE version that the text is a retrieval query. It changes the token sequence and therefore its embedding. The passage side is not prefixed, matching the asymmetric query/passage usage coded in the project.

### Strengths and limitations

BGE handles synonyms and paraphrases better than literal matching. It can still confuse topically related but task-incompatible passages, hide exact numeric distinctions in one vector, inherit model bias, and require more compute than BM25. The downstream scope and support checks address some—but not all—of those risks.

## C. FAISS

### Role

FAISS means **Facebook AI Similarity Search**. BGE creates vectors; FAISS stores and searches them. Index construction happens offline; search supplies a new query vector and returns nearest stored positions and scores.

### Actual index

`src/index.py` creates:

```python
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)
```

`Flat` means no compression or clustering: search compares against every vector. `IP` means inner product. With normalized vectors:

\[
x\cdot y=\lVert x\rVert\lVert y\rVert\cos\theta=\cos\theta.
\]

Therefore the returned score is cosine similarity up to normal floating-point behavior.

### Query walkthrough

1. BGE encodes the query into shape `(1,768)`.
2. `index.search(vector.reshape(1,-1), k)` computes inner products with all 98 stored vectors.
3. FAISS returns two arrays: similarity scores and integer row positions.
4. `DenseStore.search_vector()` maps each position to the identically ordered `Chunk` metadata list.
5. Results receive `semantic_score` and one-based `semantic_rank`.

The project saves `index.faiss`, `embeddings.npy`, and `metadata.json`. `SearchEngine.__init__()` checks that BM25 and dense chunk IDs align and verifies the chunks SHA-256 and model against `build.json`.

### Exact versus approximate search

`IndexFlatIP` is exact. Approximate structures such as IVF or HNSW can reduce search work on very large corpora but introduce tuning and possible recall loss. Exact search is sensible for 98 chunks. FAISS is still useful because the storage/search interface can evolve if the corpus grows.

### Limitations

FAISS cannot judge factual correctness, programme/year compatibility, or citation support. It retrieves geometric neighbours only. It also cannot improve weak embeddings and does not replace metadata filtering.

## D. Reciprocal Rank Fusion

### Why fuse ranks

BM25 may score in arbitrary positive units while dense retrieval returns cosine-like values. Adding raw scores would make one scale dominate unless calibrated. RRF ignores magnitudes and combines positions:

\[
RRF(d)=\sum_{s\in\{BM25,BGE\}}\frac{1}{k+rank_s(d)},\qquad k=60.
\]

If a document appears in only one list, it receives one contribution. A document in both receives two.

### Worked example

| Document | BM25 rank | BGE rank | RRF score |
|---|---:|---:|---:|
| A | 1 | 3 | `1/61 + 1/63 = 0.03227` |
| B | 2 | 1 | `1/62 + 1/61 = 0.03252` |
| C | 3 | 2 | `1/63 + 1/62 = 0.03200` |

Document B wins because it is excellent semantically and still high lexically.

### Code behavior

- `SearchEngine` requests 50 BM25 and 50 dense results.
- `retrieval.py::hybrid()` merges by exact `chunk_id` and adds `1/(60+rank)`.
- Sorting is descending RRF, then chunk ID for deterministic ties.
- `dedupe_results()` compares normalized text, but only after `_scope_signature()` confirms programme, year, admission route, topics, and year-conflict state match. Identical words with different scopes are not treated as interchangeable.
- RRF is unweighted in production; neither branch is manually favoured.

### Advantages and limits

RRF is scale-independent, simple, deterministic, and robust to one weak list. It discards confidence gaps, treats sources equally, and cannot introduce a document absent from both input lists. `k=60` smooths differences near the top; it is a conventional configured choice, not optimized on a held-out set here.

## E. BERT in the WMD experiment

### Theory

BERT is **Bidirectional Encoder Representations from Transformers**. “Bidirectional” means self-attention can use tokens on both sides of a position. Original BERT pretraining included masked language modelling: predict hidden tokens from surrounding context. BERT-base has 12 encoder layers, hidden size 768, and 12 attention heads. WordPiece breaks an unknown word into reusable subwords.

`[CLS]` is a special first token often used as a sequence representation. Other output rows correspond to input tokens/WordPieces.

### Exact experimental representation

- Checkpoint: `google-bert/bert-base-uncased`.
- Pinned revision: `86b5e0934494bd15c9632b12f734a8a67f723594`.
- `BertWordEncoder` validates hidden size 768 and 12 layers.
- Each **surface word is encoded independently**, in batches. A split word may contain multiple WordPieces, but the final selected vector is the `[CLS]` row.
- The code calls `output_hidden_states=True` and extracts `output.hidden_states[-2][:,0,:]`. In the project’s metadata this is `encoder_layer_11_cls`: the penultimate hidden-state collection, corresponding to the last encoder layer before the final collection entry convention.
- Vectors are L2-normalized.
- BERT is in evaluation/inference mode and is **not fine-tuned**.

This means the word `bank` receives the same isolated-input representation regardless of whether the original passage concerns finance or a river. BGE instead sees the full query/passage and produces a retrieval-trained sentence vector.

### Cache

`build_wmd_cache.py` builds document term-frequency measures, gathers the sorted vocabulary, encodes it once, and atomically stores:

- `vocabulary.json`;
- `embeddings.npy`;
- `documents.json`;
- `manifest.json`.

The manifest records corpus/config/preprocessing fingerprints. The current artifact has 521 words, 98 document measures, 768 dimensions, and float32 vectors. Unknown query terms are encoded lazily; `WmdReranker` keeps up to 256 in an LRU map. CUDA out-of-memory triggers a CPU fallback.

## F. Word Mover’s Distance

### Intuition

WMD asks: “How much work is required to transform the query’s word distribution into the passage’s word distribution?” Each distinct term has probability mass proportional to frequency. Moving mass between similar BERT vectors is cheap; moving it between distant vectors is expensive.

For query masses `p_i`, document masses `q_j`, embeddings `e_i`, `v_j`, and transport `T_ij`:

\[
C_{ij}=\lVert e_i-v_j\rVert_2
\]

\[
WMD(p,q)=\min_{T\ge0}\sum_{i,j}T_{ij}C_{ij}
\]

subject to:

\[
\sum_jT_{ij}=p_i,\qquad \sum_iT_{ij}=q_j.
\]

The constraints conserve all source and destination mass. Because both distributions sum to one, this is **balanced** optimal transport. Lower WMD is better.

### Hand example

Query: `{fee: 0.5, hostel: 0.5}`. Passage: `{tuition: 0.5, accommodation: 0.5}`. Suppose Euclidean costs are:

| | tuition | accommodation |
|---|---:|---:|
| fee | 0.2 | 1.0 |
| hostel | 1.0 | 0.3 |

The cheapest valid plan moves 0.5 from `fee→tuition` and 0.5 from `hostel→accommodation`:

\[
WMD=0.5(0.2)+0.5(0.3)=0.25.
\]

A mismatched passage requiring cross-moves would cost more.

### Actual solver and structures

- `TextMeasure` stores sorted unique `terms` and integer `counts`; `masses()` normalizes counts to float64 probabilities.
- Query limit: 32 tokens.
- Document limits: 12 title + 20 leaf heading + 32 passage tokens, then counts are combined.
- `ground_cost()` creates the pairwise Euclidean matrix in float64.
- `exact_wmd()` validates shape, finiteness, nonnegative unit masses, then calls `ot.emd2(a,b,cost,numItermax=100000)` from Python Optimal Transport (`pot==0.9.7`).
- `emd2` returns the minimum objective value, not the full flow matrix.
- `WmdReranker.rerank()` computes this for at most 15 eligible RRF candidates, records distance/status/time, and sorts ascending distance with original RRF rank as tie-break.

### Cost and limitations

Cosine compares two fixed vectors with roughly linear work in 768 dimensions. Exact transport solves a constrained optimization over every query-term/document-term pair; cost grows with vocabulary sizes and solver work. Caching avoids repeatedly running BERT, but not the transport solve.

WMD can lose syntax, numbers, negation, table-column meaning, and metadata constraints because it treats text as a weighted term distribution. Isolated-word BERT vectors further remove sentence context. These limitations plausibly explain the poor structured-fact rankings in this pilot, but they do not prove WMD is universally weak.


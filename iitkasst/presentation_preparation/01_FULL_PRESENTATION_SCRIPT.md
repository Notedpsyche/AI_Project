# IIIT Kottayam Applicant Assistant — 30-minute presentation script

This script describes the current implementation. Statements marked **Verified implementation** are grounded in current code or the final benchmark artifact. **Interpretation** means a plausible explanation of measured behavior, not a proven universal result.

## 1. Introduction and motivation — 3 minutes

### What I can say aloud

“Good morning. My CSE 311 project is a context-aware, closed-domain information-retrieval assistant for IIIT Kottayam applicants. An applicant may need one precise fact—such as the 2026 B.Tech tuition fee—but the official information is spread across web pages, tables, and a PDF guide. Ordinary web search may return the right page without identifying the right row, and a generative chatbot may produce fluent information that is not supported by the institute.

My objective was therefore not to build a general chatbot. It was to build a local retrieval system that searches a curated set of official sources, checks programme, year, task, and admission-route constraints, and returns a short answer with the exact supporting source. If the available evidence is inadequate, the system refuses instead of guessing.

The production pipeline combines BM25 lexical retrieval with BGE-base semantic retrieval. FAISS searches the dense vectors, Reciprocal Rank Fusion combines the two rankings, and a deterministic evidence layer validates and extracts the answer. The interface then displays the official URL, source date, programme, admission year, and retrieval diagnostics.”

### Technical explanation

- **Verified implementation:** the allowlist is `configs/college_sources.json`; it currently contains ten official IIIT Kottayam HTML/PDF sources.
- Source bytes stay local. `collect_sources()` verifies the IIIT Kottayam HTTPS domain, content type, a 10 MB limit, and stores a SHA-256 hash and retrieval time.
- The application is React → FastAPI → BM25/BGE/FAISS → RRF → scope and evidence checks → deterministic extractive answer.
- It is not RAG and has no generative LLM. “Assistant” describes the user experience; technically it is a retrieval-and-extraction system.

### Transition

“The architecture was motivated by an IEEE Access paper on transparent, low-resource, context-aware retrieval, so I will first explain what I took from that paper and what I deliberately changed.”

### Code to show

- `configs/college_sources.json`
- `src/doc2dial_retrieval/college.py`: `collect_sources()`, `build_college_chunks()`
- `backend/main.py`: FastAPI lifespan and application construction
- `app/frontend/src/App.tsx`: product description and evidence cards

### Likely interruption questions

- Is this a chatbot? — It has a chat UI, but the core is closed-domain retrieval plus deterministic extraction.
- Why refuse? — A refusal is safer than attaching a citation that does not support the requested fact.
- Is it an official service? — No; it is an academic prototype and the interface says so.

## 2. Research paper review — 4 minutes

### What I can say aloud

“The reference is *Transparent, Low Resource, and Context-Aware Information Retrieval From a Closed Domain Knowledge Base* by Shubham Rateria and Sanjay Singh, IEEE Access 2024, DOI 10.1109/ACCESS.2024.3380006.

The broader lesson I adopted is that a closed-domain assistant should exploit its bounded knowledge base, conversational context, and inspectable retrieval evidence instead of relying on an opaque general generator. The paper also motivated an experiment using BERT-derived word representations and Word Mover’s Distance.

I did not claim to reproduce the entire paper. I did not implement its complete neural classifier, did not fine-tune BERT, and did not deploy BERT plus WMD as the main retriever. I adapted the closed-domain, context-aware objective to the IIIT Kottayam corpus. My production system uses BM25, retrieval-trained BGE embeddings, FAISS, and RRF. Separately, I implemented a controlled BERT plus exact-WMD reranker over the top 15 eligible RRF candidates.

This distinction matters. Reproducing an idea does not require assuming it will win in a different corpus. I tested it, measured it, and retained the production method supported by my pilot results.”

### Technical explanation

- **Verified:** WMD is isolated under `src/doc2dial_retrieval/wmd/` and has no import path into the FastAPI application.
- **Verified:** `run_wmd_experiment.py` first gets BM25/BGE/RRF candidates, applies metadata eligibility, and only then reranks up to 15 candidates.
- **Not implemented:** a full reproduction of every paper component, a trained contextual classifier, generative RAG, or fine-tuned BERT.
- **Interpretation:** differences in corpus structure, representation choice, and candidate generation can explain why a paper-inspired component behaves differently here.

### Transition

“With that scope clear, I can show the architecture that actually serves every web request.”

### Code to show

- `README.md`, section “Optional BERT + exact WMD experiment”
- `src/run_wmd_experiment.py`
- `src/doc2dial_retrieval/wmd/ranker.py`
- `evaluation/WMD_FINAL_BENCHMARK_REPORT.md`

### Likely interruption questions

- Did you reproduce the paper? — I reproduced and evaluated the BERT-derived-word-vector plus exact-WMD idea, while adapting the overall architecture.
- Why is WMD not primary? — The nine-case source-checked pilot showed lower ranking quality and higher latency.
- Does that disprove the paper? — No; it is a small, different corpus and not an independent held-out study.

## 3. Proposed architecture — 3 minutes

### What I can say aloud

“The offline path begins with an explicit allowlist. HTML pages and one PDF are downloaded, hashed, and converted into provenance-rich chunks. Tables are preserved row by row because a fee value without its row and semester headers is dangerous. Every chunk receives a stable ID, source URL, title, programme, admission year, retrieval time, document type, topics, and a year-conflict flag.

Indexing creates two views of the same 98 chunks. BM25 indexes tokens from the heading path and passage. BGE encodes the same heading-plus-passage representation into a normalized 768-dimensional vector stored in a FAISS `IndexFlatIP` index.

At query time, the backend resolves the question’s topic, intent, programme, year, route, semester, and requested fee or document item. BM25 and BGE each retrieve 50 candidates. RRF combines ranks with constant 60. The evidence layer then checks metadata and task support, chooses at most three passages, and the answer composer copies only supported cells or sentences. The API attaches only sources actually cited in the answer.”

### Technical explanation

```text
official allowlist → collect/hash → HTML/PDF extraction → 98 chunks
                    ↘ BM25 index
                     ↘ BGE vectors → FAISS IndexFlatIP
question + bounded previous-user context → scope → BM25/BGE → RRF
→ eligibility → evidence sufficiency → deterministic extraction → citations
```

- `configs/config.yaml`: BM25 top 50, dense top 50, final UI retrieval depth 5, RRF `k=60`.
- `SearchEngine.search_all()` returns BM25, semantic, and hybrid lists from one query path.
- `RetrievalService.search()` converts RRF results to dictionaries and calls the college-specific selector.

### Transition

“The two retrieval branches solve different problems. I will start with the lexical branch, BM25.”

### Code to show

- `src/prepare_college.py`
- `src/index.py`
- `src/doc2dial_retrieval/search.py`: `SearchEngine`
- `backend/services/retrieval_service.py`: `RetrievalService.search()`

### Likely interruption questions

- Is the corpus hierarchical? — It retains a two-element heading path and structured metadata, but it is not a full hierarchical tree or FSM.
- Why 98 chunks? — That is the current persisted corpus count, not a fixed architectural limit.
- Are raw sources committed? — No; the setup collects permitted official sources locally.

## 4. BM25 and lexical search — 3 minutes

### What I can say aloud

“BM25 is a bag-of-words ranking function. It rewards a passage when query terms occur in it, rewards rare terms more than common terms, saturates repeated term frequency, and normalizes for document length.

In my code, `BM25Store` uses `rank_bm25.BM25Okapi` with `k1=1.5` and `b=0.75`. Tokenization lowercases the text and extracts Unicode word tokens with the regular expression `\w+`. There is no production stemming and no BM25 stopword list. Each indexed string is the chunk’s heading path followed by its passage text.

This is valuable for exact terms such as JoSAA, DASA, B.Tech, a programme name, a year, or a fee label. Dense semantics can consider two passages conceptually similar, but BM25 strongly preserves an exact rare identifier. Its weakness is vocabulary mismatch: a user’s paraphrase may use words absent from the relevant passage.”

### Technical explanation

The implemented score follows the `rank_bm25` ATIRE-style BM25 form:

\[
\operatorname{BM25}(q,d)=\sum_{t\in q}\operatorname{IDF}(t)
\frac{f(t,d)(k_1+1)}{f(t,d)+k_1(1-b+b|d|/\operatorname{avgdl})}.
\]

`rank_bm25` computes `IDF(t)=ln((N-df(t)+0.5)/(df(t)+0.5))` and floors negative IDFs to `epsilon × average_idf`. Repeated query terms are iterated repeatedly by the library. Details and a numerical example are in document 02.

### Transition

“To handle vocabulary mismatch and semantic paraphrases, the second branch uses BGE embeddings.”

### Code to show

- `src/doc2dial_retrieval/data.py`: `tokenize()`
- `src/doc2dial_retrieval/retrieval.py`: `BM25Store`
- `configs/config.yaml`

### Likely interruption questions

- Why not remove stopwords? — The implementation is intentionally simple and deterministic; common terms receive low IDF naturally, though explicit stopword handling is a possible experiment.
- What do `k1` and `b` do? — `k1` controls TF saturation; `b` controls length normalization.
- Can BM25 understand synonyms? — Not unless terms overlap or preprocessing maps them.

## 5. BGE and semantic retrieval — 4 minutes

### What I can say aloud

“BGE stands for Beijing Academy of Artificial Intelligence General Embedding. I use `BAAI/bge-base-en-v1.5` through Sentence Transformers. Unlike ordinary BERT used as a general language encoder, BGE has been trained for retrieval-style sentence embeddings.

The transformer tokenizer breaks text into subword tokens. Through multiple self-attention layers, each token representation can incorporate information from the other tokens. A pooling strategy produces one 768-dimensional vector for the complete query or passage. A dimension is not a human-labelled feature; the vector as a whole encodes learned patterns of meaning.

For queries my code prepends exactly: `Represent this sentence for searching relevant passages: `. Documents are encoded without that query prefix. Both are encoded with `normalize_embeddings=True`, so their L2 norm is one. Their inner product is therefore cosine similarity.

During indexing, headings and passage text are encoded in batches and saved as float32 vectors. At runtime, the same pretrained model encodes the query. I did not fine-tune BGE on this college corpus. BGE improves paraphrase handling, but semantic similarity alone may overvalue a passage about the right broad topic but the wrong task, programme, or year.”

### Technical explanation

- `index.py`: `SentenceTransformer(...).encode(texts, normalize_embeddings=True)`.
- `DenseStore.encode_query()`: adds `DENSE_PREFIX`, normalizes, returns float32.
- Persisted `build.json` verifies model `BAAI/bge-base-en-v1.5`, dimension 768, and corpus SHA-256.
- Query self-attention is contextual within the full query. This differs from the WMD experiment, which encodes each vocabulary word independently.

### Transition

“The vectors require an efficient similarity index, and that role belongs to FAISS—not to the embedding model itself.”

### Code to show

- `src/index.py`
- `src/doc2dial_retrieval/retrieval.py`: `DENSE_PREFIX`, `DenseStore`
- `indexes/college_bge_base/build.json`

### Likely interruption questions

- Is BGE BERT? — It is a transformer encoder in the BERT family, trained specifically to produce useful retrieval embeddings; the WMD experiment uses the generic `bert-base-uncased` checkpoint differently.
- What does dimension 768 mean? — Each item is represented by 768 learned coordinates; individual coordinates do not map cleanly to named concepts.
- Did you fine-tune it? — No; it is pretrained inference only.

## 6. FAISS and Reciprocal Rank Fusion — 3 minutes

### What I can say aloud

“FAISS stands for Facebook AI Similarity Search. It does not create embeddings. It stores vectors and finds vectors nearest to the query.

I use `IndexFlatIP`, a flat inner-product index. Because vectors are normalized, inner product equals cosine similarity. Flat means exact exhaustive search: every stored vector can be compared, so there is no approximate-nearest-neighbour recall loss. That is appropriate for only 98 chunks, although FAISS also gives a clean path to larger indexes.

BM25 scores and cosine scores have different ranges, so I do not add them. Reciprocal Rank Fusion uses only rank positions. For each chunk, the score is the sum of `1/(60+rank)` over the BM25 and BGE lists. A passage ranked highly by both gets two contributions. The implementation merges by stable chunk ID and then removes near-duplicate evidence only when programme, year, route, topics, and conflict metadata also match.

RRF is transparent and robust, but it ignores score magnitudes and depends on the quality and depth of its input lists.”

### Technical explanation

\[
\operatorname{RRF}(d)=\sum_{r\in\{BM25,BGE\}}\frac{1}{60+\operatorname{rank}_r(d)}.
\]

- Both branches retrieve 50.
- `hybrid()` merges by `chunk_id`, sorts by descending RRF, then calls metadata-sensitive `dedupe_results()`.
- The production selector sees up to 50 fused candidates; the web response displays only selected cited evidence.

### Transition

“Retrieval only supplies candidates. The next layer decides whether a candidate actually answers the requested task.”

### Code to show

- `src/index.py`: `faiss.IndexFlatIP`
- `src/doc2dial_retrieval/retrieval.py`: `hybrid()`, `_scope_signature()`, `dedupe_results()`

### Likely interruption questions

- Why FAISS for 98 chunks? — Manual NumPy would work, but FAISS provides a tested vector-index abstraction and reproducible exact search.
- Why `k=60`? — It is a conventional rank-smoothing value and is configured, not learned here.
- Is fusion weighted? — No; the current RRF gives the two lists equal rank contributions.

## 7. Query understanding and evidence-based answers — 3 minutes

### What I can say aloud

“The system is context-aware through explicit, bounded rules rather than an LLM or a learned dialogue classifier. `resolve_scope()` identifies topic, intent, one or more programmes, admission year, qualification year, route, semester, fee component, and document item.

It inspects the most recent user message among the last six conversation items. A short continuation containing references such as ‘it’, ‘that’, ‘next’, or ‘what about’ may inherit missing slots. An explicit programme or admission-year change prevents inheritance. The backend then passes only the relevant previous user query into retrieval.

After RRF, `eligible()` rejects metadata conflicts. `supports_request()` checks task-specific evidence—for example, a placement-count question requires placement statistics, not merely an official page. `evidence_set_sufficient()` handles requirements such as both programmes in a comparison. `select_evidence()` applies small, inspectable task bonuses and chooses at most three non-duplicate passages.

Finally, `grounded_answer()` extracts exact table cells or matching source sentences. It refuses when no valid claim remains or when cited years conflict. Citation markers like `[1]` are parsed by the API, which returns only the evidence rows actually cited.”

### Technical explanation

- This is a rule-based scope object, not a formal hierarchical FSM.
- The selector has a closed set of supported intents; an official passage does not automatically count as valid evidence.
- The current composer includes some task-specific regular expressions, especially for fee cells and reporting facts. That improves safety but limits generality.

### Transition

“Alongside this production path, I evaluated the paper-inspired BERT plus Word Mover’s Distance method.”

### Code to show

- `backend/services/college_query.py`: `resolve_scope()`, `eligible()`
- `backend/services/college_select.py`: `supports_request()`, `select_evidence()`
- `backend/services/college_answer.py`: `grounded_answer()`
- `backend/api/routes.py`: `chat()`

### Likely interruption questions

- Does context use the assistant’s previous answer? — The client sends it, but scope inheritance deliberately selects the previous user question; it does not reason over generated answer text.
- How are hallucinations prevented? — There is no free-form generator; claims are copied from selected evidence and unsupported cases refuse.
- Is every possible intent covered? — No. Unsupported intent coverage is a known limitation.

## 8. BERT + WMD experiment — 3 minutes

### What I can say aloud

“For the experiment I pinned `google-bert/bert-base-uncased` to a specific revision. Text is Unicode-normalized, lowercased, aliases such as B.Tech are normalized, and a versioned local stopword set is removed. A query keeps at most 32 terms. A document measure combines at most 12 title terms, 20 leaf-heading terms, and 32 passage terms.

Each distinct surface word is encoded independently. If WordPiece splits it, all pieces are present in that short input, but the code takes the `[CLS]` vector from `output.hidden_states[-2]`, which is encoder layer 11 in the project’s zero-based convention. The 768-dimensional vectors are L2-normalized. This is not full-sentence contextual encoding and BERT is not fine-tuned.

Word Mover’s Distance treats term frequencies as probability mass. It builds a matrix of Euclidean distances between query-word and passage-word vectors, then finds the minimum-cost transport plan satisfying both distributions. The code calls POT’s `ot.emd2`, an exact balanced optimal-transport cost. Lower distance means a closer passage.

To control cost, WMD reranks only the top 15 metadata-eligible RRF candidates. A versioned cache stores 521 vocabulary vectors and 98 document measures; unseen query terms are lazily encoded and kept in a small LRU cache.”

### Technical explanation

\[
\min_T\sum_{i,j}T_{ij}\lVert e_i-e_j\rVert_2,
\quad \sum_jT_{ij}=p_i,\quad \sum_iT_{ij}=q_j,\quad T_{ij}\ge0.
\]

The returned value from `ot.emd2` is the minimized transport cost, not the transport matrix.

### Transition

“Implementation alone does not justify deployment, so I compared it with the existing retrieval methods.”

### Code to show

- `configs/wmd_experiment.yaml`
- `src/doc2dial_retrieval/wmd/encoder.py`
- `src/doc2dial_retrieval/wmd/distance.py`
- `src/doc2dial_retrieval/wmd/ranker.py`

### Likely interruption questions

- Are the word vectors contextual? — Only within each independently encoded word and its WordPieces, not within the original sentence.
- Why exact WMD? — It directly implements balanced optimal transport for the bounded candidate and token limits.
- Can WMD find missing documents? — No; as a reranker it cannot recover a passage absent from the top-15 pool.

## 9. Evaluation results and discussion — 2 minutes

### What I can say aloud

“The final artifact records nine user-approved, source-checked pilot questions. It is not an independent held-out test set, so I report it as a pilot rather than a universal accuracy claim.

BM25 achieved MRR@10 of 0.7500 and nDCG@10 of 0.8166. BGE achieved 0.8333 and 0.8534. BM25 plus BGE RRF was best at 0.8889 MRR and 0.8835 nDCG. RRF followed by exact BERT-WMD fell to 0.5278 and 0.6155. RRF Recall@10 was 0.8889, compared with 0.7778 after WMD reranking.

WMD improved none of the nine queries. For the tuition query it moved the canonical fee-table evidence from rank 1 to rank 12. One admission query failed before reranking because its gold evidence never entered the eligible candidate pool.

The evidence supports keeping RRF for this prototype. A reasonable interpretation is that exact identifiers and structured facts benefit strongly from BM25 and retrieval-trained BGE, while isolated-word transport loses sentence structure and task-specific metadata. This does not prove WMD is generally inferior or contradict results on another corpus.”

### Technical explanation

- Candidate recall before WMD: 8/9.
- WMD increment: mean 54.2 ms; RRF+WMD mean 197.3 ms versus 143.1 ms for RRF/filter. One lazy-load event made the WMD mean less representative; warm p50 increment was 9.2 ms.
- No statistical significance test was performed; nine cases are too few for broad claims.

### Transition

“I will conclude with what the project contributes and what I would improve next.”

### Code/artifact to show

- `evaluation/WMD_FINAL_BENCHMARK_REPORT.md`
- The “Presentation brief” page in the React application

### Likely interruption questions

- Which metric matters most? — They answer different questions: recall checks whether gold appears; MRR rewards the first relevant rank; nDCG rewards graded relevance throughout the top ten.
- Was the evaluation independent? — No; labels were user-approved and source-checked after development.

## 10. Conclusion and future improvements — 2 minutes

### What I can say aloud

“The project demonstrates a transparent closed-domain retrieval assistant built from a reproducible official-source pipeline. Its strongest contribution is not a new foundation model. It is the integration of lexical and semantic retrieval with provenance, context slots, metadata safety checks, deterministic extraction, and honest abstention.

The BERT-WMD experiment is also a meaningful result because I implemented the mathematics, evaluated it on the same candidate conditions, and did not deploy it when the evidence was negative.

The main limitations are the small curated corpus, rule-based intent coverage, a small non-independent evaluation, task-specific extraction patterns, and local rather than production deployment. With more time I would expand and version the corpus, create independently judged train/development/test sets, test a lightweight cross-encoder on frozen candidates, improve table semantics and conversational evaluation, and add automated stale-source monitoring.

My final conclusion is: for this corpus and this pilot, BM25 plus BGE plus RRF offered the best balance of exact matching, semantic recall, transparency, and measured ranking quality. Thank you.”

### Technical explanation

- Future ideas are not current features.
- A cross-encoder would jointly read query and passage, unlike independently computed BGE vectors, but would add latency and require evaluation.
- Deployment on the college site would also need permissions, periodic source refresh, observability, security, and human ownership.

### Final transition to questions

“I am happy to explain the BM25 equation, BGE/FAISS vector search, RRF fusion, the exact optimal-transport formulation, or trace a question through the code.”

### Code to show

- `README.md`
- `evaluation/WMD_FINAL_BENCHMARK_REPORT.md`
- `presentation_preparation/07_DEMO_AND_CHEAT_SHEET.md`

### Likely interruption questions

- What is original? — The domain adaptation, curated provenance pipeline, scope/evidence safety integration, deterministic answer behavior, evaluation harness, and controlled WMD comparison.
- What would be the first next step? — Independent annotation and broader corpus coverage before adding a more complex model.


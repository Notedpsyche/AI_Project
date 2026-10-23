# Professor viva questions and answers

Each entry has a short spoken answer, a deeper follow-up, and implementation evidence.

## Foundations and architecture

### 1. What problem does your project solve? — Easy
**Say:** It retrieves applicant information from a curated official IIIT Kottayam corpus and returns only source-supported answers. **Deeper:** It combines lexical and semantic retrieval with scope, metadata, and evidence checks; unsupported questions abstain. **Evidence:** `README.md`, `backend/services/retrieval_service.py`.

### 2. Is it a chatbot or a search engine? — Easy
**Say:** It has a chat interface, but technically it is a closed-domain retrieval-and-extraction system. **Deeper:** There is no free-form response model; React sends dialogue, FastAPI retrieves passages, and deterministic code extracts claims. **Evidence:** `App.tsx::submit()`, `routes.py::chat()`, `college_answer.py::grounded_answer()`.

### 3. Is it generative? — Easy
**Say:** No. It copies supported source sentences or table cells and adds citation markers. **Deeper:** Some labels and bullet formatting are constructed, but factual content comes from selected evidence. **Evidence:** `_fee_claims()`, `_matching_sentences()`.

### 4. Why not use RAG? — Moderate
**Say:** The project prioritizes traceability and safe behavior on a small corpus; a generator would add hallucination and evaluation risks. **Deeper:** RAG may improve fluency, but still requires retrieval, citation verification, and claim-level grounding. The current deterministic composer makes provenance inspectable. **Evidence:** no LLM dependency or API call in `pyproject.toml`/backend.

### 5. What is “closed domain”? — Easy
**Say:** The system answers only from an explicitly bounded knowledge base. **Deeper:** Ten allowlisted official pages/PDFs are collected; arbitrary web pages are not crawled. **Evidence:** `configs/college_sources.json`, `college.py::load_manifest()`.

### 6. What is your end-to-end architecture? — Easy
**Say:** React → FastAPI → query scope → BM25 and BGE/FAISS → RRF → evidence checks → deterministic cited answer. **Deeper:** Offline collection/chunking/indexing supplies aligned lexical and dense indexes. **Evidence:** `backend/main.py`, `SearchEngine.search_all()`.

### 7. What did you implement from the paper? — Moderate
**Say:** I adapted its transparent closed-domain/contextual retrieval idea and implemented a BERT-derived-word-vector plus exact-WMD experiment. **Deeper:** I did not reproduce its complete classifier or claim full paper replication. **Evidence:** `src/doc2dial_retrieval/wmd/`, benchmark report.

### 8. What is original versus adapted? — Difficult
**Say:** The algorithms are established; my work is the college-domain source pipeline, provenance schema, hybrid integration, context/scope logic, evidence contracts, deterministic citations, and controlled WMD comparison. **Deeper:** “Original” here means project engineering and experimental adaptation, not inventing BM25/BERT/WMD. **Evidence:** college backend/services and evaluation artifacts.

## Corpus and preprocessing

### 9. How is the corpus built? — Moderate
**Say:** An allowlist is fetched, hashed, extracted, split into semantic sections/table rows, deduplicated, and written as JSONL chunks. **Deeper:** HTML and PDF have separate extractors; every chunk carries provenance and scope metadata. **Evidence:** `prepare_college.py`, `college.py`.

### 10. Why use an allowlist? — Easy
**Say:** It controls scope, provenance, and data collection. **Deeper:** It avoids silently crawling unrelated or private material and makes setup reproducible. **Evidence:** `load_manifest()` validates HTTPS IIIT Kottayam hosts.

### 11. How do you preserve tables? — Moderate
**Say:** HTML tables are converted into row-level text with column labels. **Deeper:** `_table_rows()` separates embedded charges and preserves labels such as “Second Semester,” preventing an amount from losing its context. **Evidence:** `college.py::_table_rows()`.

### 12. What is a chunk? — Easy
**Say:** A retrievable source section or table row with a stable ID and metadata. **Deeper:** The ID hashes section plus text and is prefixed by source ID; metadata includes year, programme, URL, SHA, type, and topics. **Evidence:** `build_college_chunks()` and `Chunk`.

### 13. How do you detect stale or changed data? — Moderate
**Say:** Collection stores source hashes and indexing stores the processed-corpus hash. **Deeper:** Startup rejects indexes if `chunks.jsonl` or model differs from `build.json`; it does not yet schedule automatic web refresh. **Evidence:** `SearchEngine.__init__()`.

### 14. What happens with an outdated fee? — Difficult
**Say:** Year metadata must match a year-sensitive query; conflicting-year chunks are rejected. **Deeper:** This reduces mixing but cannot know a source is administratively obsolete if its metadata is wrong; source review and refresh remain necessary. **Evidence:** `eligible()`, `year_conflict`.

## BM25

### 15. Why not use only BM25? — Easy
**Say:** BM25 preserves exact terms but misses semantic paraphrases and vocabulary mismatch. **Deeper:** BGE improves recall when the user and official page phrase the same concept differently. **Evidence:** BM25 MRR 0.7500 versus BGE 0.8333 in the pilot.

### 16. What is TF? — Easy
**Say:** The number of times a term appears in a document. **Deeper:** BM25 saturates TF so repeated occurrences have diminishing benefit. **Evidence:** `BM25Okapi(k1=1.5)`.

### 17. What is IDF? — Easy
**Say:** A weight that makes rare corpus terms more important. **Deeper:** The library uses `ln((N-df+0.5)/(df+0.5))` and floors negative values. **Evidence:** installed `rank_bm25.BM25Okapi` behavior.

### 18. What do k1 and b mean? — Moderate
**Say:** `k1=1.5` controls term-frequency saturation; `b=0.75` controls document-length normalization. **Deeper:** Higher `b` penalizes long documents more relative to average length. **Evidence:** `BM25Store.__init__()`.

### 19. Do you stem or remove BM25 stopwords? — Easy
**Say:** No. Production BM25 lowercases and extracts `\w+` tokens. **Deeper:** Common words naturally get low IDF, but stemming/stopword variants could be separately evaluated. **Evidence:** `data.py::tokenize()`.

### 20. What text is indexed by BM25? — Easy
**Say:** The chunk heading path plus passage text. **Deeper:** College heading paths contain source title and section, so descriptive structure influences lexical ranking. **Evidence:** `BM25Store.representation()`.

## BGE and transformers

### 21. What is BGE? — Easy
**Say:** A retrieval-trained embedding model; I use `BAAI/bge-base-en-v1.5`. **Deeper:** It maps full queries and passages to 768-dimensional vectors where semantic neighbours have high cosine similarity. **Evidence:** `configs/config.yaml`, dense build manifest.

### 22. How is BGE different from ordinary BERT? — Moderate
**Say:** BGE is trained to produce useful retrieval embeddings, while generic BERT provides contextual token states. **Deeper:** Production BGE creates one full-text vector; the experiment uses isolated-word `[CLS]` vectors from `bert-base-uncased`. **Evidence:** `DenseStore` versus `BertWordEncoder`.

### 23. What is self-attention? — Moderate
**Say:** It lets each token weight information from other tokens in the sequence. **Deeper:** `softmax(QKᵀ/√d)V` forms a context-dependent mixture; multiple heads learn different relations. **Evidence:** model theory; transformers library executes it.

### 24. What does 768 dimensions mean? — Easy
**Say:** Every text is represented by 768 learned numeric coordinates. **Deeper:** Meaning is distributed; a single coordinate is not a human-labelled topic. **Evidence:** `build.json` dimension 768.

### 25. What query prefix is used? — Moderate
**Say:** `Represent this sentence for searching relevant passages: `. **Deeper:** It is applied only to queries in `DenseStore.encode_query()`, not passage indexing. **Evidence:** `retrieval.py::DENSE_PREFIX`.

### 26. Did you fine-tune BGE? — Easy
**Say:** No; I use pretrained BGE inference. **Deeper:** A learned reranker scaffold exists but is deployed only if an artifact says `deploy: true`; the current production claim is RRF. **Evidence:** `RetrievalService.__init__()`.

### 27. Why not use only BGE? — Moderate
**Say:** Semantic similarity can blur exact years, codes, amounts, and task distinctions. **Deeper:** BM25 restores exact-token strength and evidence validation enforces scope. **Evidence:** hybrid RRF had higher MRR/nDCG than BGE in the pilot.

## FAISS and similarity

### 28. What is FAISS? — Easy
**Say:** A vector indexing and nearest-neighbour search library; it is not an embedding model. **Deeper:** It stores BGE vectors and returns positions with highest inner product. **Evidence:** `src/index.py`.

### 29. Why FAISS instead of manual cosine? — Moderate
**Say:** Manual NumPy would work at 98 chunks, but FAISS gives a tested index interface that can scale. **Deeper:** Current `IndexFlatIP` is still exhaustive and exact. **Evidence:** `faiss.IndexFlatIP`.

### 30. Why IndexFlatIP? — Moderate
**Say:** Unit-normalized vectors make inner product equal cosine, and a flat index avoids approximate-search loss. **Deeper:** It is appropriate for the small corpus; IVF/HNSW would add complexity without current need. **Evidence:** `index.py`, `normalize_embeddings=True`.

### 31. What does L2 normalization do? — Moderate
**Say:** It scales a vector to length one without changing its direction. **Deeper:** Then `x·y = cos(x,y)`, so magnitude cannot dominate similarity. **Evidence:** BGE encode calls.

### 32. Does FAISS understand programme or year? — Easy
**Say:** No. It knows only vector geometry. **Deeper:** Programme/year/route checks happen later in `eligible()`. **Evidence:** `college_query.py`.

## Fusion and evidence

### 33. Why is hybrid retrieval better here? — Moderate
**Say:** BM25 protects exact facts, BGE handles paraphrases, and RRF rewards passages supported by both. **Deeper:** This complementarity produced the pilot’s best MRR and nDCG. **Evidence:** final benchmark table.

### 34. Why not add BM25 and cosine scores? — Moderate
**Say:** Their numeric scales are not calibrated or directly comparable. **Deeper:** RRF uses rank positions, avoiding arbitrary score normalization. **Evidence:** `hybrid()`.

### 35. What is RRF? — Easy
**Say:** A rank-fusion rule: sum `1/(k+rank)` across retrieval lists. **Deeper:** A passage high in both lists receives two contributions. **Evidence:** `retrieval.py::hybrid()`.

### 36. Why k=60? — Moderate
**Say:** It is a conventional smoothing constant that prevents extreme top-rank dominance. **Deeper:** It is configured, not learned or proven optimal for this corpus; sensitivity testing is future work. **Evidence:** `configs/config.yaml`.

### 37. How are duplicates handled? — Difficult
**Say:** Near-identical text is collapsed only when scope metadata also matches. **Deeper:** Programme, year, route, topics, and year-conflict state form the signature; long texts need at least 0.94 sequence similarity. **Evidence:** `_scope_signature()`, `_duplicate_evidence()`.

### 38. How do you prevent irrelevant official passages? — Moderate
**Say:** Official status is insufficient; the passage must support the requested intent and attributes. **Deeper:** `supports_request()` has task contracts and `evidence_set_sufficient()` checks whole evidence sets. **Evidence:** `college_select.py`.

### 39. How do you prevent hallucinations? — Easy
**Say:** There is no generative answer model; unsupported evidence causes abstention. **Deeper:** The composer copies exact cells/sentences, rejects year conflicts, and the API returns only cited evidence. **Evidence:** `grounded_answer()`, `routes.py::chat()`.

### 40. How are citations verified? — Moderate
**Say:** Citation numbers are generated from selected evidence ranks and parsed before the API attaches sources. **Deeper:** This guarantees the displayed evidence corresponds to cited ranks, although human semantic review is still needed for effectiveness evaluation. **Evidence:** regex in `routes.py::chat()`.

### 41. What happens when information is missing? — Easy
**Say:** The assistant returns a clear refusal and no evidence. **Deeper:** Placement statistics currently demonstrate correct corpus-coverage abstention. **Evidence:** `college_answer.py::REFUSAL`.

## Context

### 42. How is the project context-aware? — Moderate
**Say:** It uses bounded rule-based inheritance of slots from the latest user question. **Deeper:** Reference-like short follow-ups may inherit programme/year/route/semester/component; explicit programme/year changes block inheritance. **Evidence:** `resolve_scope()`.

### 43. Does it use the previous answer? — Difficult
**Say:** The client sends the conversation, but retrieval inheritance deliberately uses the latest user question, not the assistant answer. **Deeper:** This avoids contaminating retrieval with potentially broad answer text but limits richer co-reference. **Evidence:** reverse user-message lookup in `resolve_scope()` and `RetrievalService.search()`.

### 44. Is there an FSM? — Easy
**Say:** No explicit finite-state machine is implemented. **Deeper:** `QueryScope` is a structured slot object built by rules; describing it as a full hierarchical FSM would exaggerate the code. **Evidence:** `college_query.py`.

## BERT and WMD

### 45. What is BERT? — Easy
**Say:** Bidirectional Encoder Representations from Transformers, a pretrained transformer language encoder. **Deeper:** BERT-base has 12 layers and 768 hidden dimensions and was pretrained with masked language modelling. **Evidence:** `BertWordEncoder` validates architecture.

### 46. Which BERT checkpoint and vector do you use? — Difficult
**Say:** Pinned `google-bert/bert-base-uncased`; I take the `[CLS]` vector from `hidden_states[-2]` for each independently encoded word. **Deeper:** The manifest calls it `encoder_layer_11_cls`; vectors are normalized and not fine-tuned. **Evidence:** `wmd/encoder.py`, WMD manifest.

### 47. What is WordPiece? — Moderate
**Say:** A tokenizer that splits uncommon words into known subword units. **Deeper:** The experiment checks that each surface word has valid WordPiece IDs, then encodes the short word sequence with special tokens. **Evidence:** `_accepted_words()`.

### 48. What is optimal transport? — Moderate
**Say:** It finds the cheapest way to move one probability distribution into another. **Deeper:** WMD minimizes mass times Euclidean word-vector cost subject to source/destination conservation. **Evidence:** `wmd/distance.py::exact_wmd()`.

### 49. What does `ot.emd2` do? — Difficult
**Say:** It returns the exact minimum Earth Mover transport objective for two balanced distributions and a cost matrix. **Deeper:** It returns the scalar cost, not the flow matrix; the code validates unit masses and uses up to 100,000 iterations. **Evidence:** `exact_wmd()`.

### 50. Why WMD instead of cosine? — Moderate
**Say:** WMD explicitly matches word-level mass, while cosine compares global vectors. **Deeper:** That can expose word-to-word semantic alignment, but it is slower and loses order after the term distribution is built. **Evidence:** `WmdReranker` and `weighted_centroid_cosine()`.

### 51. Why did WMD underperform? — Difficult
**Say:** In this pilot, isolated-word transport did not preserve structured facts as well as exact BM25 plus retrieval-trained BGE. **Deeper:** Likely factors include lost sentence/table structure, isolated-word context, token truncation, and candidate limitations; these are interpretations, not proven universal causes. **Evidence:** F01 rank 1→12; metrics 0.5278 MRR and 0.6155 nDCG.

### 52. Does that contradict the paper? — Difficult
**Say:** No. Results depend on corpus, implementation, candidates, and evaluation. **Deeper:** This is a bounded reranker over a small college corpus, not the paper’s full setup. **Evidence:** benchmark scope statement.

### 53. Why didn’t you fine-tune BERT? — Moderate
**Say:** The project had little independently labelled data and a low-resource presentation goal. **Deeper:** Fine-tuning could overfit nine pilot cases and would complicate attribution; pretrained inference made the comparison reproducible. **Evidence:** no optimizer/training path in WMD modules.

### 54. Why cache BERT words? — Easy
**Say:** Re-encoding every document word for every query would be wasteful. **Deeper:** The cache is fingerprinted to model, preprocessing, config, and corpus; missing query words are lazily cached. **Evidence:** `wmd/cache.py`, current 521-word manifest.

## Evaluation, deployment, and limitations

### 55. How did you evaluate? — Moderate
**Say:** I compared BM25, BGE, RRF, and WMD on the same nine source-checked pilot queries using Recall, MRR, and nDCG. **Deeper:** WMD reranked the same eligible top-15 RRF pool; unresolved cases were excluded. **Evidence:** `evaluate_wmd.py`, final report.

### 56. Why isn’t the evaluation independent? — Easy
**Say:** The questions and judgments were used during development and approved by the project user rather than untouched external annotators. **Deeper:** Therefore the report calls it a pilot and avoids an accuracy/generalization claim. **Evidence:** every reviewed row’s verification status and report scope.

### 57. Which method won? — Easy
**Say:** RRF: MRR@10 0.8889 and nDCG@10 0.8835. **Deeper:** WMD had 0.5278 and 0.6155 and improved no query. **Evidence:** final benchmark report.

### 58. Does it need a GPU? — Moderate
**Say:** No; BGE and BERT can run on CPU, but GPU improves indexing and model inference. **Deeper:** code selects CUDA when available; WMD catches CUDA OOM and moves BERT to CPU. **Evidence:** `index.py`, `DenseStore.load()`, `BertWordEncoder`.

### 59. How would you deploy it on the college website? — Difficult
**Say:** Containerize frontend/backend, persist versioned indexes, schedule reviewed source refresh, add authentication/rate limits/monitoring, and obtain institutional approval. **Deeper:** Production also needs accessibility, security review, source ownership, rollback, and human escalation. **Evidence:** these are future requirements, not current features.

### 60. Why not a cross-encoder? — Difficult
**Say:** A cross-encoder could judge query and passage jointly, but adds latency and needs reliable labels. **Deeper:** It is a sensible future reranker only after a frozen independent test set; complexity should follow evidence. **Evidence:** no production cross-encoder dependency/path.

### 61. What are the biggest limitations? — Easy
**Say:** Small corpus, rule-based intent coverage, task-specific extraction, non-independent pilot, and local-only deployment. **Deeper:** Missing official topics correctly abstain but reduce coverage; future expansion must preserve year/provenance safety. **Evidence:** source manifest and final report.

### 62. What would you improve first? — Moderate
**Say:** Expand verified source coverage and create an independently judged test set before changing models. **Deeper:** Then evaluate table-aware chunking, conversation cases, and a lightweight cross-encoder against the frozen baseline. **Evidence:** current corpus/evaluation limitations.


# Paper Comparison

## Reference and access note

The requested paper is *Transparent, Low-Resource, and Context-Aware Information Retrieval System for Enterprise Data*. The supplied task did not include the PDF, so the audit used the official IEEE record and DOI: [IEEE document 10477429](https://ieeexplore.ieee.org/document/10477429), [DOI 10.1109/ACCESS.2024.3380006](https://doi.org/10.1109/ACCESS.2024.3380006). The comparison below is based on the complete 11-page paper, not only its abstract.

## Paper system

The paper targets private enterprise-bank data and organizes the dialogue as a hierarchy of finite-state machines (FSMs): a global manager plus sub-FSMs for tabular, document, and intranet intents. Snips NLU extracts intent and entities such as category, country, business function, date, file type, and domain keywords. The state stores selected metadata, asks follow-up questions to narrow the result set, and switches FSM when a new intent is detected.

Documents are represented as trees whose root contains path and metadata and whose descendants correspond to heading levels and section text. A multi-label BERT-based model predicts category, country, and business function; the top two labels per dimension filter candidates. Retrieval compares:

- BM25 over documents;
- BERT word representations with centroid cosine similarity;
- BERT word representations with Word Mover’s Distance (WMD).

The WMD formulation performs optimal transport between query and document token distributions. Evaluation uses 100 random distinct user-log queries, top-10 results, 0–5 human relevance grades, and DCG. BERT+WMD is reported above BM25 and centroid cosine. A BM25/WMD interpolation is proposed later, but it is not evaluated in the main results. Retrieval-augmented generation is described as future work, not as part of the implemented system.

## Side-by-side comparison

| Dimension | Paper | Current IIITK assistant | Consequence |
|---|---|---|---|
| Domain | Private enterprise bank | Public applicant information | Metadata dimensions must differ; country/business function should not be copied. |
| Dialogue | Explicit hierarchical FSM and slot narrowing | Regex scope plus previous-user concatenation | The paper’s explicit state is directly relevant to follow-up failures. |
| Structure | Hierarchical document trees | Flat heading/page chunks | Current system loses table/list/parent semantics. |
| Metadata | Learned multi-label filter | Regex/source metadata and post-retrieval hard filter | Current filtering is transparent but too coarse and ordered too late. |
| Sparse retrieval | BM25 baseline | BM25 branch | Already present and should remain. |
| Semantic retrieval | Word-level BERT centroid/WMD | BGE-base sentence embeddings + FAISS cosine | Current dense representation is more directly designed for retrieval. |
| Fusion | Proposed BM25+WMD interpolation, not evaluated | Implemented RRF over BM25 and BGE | Current fusion has stronger local operational evidence than the paper’s untested mixture. |
| Answer | Transparent source retrieval | Deterministic cited extractive composition | Both prioritize transparency; current answer layer adds more direct response behavior. |
| Generation | RAG only future work | No LLM | The paper does not justify adding an LLM now. |

## Required feature-by-feature classification

| Feature | Classification | Practical effect of difference |
|---|---|---|
| Closed-domain knowledge base | **Directly implements the paper’s principle** | Beneficial: official allowlist and provenance fit the application, though coverage is incomplete. |
| Query understanding/context | **Partially implements** | Harmful: regex continuation lacks durable slots and clarification. |
| State machine | **Does not implement** | Harmful for follow-ups, ambiguity, and reliable reset. |
| Metadata representation | **Partially implements** | Mixed: programme/year/topic exist, but route, temporal roles, hierarchy, and version authority are weak. |
| Metadata prediction/filtering | **Uses a different approach** | Neutral-to-beneficial for transparency (rules versus learned labels), but current post-retrieval order and coarse fields are harmful. |
| Sparse retrieval | **Directly implements an equivalent** | Beneficial: BM25 is a valid strong baseline. |
| Dense representations | **Uses a different approach** | Beneficial: BGE sentence retrieval is purpose-built and contextual compared with isolated word lookup. |
| BERT architecture versus BGE | **Adapted equivalent** | Beneficial for practical retrieval; the paper’s exact classifier/embedding network is not reproduced. |
| Fine-tuning strategy | **Does not implement the paper’s classifier training** | Neutral now because equivalent labeled metadata data do not exist; a small optional logistic reranker is coded but not deployed. |
| WMD versus vector similarity | **Uses a different approach** | Neutral until a fair local test; current cosine is far cheaper. |
| Candidate ranking | **Adapted equivalent** | Beneficial operationally: two retrievers plus RRF, but no semantic pairwise reranker. |
| Hybrid scoring | **Uses a different approach** | Neutral/beneficial: RRF is implemented; the paper’s BM25/WMD mixture is proposed but not evaluated. |
| Document structure | **Partially implements** | Harmful: headings are retained superficially but not as a real tree; tables/lists lose context. |
| Source transparency | **Directly implements** | Beneficial: answer cards expose official source metadata. |
| Evaluation methodology | **Uses a different approach** | Mixed: current metrics are broader, but test leakage prevents an independent performance claim. |

The smallest defensible paper-inspired implementation is: (1) explicit college-specific FSM/slot state, (2) hierarchical versioned documents and metadata candidate constraints, and (3) a bounded WMD/centroid experiment against BM25, BGE, RRF, and a modern cross-encoder. Exact reproduction of the private classifier is neither feasible nor necessary.

## What should be adopted

### 1. Explicit finite-state dialogue control

Adopt the principle, not the enterprise labels. A college-specific FSM should track programme(s), admission route, admission/effective year, qualification year, semester, fee component, requested attribute, and answer operation. It should clarify only when a missing slot changes which source or fact is correct. This directly addresses the confirmed conversational failures.

### 2. Hierarchical, metadata-rich document representation

Preserve source → heading hierarchy → section/table → atomic fact. Programme, route, year, effective period, authority, and fact type should be first-class metadata. This is the paper’s strongest transferable retrieval idea and addresses current chunk-structure defects.

### 3. Candidate filtering before expensive ranking

When programme/year/route are explicit and metadata confidence is high, filter before dense reranking. When uncertain, use soft boosts or retrieve both scoped and unscoped candidates to avoid false negatives. This improves both precision and efficiency while avoiding the paper’s opaque top-two learned-filter risk.

### 4. WMD as a controlled academic ablation

WMD is worth reproducing as an experiment because it is central to the paper and the corpus is small. It should rerank a bounded candidate set, not scan the corpus. Use the existing BGE token or another explicitly documented embedding choice and a direct optimal-transport implementation such as [Python Optimal Transport](https://pythonot.github.io/). Do not add maintenance-mode Gensim solely for this experiment.

## What should not be copied

- Do not replace BGE sentence retrieval with words embedded independently by an older BERT; the paper’s method removes query context at the word lookup stage.
- Do not make learned metadata classification the only entry to retrieval. Top-two labels can irreversibly exclude the correct source.
- Do not treat the paper’s WMD result as proof it will improve this corpus; the domains, labels, and candidate pools differ.
- Do not claim the BM25/WMD mixture is validated; the paper proposes but does not report that experiment.
- Do not add RAG on the paper’s authority. RAG is future work in the paper.

## Paper evaluation limitations

The paper is useful but not a gold-standard experimental template:

- corpus and labels are private, preventing direct reproduction;
- only 100 user-log queries are reported;
- no held-out development/test protocol is described;
- DCG is reported without a normalized counterpart in the presented comparison;
- BERT systems receive metadata-filtered candidates while BM25 searches all documents, so candidate pools are not controlled;
- latency, memory, statistical uncertainty, and significance are not reported;
- ambiguous, unsupported, outdated, and conversational cases are not isolated;
- no learned-fusion or cross-encoder comparison is presented.

## Defensible paper-inspired experiment

Use the frozen college test collection and the same corpus/candidate cutoff to compare:

1. BM25;
2. BGE cosine;
3. current BM25+BGE RRF;
4. paper-style metadata filter + BERT/BGE centroid cosine;
5. metadata filter + bounded WMD reranking;
6. BM25/WMD interpolation with its weight tuned only on development data;
7. current RRF + a modern cross-encoder.

Report Recall@5/10, MRR@10, nDCG@10, source/version correctness, latency, and final-answer effects. This preserves the paper’s central idea while producing a fairer and more relevant comparison.


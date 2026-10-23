# Improvement Options

## Decision framework

Options are evaluated against four requirements: answer correctness, transparent official-source support, feasibility on an RTX 4050 laptop with about 6 GB VRAM and 24 GB RAM, and the ability to measure improvement on an untouched test set.

## Options

### Option A — Tune the current rules only

Add regexes, intent labels, and answer patterns without changing corpus structure.

- **Benefit:** low implementation cost and quick development-regression gains.
- **Risk:** repeats the current test-guided hard-coding pattern; cannot reliably solve totals, hierarchy, stale versions, or multi-entity questions.
- **Verdict:** reject as the main strategy. Use small rule changes only inside a typed design.

### Option B — Replace retrieval models

Swap BGE/FAISS/RRF for another embedding model or vector database.

- **Benefit:** possible ranking gains on semantic paraphrases.
- **Risk:** does not fix confirmed cases where correct evidence ranked first, where scope collapsed two programmes, or where missing sources made an answer impossible.
- **Verdict:** reject for the next phase.

### Option C — Add a generative LLM immediately

Pass retrieved chunks to a hosted or local model for answer generation.

- **Benefit:** better prose, synthesis, and multi-part response potential.
- **Risk:** an LLM cannot recover absent or incorrectly filtered facts; it can convert weak evidence into confident unsupported text. Hosted use adds privacy/network/cost concerns. Local 4B inference must share limited VRAM with BGE and any reranker.
- **Verdict:** defer until retrieval, evidence contracts, and independent evaluation are sound.

### Option D — Structure, state, evidence contract, then rerank

Keep BM25+BGE+FAISS+RRF, but introduce versioned hierarchical ingestion, typed dialogue state, pre-retrieval metadata constraints, operation-aware sufficiency checks, and deterministic structured answer plans. Evaluate a small cross-encoder afterward.

- **Benefit:** directly addresses every confirmed failure while preserving working components.
- **Risk:** requires source curation and careful schema migration.
- **Verdict:** **recommended**.

### Option E — Reproduce the paper architecture exactly

Use Snips-style intents, independent BERT word embeddings, WMD, and hierarchical FSMs as the production path.

- **Benefit:** strong academic comparison narrative.
- **Risk:** obsolete/less contextual representation, unavailable private training data, and no evidence that production WMD improves this college corpus.
- **Verdict:** adopt FSM/structure concepts; keep WMD as an experiment only.

## Recommended target components

### Corpus governance

Expand only through a reviewed official-source manifest. Required categories are current and archived B.Tech admissions, e-M.Tech, PhD, programme/route/year fees, scholarships, Training and Placement Cell statistics, academic calendars, departments/programmes, campus/hostel/facilities, reporting checklists, regulations, and role-based contact pages.

Store downloaded content locally and keep it out of public Git. Track canonical URL, retrieval time, hash, document version, effective period, supersession relation, programme, route, authority, and review status. Exclude personal directories, login-only pages, unrelated publicity, and sources whose reuse/access status is unclear.

### Structure-aware ingestion

- Parent-child IDs for source, section, subsection, table, row, and atomic fact.
- Table facts retain row and column headers, currency/unit, semester, component, and total type.
- Lists retain the heading and completeness boundary.
- PDF extraction records page, heading, table region, and a quality flag; reviewed overrides handle critical malformed documents.
- Deduplicate only after preserving and comparing metadata; never let a wrong-scope duplicate erase a correct one.

### Typed scope and dialogue FSM

Recommended slots:

`intent`, `answer_operation`, `programmes[]`, `specialisations[]`, `route`, `admission_year`, `effective_year`, `qualification_year`, `semesters[]`, `fee_components[]`, `entity`, `attribute`, `comparison_targets[]`.

Recommended states:

`NEW → RESOLVE_SCOPE → NEED_CLARIFICATION | RETRIEVE → SELECT → ANSWER | ABSTAIN`, with explicit `RESET` when the user introduces a new topic/programme/year.

Dialogue state should be updated from both the prior user request and the accepted answer scope, not from concatenated text. Inheritance must be slot-specific. An explicit new programme/year overrides old state; a short referential question inherits only compatible unresolved slots.

### Retrieval and selection

1. Apply hard metadata filters only for high-confidence explicit slots.
2. For uncertain slots, retrieve a scoped branch and an unfiltered fallback branch.
3. Run BM25 and BGE over equivalent candidate sets.
4. Fuse with current RRF.
5. Apply deterministic version/route/programme safety filters.
6. Optionally rerank top 20–30 query-passage pairs with a cross-encoder.
7. Evaluate operation-specific evidence completeness.

The first reranker experiment should use [`cross-encoder/ms-marco-MiniLM-L6-v2`](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) because it is small (about 22.7M parameters) and permissively licensed. [`BAAI/bge-reranker-base`](https://huggingface.co/BAAI/bge-reranker-base) is a stronger but larger challenger. Model-card throughput must not be projected onto this laptop; benchmark warmed p50/p95 locally. Cross-encoder logits are ranking scores, not calibrated answer-confidence probabilities.

### Evidence contract and deterministic answering

Every intent/operation should declare required slots and evidence fields. Examples:

- `deadline`: a date explicitly typed as the relevant deadline plus programme/route/year match;
- `aggregate_total`: complete component/semester coverage or an authoritative stated total;
- `comparison`: one comparable fact set per target;
- `list`: evidence marked complete for the requested scope;
- `count`: a source-backed statistic for the requested population and period;
- `amount`: an amount, currency, component, and effective period.

If the contract is not satisfied, clarify or abstain. Then compose from structured facts, validate every number and named entity against evidence, and attach claim-level source IDs.

## Optional local RAG gate

Only after the deterministic target passes held-out safety gates should a local generator be tested for multi-source prose. [Qwen3-4B GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF) offers an official Q4_K_M artifact around 2.5 GB and is technically plausible on the laptop, but total VRAM also includes BGE, reranker, runtime overhead, and KV cache. Benchmark rather than assume feasibility.

If tested, require structured output with evidence IDs, exact-number validation, sentence/claim support checks, and deterministic fallback. Do not let the model decide whether evidence is sufficient. Hosted generation should remain a separate option with explicit privacy, cost, and availability review.

## Recommended decision

Proceed with Option D. Treat cross-encoder reranking, paper-style WMD, and local RAG as successively gated experiments—not prerequisites and not assumed improvements.

## Independent assessment of the seven requested improvements

| Improvement | Expected value | Cost/risk | Measurable experiment | Rank |
|---|---|---|---|---:|
| Corpus expansion | Very high; resolves hard absence. | Manual review, staleness, permissions. | Coverage matrix, source/version correctness, answerability rate. | 1 |
| Structure-aware ingestion | Very high for fees, lists, dates, and hierarchy. | Parser complexity and PDF exceptions. | Old versus structured corpus with identical retrievers. | 2 |
| Context-aware FSM | Very high for follow-ups and ambiguity; strongest paper link. | Over-inheritance/over-clarification. | State-transition suite and multi-turn held-out cases. | 3 |
| Evidence contract/answer planning | Very high because current failures occur after retrieval. | May increase honest abstentions initially. | Complete-evidence and fully-supported-answer rates. | 4 |
| Improved hybrid retrieval | Medium after data fixes. Keep BGE prefix/normalization; test BM25 parameters, query aliases, RRF `k`, candidate depth, and filter order one factor at a time. | Tuning leakage and latency. | Equal-depth dev ablations; lock before test. | 5 |
| Cross-encoder reranking | Medium potential for top-order relevance. | Added latency/VRAM and no guaranteed final-answer benefit. | MiniLM then BGE reranker over top 10/20/30. | 6 |
| Paper-inspired WMD | Academic value; uncertain practical value. | Optimal-transport cost and token representation choices. | Bounded same-pool WMD/centroid/BM25 mixture ablation. | 7 |
| RAG | Potential later benefit for synthesis only. | Hallucination, latency, deployment, validation burden. | Feature-flagged blinded comparison after safety gates. | 8 |

Query expansion should use a reviewed ontology of programme names, abbreviations, fee components, and admission terms; it must not inject a programme/year absent from the resolved scope. BM25 and RRF tuning should wait until duplicate handling and structured ingestion are stable, otherwise parameter changes will fit parser defects.


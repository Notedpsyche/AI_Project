# Final Recommendation

## Authoritative answers

1. **Which BERT?** Use `google-bert/bert-base-uncased` pinned to revision `86b5e0934494bd15c9632b12f734a8a67f723594`. It matches the paper's base BERT family, has 12 layers/768 dimensions/110M parameters, is Apache-2.0, and fits the laptop for inference. Do not fine-tune it for this phase.

2. **How are word embeddings extracted?** Encode each normalized surface word independently as `[CLS] WordPieces [SEP]`; take the `[CLS]` hidden vector from encoder layer 11 (`hidden_states[-2]`), convert to float32, and L2-normalize. All WordPieces influence `[CLS]`; special tokens never receive transport mass. Reject `[UNK]` terms. This is the closest explicit adaptation of the paper's ambiguous “first sequence output of layer 11.”

3. **Which WMD?** Use exact balanced Earth Mover's Distance through POT 0.9.7 `ot.emd2`, term-frequency marginals, and pairwise Euclidean ground costs between normalized BERT vectors. Sinkhorn, Relaxed WMD, and cosine are not substitutes.

4. **How many candidates?** Rerank the first 15 metadata-eligible RRF candidates. This bounds exact transport and is enough for a clear CLI demonstration. Label it RRF→WMD reranking. A separate offline full-eligible-corpus WMD run provides the standalone academic comparison.

5. **What document text?** Use up to 12 title tokens, 20 leaf-heading tokens, and 32 passage tokens (64 total). Headings alone are too sparse; full chunks add unrelated mass and unpredictable cost. Hierarchical nodes are deferred.

6. **How is caching handled?** Build a sorted corpus vocabulary and one row-aligned float32 `[V,768]` matrix plus document measures and a strict manifest under `indexes/college_bert_wmd/`. Bind it to corpus SHA, model revision, preprocessing and representation schema. Memory-map on load. Encode missing query words lazily into a bounded in-process LRU.

7. **Will it run on the laptop?** It is technically feasible: BERT base is roughly 440 MB of float32 weights before runtime overhead, cache vectors are about 3 KB per unique term, and exact matrices are capped at 32×64 for 15 candidates. Actual CUDA/CPU latency and peak memory must be measured. Run the WMD CLI separately from the BGE backend for the demo if concurrent VRAM is uncertain.

8. **What is realistic before the presentation?** Protect the baseline, land four focused reliability fixes, implement exact solver/encoder/cache/ranker, build one cache, run deterministic tests and a five-query smoke comparison, and demonstrate through CLI. Do not attempt UI integration, corpus expansion, hierarchy migration, production WMD, cross-encoder work, or independent-accuracy claims.

9. **Which existing bugs are first?** Closed evidence sufficiency, multi-programme preservation, compatible semester/fee slot inheritance, then metadata-sensitive deduplication. WMD begins only after their integration gate passes.

10. **What is the first implementation task?** Capture the baseline and then implement the closed evidence-support contract in `college_query.py`/`college_select.py` with a new focused regression file. Exact instructions and commands are in `FINAL_IMPLEMENTATION_CHECKLIST.md`.

## Production decision

BM25+BGE+FAISS+RRF remains the sole default production retriever. BERT+WMD is a real, independently executable academic experiment. It becomes an optional production reranker only after a future held-out test demonstrates ranking **and final-answer** benefit with acceptable latency and no safety regression. A negative result is still a successful implementation and should be reported faithfully.

## Final implementation boundary

- No RAG or generative LLM.
- No BERT fine-tuning.
- No BGE/FAISS/RRF rewrite.
- No WMD import on default backend startup.
- No raw BM25/WMD score addition.
- No UI change before the presentation.
- No claim that the current 45-case suite or the immediate 20-case benchmark is independent production accuracy.

The architecture is frozen. No further design decision is required before starting Stage 1 and the first coding task.


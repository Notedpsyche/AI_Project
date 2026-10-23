# Executive Recommendation

## Decision

Refactor the existing IIIT Kottayam assistant; do not rewrite it and do not replace the retrieval stack. The recommended next release keeps React, FastAPI, BM25, BGE-base, FAISS, RRF, source provenance, and deterministic extractive fallback. It changes the corpus representation, query/dialogue state, evidence sufficiency rules, and answer planning before considering a learned reranker or LLM.

## Why

The audit found multiple novel failures in which retrieval had already surfaced useful evidence:

- a correct PhD candidate ranked first, but generic selection and lexical composition answered with B.Tech material;
- CSE evidence was retrieved for a CSE/ECE comparison, but the singular programme resolver reduced the question to ECE and filtered CSE out;
- fee components were retrieved, but no total operation or completeness contract existed;
- a deadline request received portal-submission instructions because any general admissions evidence was treated as sufficient;
- an elliptical follow-up inherited programme/year but lost semester/component scope.

These failures cannot be solved by changing the embedding model alone. The corpus is also too narrow for the advertised breadth: there is no active placement evidence and incomplete PhD, e-M.Tech, department, calendar, and facilities coverage.

## Recommended order

1. Freeze reproducible traces and treat the current 45-question set only as development regression.
2. Curate and version the missing official sources.
3. Preserve document hierarchy and create structured table/list facts.
4. Replace singular regex scope with typed multi-entity dialogue state and explicit clarification/reset behavior.
5. Replace permissive evidence checks with operation-specific completeness contracts.
6. Compose deterministically from an evidence plan with claim-level citations.
7. Freeze an independently authored test set.
8. Evaluate a small cross-encoder; retain it only if held-out evidence/final-answer quality improves safely.
9. Reproduce WMD as a bounded paper comparison, not as an assumed production upgrade.
10. Test local RAG only after the deterministic system passes safety gates.

## Top five changes to prioritize

1. Curate and version complete official coverage for the scope the assistant advertises.
2. Preserve heading/table/list hierarchy and create typed atomic facts with authoritative temporal metadata.
3. Introduce multi-entity typed query scope and an explicit dialogue FSM with safe inheritance/reset.
4. Replace default-true evidence acceptance with operation-specific completeness contracts.
5. Build deterministic answer plans with calculation/comparison/list support and claim-level citation validation.

## Paper conclusion

The referenced IEEE paper is most valuable for two ideas: explicit finite-state conversational control and hierarchical metadata-rich documents. Its WMD result is worth a fair ablation. It does not justify replacing BGE/RRF, and it does not provide evidence for adding RAG—the paper lists RAG as future work. Its private corpus, 100-query evaluation, unequal candidate filtering, and lack of latency/statistical reporting limit direct transfer.

## Model decision

- **BGE-base:** keep. The query prefix and normalized-cosine FAISS implementation are correct.
- **BM25 and RRF:** keep as baselines and likely production components.
- **Cross-encoder:** evaluate MiniLM first after deterministic scope/version filters; compare BGE reranker if resources permit.
- **WMD:** experiment only on a bounded candidate pool.
- **Generative LLM:** defer. A 4B quantized local model is technically plausible but not yet justified and must not control evidence sufficiency.

## Success definition

The application is ready to claim reliability only when an untouched, independently authored test set demonstrates high evidence recall and fully supported answer behavior, with zero designated wrong-year/route/programme failures and no critical unsupported numeric claims. Proposed gates are Recall@10 ≥90%, fully correct and supported behavior ≥85%, clarification and conversational state accuracy ≥90%, and complete claim-level official citations. Report confidence intervals and exact counts.

Until then, describe the system honestly as a local research prototype whose known development regression set passes, not as a proven 100%-accurate assistant.

## Immediate next action

Approve Milestones 0–2 only: baseline trace freeze, official-source coverage review, and structure-aware ingestion design/fixtures. Do not begin reranker training or RAG integration yet. The first go/no-go review should inspect source coverage, extraction fidelity, and whether the new schema can represent the currently failing totals, comparisons, deadlines, eligibility, and conversational slots without hard-coded answers.

## Audit boundary

This planning task changed no implementation code, runtime configuration, frontend, corpus, index, model, or Git history. It created only the eight Markdown reports in `planning/`. No commit or push was performed.


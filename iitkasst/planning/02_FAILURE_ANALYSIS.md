# Failure Analysis

## Method

This analysis combines static tracing with bounded live queries against the current running backend. It does not infer that every poor answer is a retrieval failure. Each failure is assigned to the earliest stage that loses required information and to any downstream stage that fails to contain the error.

## Failure taxonomy

| Class | Confirmed mechanism | Typical symptom |
|---|---|---|
| Corpus coverage | Required official source is not in the allowlist. | Abstention or a nearby but wrong topic. |
| Structure loss | Tables/headings are flattened and chunks split by word count. | Missing totals, row context, list completeness, or temporal qualifiers. |
| Scope representation | One programme/intent/year cannot express multi-entity or typed years. | Comparisons collapse to one entity; qualification years look like conflicts. |
| Dialogue resolution | Surface-reference regex plus previous-user concatenation. | Elliptical follow-ups lose semester/attribute; new queries may be over- or under-inherited. |
| Candidate hygiene | Text-only deduplication precedes metadata eligibility. | Correct route/year duplicate may be discarded. |
| Evidence validation | Unrecognized intents default to supported. | Relevant-domain but wrong-attribute evidence is accepted. |
| Answer planning | Lexical sentence extraction without operation semantics. | A sentence about submission answers a deadline question; a tuition row answers a total-cost question. |
| Evaluation leakage | Development questions and facts shaped implementation. | Perfect saved regression scores do not predict novel-query reliability. |

## Confirmed runtime failures

### 1. Total fees over eight semesters

Query: “How much will a B.Tech student pay in total over all eight semesters in 2026?”

**Trace.** `intent_in` classified the request as generic `fees`; no aggregate operation or complete component set was represented. Dense retrieval found fee rows, while BM25 included weaker results. Fusion retained fee evidence. Selection chose tuition, hostel, and mess-related chunks, but `evidence_set_sufficient` did not require every semester/component needed for a total. `grounded_answer` selected one full tuition row and performed no arithmetic.

**Primary root cause:** `college_query.py::intent_in` and `QueryScope` do not represent aggregate-total semantics.  
**Containment failure:** `college_select.py::evidence_set_sufficient` treats generic fees as sufficient.  
**Output failure:** `college_answer.py::grounded_answer` lacks a structured fee calculator and completeness check.

This is not primarily a BGE or RRF failure; the necessary fee material was substantially retrieved.

### 2. Compare CSE and ECE

Query: “Compare the CSE and ECE programmes.”

**Trace.** `programme_in` returned only B.Tech ECE because it tests and returns a single programme. CSE candidates appeared in retrieval but became ineligible under the resolved ECE scope. Selection and composition therefore produced only an ECE description.

**Primary root cause:** `college_query.py::programme_in` and the singular `QueryScope.programme`.  
**Downstream behavior:** `eligible` correctly enforced the wrong, lossy scope; answer composition had no comparison plan.

This is a query-understanding/schema defect, not a retrieval miss.

### 3. PhD eligibility

Query: “What are the eligibility requirements for PhD admission?”

**Trace.** Scope recognized PhD but mapped the attribute to generic admissions. A correct PhD list stub ranked first in fused retrieval. Selection also accepted B.Tech admission procedure and scholarship evidence because generic admissions defaults to supported. Lexical answer construction then selected a B.Tech seat sentence.

**Primary root cause:** no explicit eligibility intent/attribute in `intent_in`.  
**Containment failure:** `supports_request` defaults to `True` for unmodeled requests.  
**Output failure:** sentence overlap can outrank entity/attribute entailment.

Retrieval succeeded at rank 1; selection and answer construction converted success into an irrelevant answer.

### 4. Final application deadline

Query: “When is the final deadline to apply for B.Tech in 2026?”

**Trace.** The request became generic admissions. Portal-guide chunks ranked highly. No selected evidence contained a verified deadline, but the sufficiency layer accepted general admissions text and the composer returned “FINAL SUBMIT” instructions as if they answered a date question.

**Primary root cause:** missing deadline/date attribute representation.  
**Containment failure:** no requirement that evidence include the requested date type.  
**Correct behavior with the current corpus:** abstain or ask for a more specific admission route if no authoritative deadline is present.

### 5. Elliptical fee follow-up

Conversation: first-semester B.Tech tuition fee for 2026 → “How much is that?”

**Trace.** Context was recognized and programme/year were inherited, but the prior semester and requested fee component were not carried as durable typed slots. Retrieval and composition returned an all-semester tuition row rather than the first-semester amount.

**Primary root cause:** `resolve_scope` reconstructs scope from text instead of updating a dialogue-state object.  
**Containment failure:** selection does not require exact semester/component coverage for generic follow-up phrasing.

### 6. Broad postgraduate programme request

Query: “What postgraduate programmes are currently offered?”

**Trace.** No postgraduate entity/group is represented. The system returned B.Tech, e-M.Tech, and PhD-adjacent chunks. Corpus coverage for current postgraduate programmes is also incomplete.

**Primary root cause:** missing programme-level ontology and corpus coverage.  
**Correct behavior now:** qualify or abstain; after corpus expansion, list only verified current postgraduate offerings.

### 7. New-question ambiguity after context

Conversation: B.Tech CSE 2026 → “What is the fee?”

The second message has no recognized reference marker, so it is treated as standalone and loses the prior programme/year. This shows that the continuation gate is too lexical for ordinary conversation. Conversely, automatically inheriting every short message would contaminate real topic switches; explicit slot-state and reset rules are required.

## Why saved results are not evidence of general reliability

The repository records a baseline of 17/45 strict successes, 21 irrelevant responses, four unnecessary abstentions, 0/3 correct follow-ups, and Recall@10 of 77.8%. A later run records 45/45 with Recall@10 of 83.3%, MRR 0.7114, nDCG 0.7357, p50 2,023 ms, and p95 2,868 ms.

The later score is a development-regression result, not independent accuracy:

- the same 45 questions were repeatedly used to guide changes;
- expected answers are checked mainly with required/forbidden substrings;
- some exact expected facts appear directly in answer code;
- citation support only verifies that emitted text occurs in selected evidence, not that it answers the question;
- the dataset describes itself as agent-authored/agent-verified, not independently human-authored;
- there is no untouched final test set, uncertainty estimate, or external adjudication.

Therefore the current evidence supports “the known regression set is passed,” not “the assistant is 100% accurate.”

## Root-cause priority

1. **Coverage and versioning:** no selector can answer facts absent from the corpus.
2. **Typed query/dialogue schema:** retrieval cannot preserve distinctions the scope object cannot represent.
3. **Structure-aware ingestion:** totals, comparisons, tables, and complete lists need atomic facts plus parent context.
4. **Evidence contract:** unknown intents must not default to sufficient.
5. **Answer plan:** determine operation and required facts before phrasing an answer.
6. **Ranking refinement:** reranking is useful only after the preceding correctness constraints are in place.

Changing BGE, FAISS, or RRF first would not fix the confirmed comparison, deadline, follow-up, or aggregation failures.

## Issue verification matrix

| Issue | Evidence status | Severity | Affected module | Proposed correction | Verification |
|---|---|---:|---|---|---|
| Singular programme scope | **Confirmed by code and runtime** | Critical | `college_query.py` | Represent `programmes[]` and comparison targets. | CSE/ECE and B.Tech/e-M.Tech comparisons retain both entities through selection. |
| Unknown intents default to sufficient | **Confirmed by code and runtime** | Critical | `college_select.py` | Closed set of operation contracts; unknown becomes clarify/abstain. | PhD eligibility and deadline cases cannot select wrong-attribute evidence. |
| Flat table/list chunks | **Confirmed by code and corpus inspection** | High | `college.py` | Hierarchical nodes and atomic table/list facts. | Reviewed fee tables reconstruct headers, semesters, amounts, units, and totals. |
| Text-only pre-filter dedupe | **Confirmed by code and duplicate data** | High | `retrieval.py` | Metadata-aware lineage dedupe after safety handling. | Route/year-specific duplicates remain available and only equivalent scoped facts collapse. |
| Dialogue loses prior slots | **Confirmed by code and runtime** | High | `college_query.py` | Typed state with per-slot inheritance provenance. | Elliptical fee follow-up inherits semester/component; explicit new topic resets. |
| Missing official categories | **Confirmed from manifest/chunk inventory** | Critical for broad scope | source manifest/ingestion | Curate authoritative e-M.Tech, PhD, TPC, calendar, department, and facility sources. | Coverage matrix and answerability labels show every advertised category supported. |
| Regex metadata mistakes qualification years for conflicts | **Confirmed by code and examples** | High | `college.py`, `college_query.py` | Typed temporal extraction and review. | Passing-year text no longer invalidates an admission-year source. |
| Hard-coded source facts in composer | **Confirmed by code** | High | `college_answer.py` | Move values to structured facts and generic rendering. | Source update changes output after rebuild without code edits. |
| RRF parameters may be suboptimal | **Hypothesis; not demonstrated** | Medium | `search.py`, config | Tune only after data/schema fixes using development data. | Same-pool ablation with confidence intervals. |
| Cross-encoder may improve top-order ranking | **Hypothesis** | Medium | future reranker | Controlled MiniLM/BGE reranker experiment. | Held-out nDCG/final-answer gain with no safety or latency regression. |

## Reproduction and validation guidance

Preserve the current corpus/index hashes and capture `/api/chat` plus debug traces for the five confirmed novel cases above before making changes. For each run, save the normalized scope, BM25 top 10, dense top 10, fused top 10, eligibility rejection reasons, selected evidence, answer plan/answer, and timing. Re-run the exact cases after each relevant milestone. Use `uv run python -m pytest -q` for the current test suite; the shorter `uv run pytest -q` command presently hits a stale console-script path from the directory rename and should not be treated as a product test failure. Keep all new cases in the development regression split, not the untouched final test.


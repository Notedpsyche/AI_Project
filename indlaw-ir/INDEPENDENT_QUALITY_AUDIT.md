# IIIT Kottayam AI Assistant — Independent Quality Audit

Audit date: 9 October 2026  
Repository: `indlaw-ir`  
Evaluation status: **agent-authored and agent-verified; not independently human-validated**  
Production changes during audit: **none**

## 1. Executive summary

The assistant is **not ready for an open-ended college demonstration**. It is suitable only for a tightly scripted internal demonstration using previously verified questions.

The frozen 45-question audit produced:

- 15 fully correct answers among 36 answerable questions (`41.7%`).
- 2 correct abstentions among 9 unanswerable questions (`22.2%`).
- 17 strict successes among all 45 questions (`37.8%`).
- 24 incorrect answers and 4 unnecessary abstentions.
- 0/3 correct conversational follow-ups.
- 100% claim-to-citation support among 39 non-refusal responses, but 21 responses were question-irrelevant despite quoting their cited source accurately.
- Fused retrieval Recall@10 of `77.8%`, materially better than final-answer correctness.

The central reliability defect is therefore not citation fabrication. It is that the system can return a perfectly cited passage that does not answer the question. Intent/context resolution, evidence sufficiency, and sentence selection fail more often than the underlying retrievers.

No application code, corpus file, index, model, ranking parameter, or answer-composition rule was modified during this audit.

## 2. Deliverables and reproducibility

| Artifact | Purpose |
| --- | --- |
| `evaluation/independent_questions.jsonl` | Frozen 45-question dataset, expected behaviour, relevant chunks, passages, URLs, and context. |
| `results/college/independent_evaluation.json` | Full machine-readable results, BM25/dense/RRF top tens, selected evidence, API output, metrics, and manual failure diagnoses. |
| `results/college/independent_evaluation_api.jsonl` | Raw live FastAPI responses and end-to-end latency. |
| `evaluation/run_independent_evaluation.py` | Evaluation-only runner. |
| `evaluation/review_independent_results.py` | Evaluation-only manual-review annotations and metric recomputation. |

Frozen dataset SHA-256:

```text
4d849f726481afc11950465a2bb9981b72b63562719b8fe8f54c3a94e8dcb60a
```

Evaluated corpus SHA-256:

```text
d8165bb665a8fa3274b9be99f5bff54aa6bc97fdd8a4327c96e18622a865aa12
```

## 3. Dataset construction and limitations

The dataset was frozen before the assistant was executed. It contains 45 questions:

- 36 answerable from the current corpus.
- 9 requiring abstention because the requested information is not in the current corpus.
- 42 standalone questions.
- 3 conversational follow-ups.

Coverage includes admissions, programmes, reporting requirements, fees, scholarships, placements, departments/academics, campus services, ambiguity, multi-evidence questions, and conversational ellipsis.

Questions were not copied from `development_regressions.jsonl`, the two previously fixed failures, or exact test literals. Expected answers were constructed from the locally collected official pages/PDF, not from assistant responses. Verification references include the official [2026 UG admission material](https://www.iiitkottayam.ac.in/#!/admission26), [admission overview](https://www.iiitkottayam.ac.in/#!/admission), [fee table](https://www.iiitkottayam.ac.in/views/fees.html), [scholarship page](https://www.iiitkottayam.ac.in/#!/scholarship), programme pages, and the official 2026 admission-process PDF.

Limitations:

1. The set was authored and verified by the evaluating agent, not by independent human annotators.
2. It is independent of development questions but is not a definitive unbiased benchmark.
3. Relevance judgments identify canonical supporting chunks. Equivalent duplicate passages may exist elsewhere in the corpus, so retrieval metrics are deliberately strict and sometimes conservative.
4. There are only three conversational cases and nine unanswerable cases; subset percentages have high uncertainty.
5. Official content was evaluated from the source snapshot collected on 9 October 2026. Future source changes require a new audit.

## 4. Execution method

Every user-visible answer came from the running FastAPI `POST /api/chat` endpoint. For each case, a read-only local `SearchEngine` invocation mirrored the backend's context decision and captured:

- BM25 top 10.
- BGE/FAISS dense top 10.
- RRF fused top 10.
- Resolved scope and context decision.
- Eligibility and selected evidence.
- Actual cited evidence and answer.
- End-to-end HTTP latency.

The full trace is in `results/college/independent_evaluation.json`; the report below summarizes it without hiding unsuccessful cases.

## 5. Overall metrics

| Metric | Result | Denominator |
| --- | ---: | ---: |
| Strict correctness, including correct abstentions | 17/45 (`37.8%`) | All cases |
| Fully correct and complete answer | 15/36 (`41.7%`) | Answerable cases |
| Correct abstention | 2/9 (`22.2%`) | Unanswerable cases |
| Unnecessary abstention | 4/36 (`11.1%`) | Answerable cases |
| Incorrect response | 24/45 (`53.3%`) | All cases |
| Correct but incomplete | 0/45 | All cases |
| Partially correct | 0/45 | All cases |
| Unsupported/hallucinated factual claim | 0/39 (`0%`) | Non-refusal responses |
| Question-irrelevant response | 21/45 (`46.7%`) | All cases |
| Claim-level citation support | 39/39 (`100%`) | Non-refusal responses |
| Conversational correctness | 0/3 (`0%`) | Conversational cases |

“Citation support” means the cited source text contains the emitted claim. It does **not** mean the claim answers the user's question. The 21 irrelevant responses are the clearest demonstration of that distinction.

## 6. Category-wise performance

| Category | Strict successes | Failures | Strict rate |
| --- | ---: | ---: | ---: |
| Admission procedure | 3/5 | 2 | 60.0% |
| Programmes | 3/6 | 3 | 50.0% |
| Eligibility and requirements | 3/7 | 4 | 42.9% |
| Fees | 3/7 | 4 | 42.9% |
| Scholarships | 2/4 | 2 | 50.0% |
| Placements | 1/3 | 2 | 33.3% |
| Departments and academics | 1/4 | 3 | 25.0% |
| Campus services | 0/4 | 4 | 0.0% |
| Ambiguous standalone questions | 1/2 | 1 | 50.0% |
| Conversational follow-ups | 0/3 | 3 | 0.0% |

The single placement success is a correct abstention, not a placement answer.

## 7. Retrieval performance

Metrics are macro-averaged over the 36 answerable questions with explicit relevant-chunk judgments.

| Metric | Result |
| --- | ---: |
| Recall@5 | 0.7222 |
| Recall@10 | 0.7778 |
| MRR@10 | 0.6559 |
| nDCG@10 | 0.6802 |

At least one canonical judged chunk was present in fused top 10 for 28/36 answerable cases. At least one canonical judged chunk survived evidence selection for 21/36. Nevertheless:

- 15 cases failed even though a judged relevant chunk was in fused top 10.
- 8 cases failed even though a judged relevant chunk was already selected.

This shows that replacing BM25/BGE/RRF is not the first corrective action. Retrieval misses exist, but the more frequent losses occur after or alongside retrieval.

## 8. Citation correctness and answer relevance

All 39 non-refusal answers were extractive, and every displayed citation supported its associated text. There were no citation-rank mismatches and no generated factual claims absent from the cited evidence.

However, seven of nine unanswerable questions received a cited but non-responsive passage rather than an abstention. Examples include:

- A transfer-certificate checklist item in response to a 2026 placement-count question.
- A CSE curriculum sentence in response to a recruiter question.
- ECE extracurricular text in response to “Who is the CSE department head?”
- Institute phone numbers in response to hotel phone numbers and nightly prices.

The current safety condition checks whether a sentence can be extracted from evidence, not whether the evidence covers all requested attributes.

## 9. Abstention analysis

Only two unanswerable questions were handled safely:

- `ind030`: latest average salary package.
- `ind041`: context-free “How much is it?”

Seven unanswerable questions received irrelevant cited answers. Four answerable questions were unnecessarily refused:

- `ind005`: post-submission confirmation and report.
- `ind013`: character-certificate rule for a student who passed Class 12 in 2024.
- `ind022`: comparison of two first-term ₹330 charges.
- `ind033`: whether ECE blends electronics and Computer Science.

The assistant is therefore both under-conservative and over-conservative, depending on which intent rule fires.

## 10. Conversational performance

All three follow-ups failed:

| Case | Follow-up | Context decision | Result |
| --- | --- | --- | --- |
| `ind043` | “Do I actually have to show up in person?” | Standalone | Returned a DASA passport item instead of offline reporting dates. |
| `ind044` | “And the next semester?” | Standalone | Lost the hostel-fee subject and returned ECE programme content. |
| `ind045` | “What does it concentrate on in the later semesters?” | Used context, but inherited generic CSE | Filtered out the Cyber Security evidence and returned regular CSE content. |

The first two expose a narrow follow-up reference detector. The third exposes programme-resolution ordering: `CSE` is detected before the more specific `Cyber Security` specialization.

## 11. End-to-end latency

The backend was already loaded before execution. Latency includes local HTTP transport, context resolution, hybrid retrieval, evidence selection, and answer construction.

| Metric | Time |
| --- | ---: |
| p50 | 1138.3 ms |
| p95 | 1659.7 ms |

This is acceptable for a local demonstration. Reliability, not latency, is the blocking issue.

## 12. Root-cause totals

A failure may have more than one contributing cause.

| Root cause | Failure cases |
| --- | ---: |
| Query intent or context-resolution failure | 17 |
| Evidence eligibility or selection failure | 15 |
| Extractive answer-composition limitation | 11 |
| BM25 or dense retrieval failure | 4 |
| Missing official source coverage | 3 |
| Wrong source metadata | 1 |
| RRF-specific ranking defect | 0 isolated cases |
| Citation mismatch | 0 |
| Deployment-state issue | 0 |

Severity assignments: 4 Critical, 21 High, and 3 Medium.

## 13. Individual failure cases

The machine-readable result contains complete BM25, dense, and RRF top-ten rows with titles, chunk IDs, scores, source URLs, metadata, eligibility, and selected evidence. The table below records the decisive trace and diagnosis for every failure.

| ID | Question and expected behaviour | Actual behaviour | Relevant retrieval/selection evidence | Exact stage and severity | Recommended correction |
| --- | --- | --- | --- | --- | --- |
| `ind004` | Portal section count → seven mandatory steps | Returned the login sentence | `ebc44…` RRF #3, selected #2 | Answer composition — **High** | Rank sentences for requested count and obligation terms. |
| `ind005` | Confirmation email and printable report | Asked for JoSAA/DASA route | Judged portal chunks RRF #1/#2; none selected | Intent/route gate — **High** | Separate output-document questions from admission-checklist intent. |
| `ind007` | List MnC career/research areas | Returned generic mathematical-foundation sentence | Career list `eedc57…` RRF #1, selected #2 | Answer composition — **Medium** | Support list-bearing answers for areas/fields/careers. |
| `ind010` | Two e-M.Tech subject groups | Returned B.Tech admission procedure | e-M.Tech list `fde33…` RRF #1, not selected | Intent and selection — **High** | Resolve named programme-list intent before generic admissions. |
| `ind011` | PhD disciplines | Returned B.Tech seat-allocation sentence | PhD list `ba2a99…` RRF #1, selected #3 | Intent/composition — **High** | Preserve structural PhD list evidence through composition. |
| `ind013` | 2024 Class-12 character-certificate condition | Asked for admission route | Judged row outside RRF top 10 | Year semantics/context — **High** | Distinguish passing year from admission year; avoid unnecessary route gate. |
| `ind014` | Aadhaar copy in JoSAA checklist | Returned reporting dates | Aadhaar row `077450…` RRF #1, not selected | Topic/selection — **High** | Recognize photocopy/Aadhaar as checklist-document intent. |
| `ind015` | DASA passport-photo count | Returned reporting dates | Photograph row `d05fa7…` RRF #2, not selected | Topic/selection — **High** | Recognize photos/photographs as document items. |
| `ind017` | Required vaccination records | Returned remaining-fee warning | Reporting-notes evidence `60f72…` RRF #1; wrong evidence selected | Topic/selection — **High** | Recognize vaccination/medical records and require subject support. |
| `ind019` | Third-semester mess advance | Returned orientation date | Canonical fee row absent from RRF top 10 | Intent/retrieval — **High** | Map named charge types such as mess advance to fees and semester rows. |
| `ind022` | Compare club and sports-equipment charges | Refused | Both canonical rows absent from RRF top 10 | Intent/retrieval/composition — **High** | Normalize charged/amount to fee and support two-row comparisons. |
| `ind023` | Total first-semester charges | Returned tuition only | Total-bearing summary `a03308…` RRF #2, selected #2 | Answer composition — **High** | Give “total” priority over component charges. |
| `ind024` | Alumni charge amount and recurrence | Returned B.Tech admission procedure | Alumni row `0ec1f3…` RRF #9, not selected | Intent/selection — **Medium** | Normalize charge/amount to fees and prioritize exact fee names. |
| `ind027` | Whether institute forwards scholarship paperwork | Returned State-Government application sentence | Scholarship chunk RRF/selected #1 | Answer composition — **Medium** | Match action-object pairs such as forward + documents. |
| `ind029` | Scholarship names, amounts, income limits → abstain | Returned generic scholarship policy | Requested attributes absent from corpus | Evidence sufficiency — **High** | Require coverage of every requested attribute or abstain. |
| `ind031` | 2026 placement count → abstain | Returned transfer-certificate row | No relevant placement evidence | Intent/sufficiency — **Critical** | Recognize “secured jobs” and require placement-outcome evidence. |
| `ind032` | Recent CSE employers → abstain | Returned CSE curriculum sentence | No recruiter evidence | Intent/sufficiency — **Critical** | Recognize employer/hired/recruiter language and require recruiter evidence. |
| `ind033` | ECE electronics/CS mix | Refused | ECE description `d7818…` RRF/selected #1 | Intent/composition — **High** | Map curriculum/content questions to programme description and mix↔blend. |
| `ind035` | Current CSE department head → abstain | Returned ECE extracurricular sentence | Requested person/role absent | Coverage/selection — **High** | Require person/role support and abstain when absent. |
| `ind036` | Laboratory-building locations → abstain | Returned B.Tech admission procedure | Requested locations absent; broad facilities metadata survives | Metadata/sufficiency — **High** | Tighten facility metadata and require location/laboratory terms. |
| `ind037` | First-year male housing arrangement | Returned second-year housing sentence | Correct chunk `6418d…` RRF/selected #1 | Answer composition — **Critical** | Match temporal qualifier “first-year” within multi-fact chunks. |
| `ind038` | Hostel room items and ₹2,650 cost | Returned first-year hostel-location sentence | Items chunk `60f72…` RRF #1, not selected | Evidence selection — **High** | Require item nouns and cost terms during selection. |
| `ind039` | Free travel from rented hostels | Returned second-year housing sentence | Correct conveyance chunk RRF/selected #1 | Answer composition — **High** | Normalize travel/transport/conveyance and select the matching sentence. |
| `ind040` | Hotel contacts and nightly prices → abstain | Returned institute phone numbers and hotel-list link | Requested hotel details absent | Coverage/sufficiency — **High** | Do not substitute nearby contact data; abstain on missing attributes. |
| `ind042` | Context-free “When should I come?” → abstain | Returned DASA passport requirement | No resolved event/year | Underspecification/selection — **High** | Require resolved event scope before answering dates. |
| `ind043` | Follow-up: whether JoSAA student must report in person | Returned DASA passport requirement | Context not used; reporting chunk outside RRF top 10 | Context detection — **Critical** | Recognize in-person/show-up conversational ellipsis. |
| `ind044` | Follow-up: next hostel-fee semester | Returned ECE programme content | Context not used; canonical row outside RRF top 10 | Context detection — **High** | Carry fee component and semester ordinal for next/previous follow-ups. |
| `ind045` | Follow-up: later Cyber Security semesters | Returned regular CSE foundation | Cyber chunk RRF #1 but excluded; regular CSE selected | Programme resolution — **High** | Resolve specific specialization before generic CSE. |

## 14. Top five recommended improvements

These are recommendations only; none was implemented.

### 1. Fix intent, entity, and conversational scope resolution

Highest impact. This cause appears in 17 failures and all three conversational failures. Add explicit handling for programme level (`B.Tech`, e-M.Tech, PhD), specialization specificity, document-item vocabulary, named fee components, employment language, qualification year versus admission year, and contextual expressions such as “next semester” and “show up in person.”

### 2. Add an evidence-sufficiency gate tied to requested attributes

Before answering, verify that selected evidence contains the requested entity and every required attribute: e.g. employer + date, hotel + contact + price, scholarship + scheme + amount + income limit. If not, abstain. This addresses the most dangerous pattern: accurately cited but irrelevant text.

### 3. Make answer extraction task-aware

The composer needs separate, deterministic handling for lists, counts, comparisons, totals, named table rows, and temporal qualifiers. Relevant evidence was already selected in eight failed cases, so better retrieval alone cannot fix them.

### 4. Tighten chunk metadata and add official sources only for intended scope

Remove broad facility/department tags from chunks that do not actually cover those subjects. If placements, staff roles, laboratory locations, or hotel details are intended product features, add curated official sources; otherwise those intents must always abstain.

### 5. Improve retrieval for named checklist and fee terminology, then re-evaluate

Normalize terms such as `charge`, `amount`, `mess advance`, `photos`, `vaccination records`, and semester ordinals. Preserve table/list structure and consider field-aware retrieval. Evaluate these changes on a new frozen set before considering a learned reranker.

## 15. Reranker and grounded-LLM assessment

A learned reranker is **not the first justified change**. Only four failures include a clear BM25/dense retrieval miss, while 15 fail despite judged evidence in fused top 10 and eight fail despite judged evidence being selected. A reranker could help some named-fee/checklist cases, but it would not fix context loss, wrong intent, missing-source questions, or wrong-sentence extraction.

A grounded LLM is also **not yet justified as the primary fix**. It could improve sentence synthesis and multi-part answers, but without a strong sufficiency gate it may turn the current irrelevant-extraction problem into fluent unsupported answers. If later evaluated, it should receive only selected evidence, be required to abstain on missing attributes, and undergo claim-level citation verification.

## 16. Demonstration-readiness verdict

**Not ready for an open-ended college demonstration.** The blocking evidence is:

- `37.8%` overall strict correctness.
- `41.7%` complete correctness on answerable questions.
- `22.2%` correct abstention on unavailable information.
- `0/3` conversational follow-ups correct.
- `0/4` campus-service cases successful.
- Critical misleading answers for placements and first-year housing.

A limited scripted demonstration is possible only with a fixed set of previously verified questions, visible citations, and a clear warning that the assistant is not yet reliable for arbitrary applicant questions. The next development cycle should address the five recommendations above and then use a new, separately authored held-out audit.

## 17. Stop condition

Phases 1–3 are complete. No recommended fix has been implemented. Further application changes require explicit approval.

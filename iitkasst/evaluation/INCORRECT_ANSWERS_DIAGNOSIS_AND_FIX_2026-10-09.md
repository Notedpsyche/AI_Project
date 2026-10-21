# IIIT Kottayam Assistant — Incorrect-Answer Diagnosis and Fix Report

Date: 9 October 2026  
Project: `iitkasst` (IIIT Kottayam Applicant Assistant)
Corpus at verification: 98 local chunks from 10 allowlisted official sources  
Corpus SHA-256: `d8165bb665a8fa3274b9be99f5bff54aa6bc97fdd8a4327c96e18622a865aa12`

## 1. Executive finding

Both reported failures were reproduced before changing the code. Neither failure was caused by an absence of relevant official material, and neither required replacing BM25, BGE, FAISS, or RRF.

- **Failure A was primarily an evidence-selection failure, aggravated by a bad HTML section boundary.** The correct admission-process text was already present in the candidate pool. It was rejected because the selector compared the raw token `apply` with source wording such as `admission` and `application`, producing zero lexical overlap. A mixed HTML block also mislabeled the admission procedure as a DASA-fee section.
- **Failure B was an intent/metadata/selection failure, not simply a retrieval failure.** The retrievers returned programme descriptions, but source-wide `programmes` metadata made unrelated certificate and fee chunks eligible. The selector then treated the generic word `available` as a discriminative query term and promoted the category-certificate chunk because that chunk happened to contain that word.

The fixes add general intent representation, normalized query terms, chunk-level topics, semantic section boundaries, intent-aware eligibility, structural programme-list selection, and intent-aware extractive composition. The retrieval architecture was preserved.

The live API was also found to be running an old Python process after the code/index update. Restarting only the backend listener was required before the browser could use the fixed code. This was a deployment-state issue in addition to the two code defects.

## 2. Actual pipeline

| Stage | Actual implementation | Behaviour |
| --- | --- | --- |
| HTTP chat request | `backend/api/routes.py::chat` | Accepts the question and conversation, calls retrieval, builds the final answer, and returns only cited evidence. |
| Context, topic, programme, year, and intent | `backend/services/college_query.py::resolve_scope` | Produces `QueryScope`; decides whether bounded conversation context is used and resolves programme/year/topic/intent. |
| Query reformulation | `backend/services/retrieval_service.py::RetrievalService.search` and `src/doc2dial_retrieval/search.py::SearchEngine.build_query` | If scope resolution chooses context, prepends the most recent user question. These two observed questions are standalone, so no history is prepended. |
| BM25 retrieval | `src/doc2dial_retrieval/search.py::SearchEngine._retrieve` → `src/doc2dial_retrieval/retrieval.py::BM25Store.search` | Retrieves lexical candidates. |
| Dense retrieval | `SearchEngine._retrieve` → `DenseStore.search` | Encodes with `BAAI/bge-base-en-v1.5` and searches normalized vectors in FAISS. |
| Fusion | `SearchEngine.search_all` → `src/doc2dial_retrieval/retrieval.py::hybrid` | Reciprocal-rank fusion with configured `rrf_k`; no learned reranker is active. |
| Scope eligibility and evidence selection | `backend/services/college_query.py::eligible` → `backend/services/college_select.py::select_evidence` | Removes year/programme/intent conflicts and scores inspectable query/evidence features. |
| Answer construction | `backend/services/college_answer.py::grounded_answer` | Deterministically extracts and composes supported text; it does not call Gemini, OpenAI, Ollama, or another answer-generating LLM. |
| Abstention | `grounded_answer` | Refuses when no selected evidence can support a response. There is no arbitrary cosine cutoff controlling the final answer. |

No trained reranker is deployed: `models/college_reranker.json` does not exist. The code can load one only when a future artifact exists, has a compatible schema and corpus hash, and explicitly sets `deploy: true`.

## 3. Trace conventions and source metadata

The trace utility is `src/trace_college.py`. It records the scope, the first ten BM25, dense, and fused results, eligibility, selected evidence, answer, and refusal reason.

Relevant source metadata:

| Source ID | Title | Programme | Year | Type | Canonical source |
| --- | --- | --- | --- | --- | --- |
| `ug-admission-2026` | UG Admission 2026 | B.Tech | 2026 | HTML | <https://www.iiitkottayam.ac.in/#!/admission26> |
| `admission-overview` | Admission overview | Unspecified | Not year-bound | HTML | <https://www.iiitkottayam.ac.in/#!/admission> |
| `admission-portal-guide-2026` | B.Tech admission portal application process 2026 | B.Tech | 2026 | PDF | <https://www.iiitkottayam.ac.in/data/pdf/BTech_Admission_Student_Application_Process_2026.pdf> |
| `btech-cse`, `btech-ece`, `btech-cyber`, `btech-ai`, `btech-mnc` | Programme pages | Specific B.Tech programme | Not year-bound | HTML | Official programme pages in `configs/college_sources.json` |

Scores below are raw scores from their respective retrievers; BM25 and cosine values are not directly comparable. A dash means the result did not appear in that retriever's displayed top ten. RRF scores are rank-fusion scores.

## 4. Failure A — B.Tech application procedure

Question: **How do I apply for B.Tech in 2026?**

### 4.1 Pre-fix scope and decision

```text
programme=B.Tech
admission_year=2026
year_sensitive=true
topic=admissions
context_used=false
intent=<not represented>
```

The lack of a distinct `admission_process` intent meant that document requirements, fees, programme descriptions, and portal UI pages could not be distinguished from the actual route/process at the evidence-selection boundary.

### 4.2 Pre-fix BM25 top ten

| Rank | Chunk ID | Title / section | BM25 | Eligible before fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `ug-admission-2026::ba679eb81005e3df` | UG Admission 2026 / DASA documents | 6.7807 | yes |
| 2 | `admission-overview::e29cd6d4cf3c9bb0` | Admission overview / Undergraduate programmes | 5.3052 | no |
| 3 | `admission-overview::fde33dd53bc44dd0` | Admission overview / e-M.Tech Admission | 4.7572 | no |
| 4 | `scholarships::97cd825f583968a3` | Scholarships / Scholarship | 4.7009 | no |
| 5 | `admission-overview::ba2a99a0e47b5372` | Admission overview / PhD Admission | 4.6861 | no |
| 6 | `btech-mnc::eedc579639898699` | B.Tech Mathematics and Computing | 3.9782 | no |
| 7 | `ug-admission-2026::e7ac004ce19fb354` | UG Admission 2026 / DASA remaining fees | 3.9131 | yes |
| 8 | `ug-admission-2026::6418d78d9e207cf2` | UG Admission 2026 / portal and hostel notice | 3.7226 | yes |
| 9 | `ug-admission-2026::e6eb68f68094d76a` | UG Admission 2026 / DASA documents | 3.7171 | yes |
| 10 | `ug-admission-2026::0cac27a80e2bc73a` | UG Admission 2026 / mixed DASA-fee and admission-process block | 3.6713 | yes |

### 4.3 Pre-fix dense top ten

| Rank | Chunk ID | Title / section | Cosine | Eligible before fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `admission-portal-guide-2026::82bfb996c403f360` | Portal guide / page 6 | 0.7049 | no |
| 2 | `admission-portal-guide-2026::113593be0da155ae` | Portal guide / page 1 | 0.6970 | no |
| 3 | `admission-portal-guide-2026::99d7b7f678568d72` | Portal guide / page 3 | 0.6945 | no |
| 4 | `admission-portal-guide-2026::ebc44eab8e3de09f` | Portal guide / page 2 | 0.6892 | no |
| 5 | `admission-portal-guide-2026::c3c6569555c0d388` | Portal guide / page 5 | 0.6830 | no |
| 6 | `admission-portal-guide-2026::49700623fec12d96` | Portal guide / page 7 | 0.6800 | no |
| 7 | `ug-admission-2026::0cac27a80e2bc73a` | Mixed DASA-fee and admission-process block | 0.6789 | yes |
| 8 | `btech-fees-2026::0ec1f35fcafaff33` | B.Tech fee table | 0.6756 | no |
| 9 | `admission-overview::e29cd6d4cf3c9bb0` | Undergraduate programmes | 0.6745 | no |
| 10 | `btech-ai::c11433644010b29d` | B.Tech AI / Admission | 0.6743 | no |

### 4.4 Pre-fix RRF top ten

| Rank | Chunk ID | Section | RRF | Eligible before fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `admission-overview::e29cd6d4cf3c9bb0` | Undergraduate programmes | 0.03062 | no |
| 2 | `admission-portal-guide-2026::c3c6569555c0d388` | Page 5 | 0.02927 | no |
| 3 | `admission-portal-guide-2026::ebc44eab8e3de09f` | Page 2 | 0.02914 | no |
| 4 | `ug-admission-2026::0cac27a80e2bc73a` | Mixed DASA-fee and admission-process block | 0.02901 | yes |
| 5 | `admission-portal-guide-2026::49700623fec12d96` | Page 7 | 0.02848 | no |
| 6 | `btech-ai::c11433644010b29d` | Admission | 0.02798 | no |
| 7 | `ug-admission-2026::6418d78d9e207cf2` | Portal and hostel notice | 0.02736 | yes |
| 8 | `admission-portal-guide-2026::99d7b7f678568d72` | Page 3 | 0.02724 | no |
| 9 | `btech-cyber::c3514b2ee1d00fec` | Admission | 0.02518 | no |
| 10 | `ug-admission-2026::cb7496ad5bca0382` | First-semester fee | 0.02256 | yes |

### 4.5 Exact failure point

`backend/services/college_select.py::select_evidence` rejected every surviving candidate. Its feature gate used the unnormalized raw query terms. After generic words were removed, `apply` remained, but the official evidence used `admission` and `application`. The focus overlap was therefore zero. The correct process text was already fused at rank 4 and the portal notice at rank 7; retrieval had supplied usable evidence.

The bad HTML boundary was a second defect. The JEE Main → JoSAA/CSAB procedure lived in `ug-admission-2026::0cac27a80e2bc73a`, but inherited the previous heading `Remaining fee details for students admitted via DASA`. This made intent-specific eligibility unsafe.

The answer constructor then behaved correctly for its input: selection returned no evidence, so `grounded_answer` abstained.

### 4.6 Fix and post-fix trace

The extractor now creates a distinct `B.Tech admission procedure` section. Scope resolution now emits `intent=admission_process`, `apply/application/admissions` normalize to `admission`, and intent eligibility excludes fee/document chunks while admitting the process and appropriate portal evidence.

Post-fix RRF top ten:

| Rank | Chunk ID | Section | RRF | Eligible after fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `ug-admission-2026::6e63924cd2367402` | B.Tech admission procedure | 0.02921 | yes |
| 2 | `admission-portal-guide-2026::c3c6569555c0d388` | Page 5 | 0.02899 | no |
| 3 | `admission-portal-guide-2026::ebc44eab8e3de09f` | Page 2 | 0.02862 | yes |
| 4 | `btech-ai::c11433644010b29d` | Admission | 0.02817 | no |
| 5 | `admission-portal-guide-2026::49700623fec12d96` | Page 7 | 0.02801 | yes |
| 6 | `ug-admission-2026::6418d78d9e207cf2` | UG Admission 2026 portal notice | 0.02743 | yes |
| 7 | `admission-portal-guide-2026::99d7b7f678568d72` | Page 3 | 0.02602 | yes |
| 8 | `btech-cyber::c3514b2ee1d00fec` | Admission | 0.02431 | no |
| 9 | `ug-admission-2026::cb7496ad5bca0382` | First-semester fee | 0.02360 | no |
| 10 | `ug-admission-2026::064e9de2112d0c35` | DASA fee | 0.02208 | no |

Selected evidence after the fix:

1. `ug-admission-2026::6e63924cd2367402` — B.Tech admission procedure — final selection score `0.17421`.
2. `ug-admission-2026::6418d78d9e207cf2` — institute admission data-entry portal — `0.17243`.
3. `admission-portal-guide-2026::ebc44eab8e3de09f` — relevant portal guide page — `0.03862`; retained as supporting evidence but not needed in the two-claim answer.

Final live response:

```text
For B.Tech (admission 2026):
• Admission to the B.Tech/B.Tech-MS programme will be based on performance in the Joint Entrance Examination (JEE - Main) ... through the counselling under JoSAA/CSAB. [1]
• Admission Data Entry Portal (JoSAA/CSAB/DASA -2026): Enter the candidate details in the institute admission data entry portal via https://admission.iiitkottayam.ac.in/ and click on FINAL SUBMIT. [2]
```

## 5. Failure B — available courses/programmes

Question: **what are the available courses**

### 5.1 Pre-fix scope and decision

```text
programme=<none>
admission_year=<none>
topic=programmes
context_used=false
intent=<not represented>
```

The system knew the broad topic but did not represent the user's list intent. It could not distinguish “list the programmes” from “describe a programme” or from incidental use of programme-related words in an admission document.

### 5.2 Pre-fix BM25 top ten

| Rank | Chunk ID | Title / section | BM25 | Eligible before fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `btech-cse::0c6c7d782ff9a313` | CSE programme description | 6.7418 | yes |
| 2 | `btech-ai::cc1129a601271986` | AI and Data Science description | 6.1210 | yes |
| 3 | `ug-admission-2026::c3819a784b099b4b` | JoSAA/CSAB document requirements | 5.3045 | yes |
| 4 | `ug-admission-2026::ba679eb81005e3df` | DASA document requirements | 5.0330 | yes |
| 5 | `admission-portal-guide-2026::49700623fec12d96` | Portal guide / page 7 | 4.6251 | no |
| 6 | `btech-cyber::40aebffdbc73def2` | Cyber Security description | 4.3181 | yes |
| 7 | `scholarships::97cd825f583968a3` | Scholarship | 4.2577 | no |
| 8 | `admission-portal-guide-2026::51cc407df2391298` | Portal guide / page 4 | 3.4820 | no |
| 9 | `btech-ece::d7818d2d1c0ae031` | ECE programme description | 3.0663 | yes |
| 10 | `ug-admission-2026::e7ac004ce19fb354` | DASA fees | 2.8037 | yes |

### 5.3 Pre-fix dense top ten

| Rank | Chunk ID | Title / section | Cosine | Eligible before fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `admission-overview::fde33dd53bc44dd0` | e-M.Tech list | 0.5291 | yes |
| 2 | `btech-ai::fbcdae4fbc8d6f3b` | AI admission fragment | 0.5259 | yes |
| 3 | `btech-ai::ffd316cd9d9c17dc` | AI admission fragment | 0.5216 | yes |
| 4 | `btech-ai::f412f3659cf14302` | AI admission fragment | 0.5113 | yes |
| 5 | `btech-mnc::eedc579639898699` | Mathematics and Computing | 0.5084 | yes |
| 6 | `btech-ai::cc1129a601271986` | AI and Data Science description | 0.5045 | yes |
| 7 | `btech-cse::0c6c7d782ff9a313` | CSE programme description | 0.5025 | yes |
| 8 | `admission-overview::ba2a99a0e47b5372` | PhD list | 0.4978 | yes |
| 9 | `btech-fees-2026::9031b1d2425f8cb9` | Fee table | 0.4901 | no |
| 10 | `ug-admission-2026::6b0db82c2d4aacdf` | DASA fees | 0.4866 | yes |

### 5.4 Pre-fix RRF top ten

| Rank | Chunk ID | Section | RRF | Eligible before fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `btech-ai::cc1129a601271986` | AI and Data Science description | 0.03083 | yes |
| 2 | `btech-cse::0c6c7d782ff9a313` | CSE description | 0.03068 | yes |
| 3 | `ug-admission-2026::c3819a784b099b4b` | JoSAA/CSAB documents | 0.02577 | yes |
| 4 | `btech-cyber::40aebffdbc73def2` | Cyber Security description | 0.02515 | yes |
| 5 | `ug-admission-2026::e7ac004ce19fb354` | DASA fees | 0.02504 | yes |
| 6 | `btech-ece::d7818d2d1c0ae031` | ECE description | 0.02480 | yes |
| 7 | `scholarships::97cd825f583968a3` | Scholarship | 0.02402 | no |
| 8 | `ug-admission-2026::d2f85c311c96d6d6` | DASA documents | 0.02250 | yes |
| 9 | `btech-cyber::c3514b2ee1d00fec` | Admission | 0.02062 | yes |
| 10 | `admission-overview::fde33dd53bc44dd0` | e-M.Tech list | 0.01639 | yes |

### 5.5 Exact failure point

The source manifest labeled the entire UG Admission 2026 source with `programmes`. Before the fix, every chunk copied all source topics. Consequently, document and fee chunks were incorrectly eligible for a programmes query.

The selector removed `course` as generic but left `available` as a focus term. The category-certificate sentence contained “available on the JoSAA/CSAB-2026 website”, so it received a larger lexical bonus than the actual programme descriptions. The selected order was:

1. category-certificate chunk — final score `0.09077`;
2. DASA document chunk — `0.08063`;
3. AI programme description — `0.03583`.

The answer constructor then extracted the first high-scoring sentence. It cited the sentence correctly, but the sentence was irrelevant to the question. Citation presence alone did not provide question-to-evidence relevance.

### 5.6 Fix and post-fix trace

The extractor now assigns chunk-level topics. Document rows are `documents`, fee rows are `fees`, and structural programme sections are `programmes`. The query now resolves to `intent=programmes_list`. Programme-list eligibility rejects documents, fees, and portal instructions, and selection prefers reviewed structural list sections rather than isolated descriptions.

Post-fix RRF top ten:

| Rank | Chunk ID | Section | RRF | Eligible after fix |
| ---: | --- | --- | ---: | :---: |
| 1 | `ug-admission-2026::2aa547656f2faa42` | Available B.Tech programmes | 0.03068 | yes |
| 2 | `btech-ai::cc1129a601271986` | AI and Data Science description | 0.03041 | yes |
| 3 | `btech-cse::0c6c7d782ff9a313` | CSE description | 0.03028 | yes |
| 4 | `ug-admission-2026::c3819a784b099b4b` | JoSAA/CSAB documents | 0.02577 | **no** |
| 5 | `btech-cyber::40aebffdbc73def2` | Cyber Security description | 0.02538 | yes |
| 6 | `ug-admission-2026::e7ac004ce19fb354` | DASA fees | 0.02484 | **no** |
| 7 | `btech-ece::d7818d2d1c0ae031` | ECE description | 0.02480 | yes |
| 8 | `ug-admission-2026::d2f85c311c96d6d6` | DASA documents | 0.02223 | **no** |
| 9 | `admission-overview::6e63924cd2367402` | B.Tech admission procedure | 0.01827 | no |
| 10 | `admission-overview::fde33dd53bc44dd0` | e-M.Tech list | 0.01587 | yes |

The candidate pool extends beyond the displayed ten to the configured BM25/dense depths. The selector chose these structural sources:

1. `ug-admission-2026::2aa547656f2faa42` — B.Tech/B.Tech-MS list — `0.07818`.
2. `admission-overview::fde33dd53bc44dd0` — e-M.Tech list — `0.05587`.
3. `admission-overview::ba2a99a0e47b5372` — PhD list — `0.05351`.

Final live response:

```text
According to the official sources:
• B.Tech/B.Tech-MS: CSE, ECE, CSE with Cyber Security, CSE with AI & Data Science, and Mathematics and Computing. [1]
• e-M.Tech: AI, ML and Data Science; Cyber Security and Digital Forensics. [2]
• PhD: CSE, ECE, and Mathematics. [3]
```

## 6. Code changes

### `src/doc2dial_retrieval/college.py`

- Added `_semantic_sections` to split mixed HTML blocks into meaningful programme-list and admission-procedure sections.
- Added `_chunk_topics` so document rows, fee rows, portal instructions, programme lists, facilities, and other content no longer inherit every source-level topic.
- Rebuilt the corpus from 96 to 98 chunks and rebuilt BM25, embeddings, and FAISS indexes.

### `backend/services/college_query.py`

- Added `QueryScope.intent`.
- Added conservative term normalization for `apply/application/admissions → admission` and `course/branches/degrees → program`.
- Added general intents including `admission_process`, `admission_data_entry`, `programmes_list`, `programme_description`, and `departments_list`.
- Expanded topic recognition for placements, departments, and facilities.
- Made eligibility intent-aware and retained programme/year/route constraints.

### `backend/services/college_select.py`

- Uses normalized rather than raw query terms.
- Stops generic words such as `available`, `course`, and `programme` from acting as high-value relevance features.
- Restricts list questions to structural programme-list evidence.
- Requires subject-specific overlap for broad facilities, departments, and placements queries so unrelated “campus” or “student” text cannot answer them.
- Adds small, inspectable structural bonuses; it does not add a learned or opaque reranking model.

### `backend/services/college_answer.py`

- Composes application answers from the actual route/process and institute portal evidence.
- Preserves full roman/numeric programme lists instead of truncating them as unrelated sentences.
- Avoids attaching a year label to a broad answer assembled from mixed year-bound and non-year-bound sources.
- Continues to emit only extractive, cited claims or an abstention.

### Diagnostics and tests

- Added `src/trace_college.py` for stage-by-stage traces.
- Added `evaluation/development_regressions.jsonl` with 24 reviewed development regressions.
- Added `src/evaluate_development_regressions.py` to separate retrieval, selection, answer, citation, and abstention failures.
- Expanded `tests/test_college.py` to cover semantic splits, chunk topics, intents, eligibility, programme lists, admission procedure composition, and safe abstention.

## 7. Regression evaluation

The set contains the two observed failures plus realistic paraphrases across B.Tech admission procedure, programmes, eligibility, fees, scholarships, placements, departments, facilities, and insufficient-evidence questions. Expected content was checked against the locally collected official pages and PDFs.

This is an **agent-reviewed development regression set**, and several questions guided the fixes. It must not be reported as independent model accuracy.

| Metric | Final result |
| --- | ---: |
| Cases correct | 24 / 24 |
| Answerable cases | 16 |
| Average relevant-chunk Recall@10 | 0.9792 |
| At least one judged relevant selected evidence item | 16 / 16 (1.0000) |
| Unsupported answers | 0 |
| Irrelevant answers | 0 |
| Unnecessary abstentions | 0 |
| Citation-support failures | 0 |

| Category | Correct / cases |
| --- | ---: |
| B.Tech admission procedure | 3 / 3 |
| Available programmes | 3 / 3 |
| Eligibility | 2 / 2 |
| Tuition and hostel fees | 3 / 3 |
| Scholarships | 3 / 3 |
| Placement information | 2 / 2 |
| Academic departments | 2 / 2 |
| Campus facilities | 3 / 3 |
| Insufficient official evidence | 3 / 3 |

The one partial-recall case is the broad courses question: two of its three list chunks are in fused top ten (`2/3` Recall@10), while the third is below ten but inside the larger fused candidate pool and is selected by the structural list policy. This is why mean Recall@10 is 0.9792 rather than 1.0 even though the final selected evidence and answer are complete.

Additional verification:

- `uv run pytest -q`: **51 passed**.
- `uv run ruff check .`: **passed**.
- `npm run build` in `app/frontend`: **passed**.
- `git diff --check`: **passed**; Git emitted only expected Windows LF/CRLF notices.
- Live `POST /api/chat` after restarting the backend: both reported questions returned the corrected non-refusal answers and matching cited sections.
- Live 20-question functional smoke suite: **20 / 20 expected behaviours passed**; this is not a quality benchmark.
- Warm retrieval over the existing 20 pilot questions: p50 **926.8 ms**, p95 **1221.0 ms** on this laptop; startup, answer composition, and browser time are excluded.

## 8. Evidence verification

The official admission overview states that B.Tech/B.Tech-MS admission is based on JEE Main through JoSAA/CSAB and lists e-M.Tech and PhD areas. The 2026 UG page/portal provides the current programme list and institute data-entry instructions. The official fees page supports the development checks for tuition, hostel, and caution amounts, and the official scholarship page supports the system's limited scholarship response.

These checks validate the facts represented in the regression labels, but they do not turn the development set into an independent benchmark.

## 9. Remaining limitations and failure categories

1. **No independent held-out accuracy result yet.** A separate person should author and judge a frozen test set after development stops.
2. **Corpus coverage is deliberately narrow.** The current allowlist does not contain an authoritative all-departments list, current recruiter list, swimming-pool statement, or library hours. The correct behaviour for those questions is abstention.
3. **Programme nomenclature can change.** Current answers are bound to collected official sources; source refresh and index rebuild are required when the institute changes programme names or admission-year material.
4. **HTML/PDF layout changes remain a risk.** Structural extraction tests cover the current pages, but a redesigned page may require extractor maintenance.
5. **Broad “courses” semantics are application-oriented.** The answer returns offered programmes/degrees, not every course in every curriculum. A course-catalog feature would require curriculum sources and a separate intent.
6. **Recall@10 is not perfect for broad multi-source lists.** The structural selector currently recovers the missing PhD list from the larger candidate pool. This should be watched on an independent set.
7. **The live backend must be restarted after index/code changes** unless it is intentionally run with reload. A stale process can make corrected local code appear unfixed.

## 10. Is reranking or grounded LLM generation justified now?

**Not by these failures.** In Failure A, the correct process evidence was already fused at rank 4 before the fix. In Failure B, relevant programme evidence occupied fused ranks 1 and 2, while the irrelevant document survived because of bad topic propagation and selection features. A reranker would have treated symptoms without correcting the scope and corpus metadata defects.

The final development result is 24/24 with no learned reranker and no generative answer model. Therefore:

- Do not deploy a learned reranker merely because these two failures occurred.
- Train/evaluate one only on a frozen, independently judged set with enough hard negatives, and retain it only if ranking and safety improve without wrong-year regressions.
- A grounded LLM is not required to answer the current structured applicant questions. It could improve wording later, but it would add unsupported-generation risk and must be restricted to selected evidence with claim-level citation checks and an independent comparison.

The evidence currently supports keeping the deterministic cited extractor as the deployed answer path.

## 11. Reproduction commands

From the project directory:

```powershell
uv run python src/prepare_college.py all
uv run python src/index.py
uv run python src/trace_college.py --output results/college/observed_failures_after.json "How do I apply for B.Tech in 2026?" "what are the available courses"
uv run python src/evaluate_development_regressions.py
uv run pytest -q
uv run ruff check .
Set-Location app/frontend
npm run build
```

The detailed machine-readable pre-fix and post-fix traces are kept locally under `results/college/`; generated result artifacts are intentionally ignored by Git.

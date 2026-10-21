# IIIT Kottayam Applicant Assistant — Implementation Progress Report

**Report date:** 9 October 2026  
**Project:** `iitkasst`
**Status:** Local application and pilot-regression fixes implemented; human relevance annotation, held-out evaluation, and reranker training are still pending.  
**Important:** The 20/20 pilot smoke result is a functional regression result, not an accuracy benchmark.

## 1. Current outcome

The active application has been refactored from a Doc2Dial agency assistant into a local IIIT Kottayam applicant assistant. It now retrieves from a curated allowlist of official institute pages and one official admission PDF, carries programme/year/source provenance through the API, answers extractively with displayed citations, asks for clarification when admission route matters, and abstains when the local official corpus does not support an answer.

The existing retrieval foundation was retained:

`question + bounded history → scope resolution → BM25 + BGE-base/FAISS → RRF → eligibility and evidence selection → extractive cited answer or clarification/abstention`

No cloud LLM was added. BGE, BM25, FAISS, and RRF were not replaced.

## 2. Data and indexing completed

- Added `configs/college_sources.json`, a ten-source allowlist restricted to official `iiitkottayam.ac.in` URLs.
- Added local HTML/PDF collection and extraction in `src/doc2dial_retrieval/college.py`.
- Added the reproducible preparation command `uv run python src/prepare_college.py all`.
- Added source provenance fields: canonical URL, title, document type, programme, admission year/effective period, retrieval timestamp, and source hash.
- Kept downloaded source bytes, prepared chunks, indexes, candidate sheets, results, and model artifacts out of public Git tracking.
- Built the current local corpus from the 8 October 2026 snapshot: **10 sources and 96 chunks**.
- Rebuilt BM25 and BGE-base FAISS indexes after correcting extraction. The dense index has 768 dimensions and was built on the local RTX 4050.
- Added index integrity checks for missing files, BM25/dense metadata alignment, chunk hash, and embedding count.

### Extraction defects corrected in the latest pass

1. Very short trailing word chunks are now merged into the previous chunk. This removed the orphaned Mathematics and Computing fragment beginning “set that prepares…”.
2. Fee-table rows containing two distinct charges are split into distinct facts. The caution-deposit row no longer absorbs the later convocation-fee cell.
3. The corrected current caution-deposit chunk is `btech-fees-2026::5461a4efc2d2aaec`.
4. The corrected current Mathematics and Computing description is `btech-mnc::51bdc669d6853e50`.

## 3. Query, context, and safety behavior completed

The college path is implemented in:

- `backend/services/college_query.py` — topic, programme, year, admission-route, and follow-up scope resolution.
- `backend/services/retrieval_service.py` — execution of the existing hybrid retriever and college evidence path.
- `backend/services/college_select.py` — programme/year/route eligibility checks and question-focused evidence ranking.
- `backend/services/college_answer.py` — conservative extractive answers, citations, clarifications, and abstentions.

Current behavior includes:

- Short referential questions can inherit the previous user question.
- Explicit programme or year changes start a new scope.
- Year-specific questions cannot use a source with a different year or unresolved conflicting-year text.
- Programme-specific questions prefer the matching programme’s descriptive source over generic admission boilerplate.
- Document checklists require JoSAA/CSAB or DASA before evidence is returned.
- Route-dependent online payment questions also request the route.
- Unsupported future or absent-year requests decline to guess.
- The answer’s year label is derived from the cited passage rather than unrelated selected evidence.

## 4. Pilot failures fixed

The initial review found five answerable failures and two partial answers. The correct evidence was generally already in the candidate pool; the main problems were extraction, fact-level selection, and answer composition.

| Pilot case | Pre-fix behavior | Current behavior |
| --- | --- | --- |
| q001 — How to apply for B.Tech in 2026 | Only partial admission route | Gives JEE/JoSAA route and the institute data-entry portal/final-submit step |
| q003 — Admission data-entry portal | False refusal | Returns `https://admission.iiitkottayam.ac.in/` from official 2026 evidence |
| q007 — Caution deposit | Answered with ₹1,59,800 tuition | Returns one-time caution deposit of ₹14,000 |
| q011 — Scholarship application support | Selected unrelated earlier sentences | Returns the sentence about providing documents and forwarding applications |
| q013 — Mathematics and Computing | False refusal caused by orphan fragment | Returns the actual programme description |
| q014 — CSE programme provenance | Added an unsupported 2026 label | Uses only provenance supported by the cited programme passage |
| q015 — ECE programme | Answered with admission instructions | Returns the ECE curriculum/field description |

Additional behavior retained:

- q004 asks for JoSAA/CSAB versus DASA before listing verification documents.
- q008 safely declines to validate 2025 payment instructions from a 2026-focused corpus.
- q017, q018, and q019 abstain on unsupported future/absent-year requests.
- q020 uses the prior fee question but asks for the admission route before giving payment instructions.

## 5. Frontend and API completed

- Preserved `/api/health`, `/api/search`, and `/api/chat`.
- Extended evidence payloads with `source_url`, `programme`, `admission_year`, `retrieved_at`, and `document_type`.
- Reworded and restyled the React application for prospective IIIT Kottayam applicants.
- Added source cards with official links and provenance metadata.
- Preserved a retrieval/debug view for diagnosis.
- Verified the frontend production build successfully.

The local frontend is available at `http://127.0.0.1:5173/` while the development server is running. The backend is currently running at `http://127.0.0.1:8000/` and reports BGE-base on `cuda:0`.

## 6. Evaluation support completed

- Added `evaluation/question_bank.jsonl` with 20 pilot questions.
- Added `src/annotation_candidates.py` and regenerated the ignored local `evaluation/candidates.jsonl` against the current 96-chunk index.
- Added `evaluation/annotation_guide.md`.
- Expanded the judgment schema with `expected_behavior` values:
  - `answer`
  - `clarify`
  - `abstain`
- Added validation so answerable rows require gold evidence and a verified fact, clarification rows require a named missing attribute, and non-answer rows cannot carry answer facts.
- Added `src/evaluate_college.py` for equal-cutoff Recall@5, MRR@10, and nDCG@10 comparisons.
- Added `src/train_reranker.py` for a small logistic relevance reranker trained only from human-judged pairs.
- Added `src/smoke_college.py`, a repeatable live API check for the 20 reviewed pilot behaviors.

The refreshed candidate generation measured warmed retrieval over the 20 pilot prompts at approximately **1016.3 ms p50** and **1371.4 ms p95**. This excludes model startup, answer composition, and browser rendering.

## 7. Verification results

| Check | Result |
| --- | --- |
| Full Python test suite | **46 passed** |
| Ruff static checks | **Passed** |
| Git whitespace/error check | **Passed**; only Windows LF→CRLF notices |
| React/TypeScript production build | **Passed**; 1,896 modules transformed |
| Live 20-question API smoke | **20/20 expected behaviors passed** |
| Current corpus | **10 sources / 96 chunks** |

The live smoke test verifies required answer fragments, expected refusal/clarification state, and follow-up context use for q020. It does not substitute for independent source review or retrieval metrics.

## 8. What is not complete

The following project gates remain open:

1. **No human gold judgments exist yet.** `evaluation/judgments.jsonl` has deliberately not been fabricated from model output or the agent-authored pilot review.
2. **The 20 pilot prompts are not a held-out benchmark.** They were used for diagnosis and regression testing.
3. **The planned ~100-question set is not complete.** It still needs independent applicant-style questions, verified source sections, answer facts, and family-preserving 60/20/20 splitting.
4. **No reranker has been trained or deployed.** Training should start only after human judgments exist. It should be retained only if held-out ranking improves without regressing wrong-year, clarification, or abstention behavior.
5. **No final effectiveness claim can be made.** The 20/20 result means the repaired implementation satisfies the encoded pilot expectations; it does not mean 100% real-world accuracy.
6. **No Git commit or push was performed during this implementation continuation.** The repository still contains pre-existing and current uncommitted work. Unrelated sibling directories were not touched.

## 9. Exact next step

The next defensible step is human annotation, beginning with the refreshed local `evaluation/candidates.jsonl` and the rules in `evaluation/annotation_guide.md`:

1. Independently open the official source for each question.
2. Verify the answer fact without relying on the system answer.
3. Mark current relevant chunk IDs from `data/processed/chunks.jsonl`.
4. Assign `answer`, `clarify`, or `abstain`.
5. Review q001, q004, q008, and q020 particularly carefully because workflow scope, route ambiguity, and old-year claims require judgment.
6. Expand to approximately 100 questions and freeze the family-preserving split.
7. Run BM25, dense, and hybrid at equal cutoffs.
8. Train the reranker only on the training split, select on development, and report the untouched test result once.

Until that review is completed, the correct project description is: **working local applicant-assistant prototype with provenance-aware hybrid retrieval, source-safe answers, and a passing 20-case functional regression suite; effectiveness evaluation pending human labels.**

## 10. Useful commands

From `C:\Users\Saivarad KG\Documents\AI project\iitkasst`:

```powershell
uv sync
uv run python src/prepare_college.py all
uv run python src/index.py
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd app\frontend
npm install
npm run dev
```

Verification:

```powershell
uv run pytest -q
uv run ruff check .
uv run python src/smoke_college.py
```

Human-review preparation and later evaluation:

```powershell
uv run python src/annotation_candidates.py
uv run python src/evaluate_college.py
uv run python src/train_reranker.py
```

The last two commands require a valid human-reviewed `evaluation/judgments.jsonl`.

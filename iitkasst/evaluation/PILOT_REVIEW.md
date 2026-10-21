# IIIT Kottayam applicant-assistant pilot review

Initial review date: 2026-10-09. Reviewer: Codex (agent review, **not independent human annotation**). Scope: 20 questions in `question_bank.jsonl`, the local 2026-10-08 official-source snapshot, its **pre-fix 95 extracted chunks**, the saved top-15 hybrid candidate sheet, and live `/api/chat` responses. The item-by-item table below records the **pre-fix diagnosis**; some chunk IDs changed when the same raw sources were re-extracted into 96 chunks. These are diagnostic outcomes, **not** a held-out accuracy estimate or a `judgments.jsonl` gold set.

## Summary

| Outcome | Questions | Count |
| --- | --- | ---: |
| Directly responsive and supported | q002, q005, q006, q009, q010, q012, q016 | 7 |
| Partially useful / provenance needs correction | q001, q014 | 2 |
| Answerable from collected evidence, but app fails | q003, q007, q011, q013, q015 | 5 |
| Appropriate clarification or safe refusal | q004, q008, q017, q018, q019, q020 | 6 |

The clearest finding is **not a missing corpus** for the five failed answerable questions. The correct passage is present (within the top 9 hybrid candidates), but selection or one-passage answer composition loses the requested fact. The applicant corpus is adequate for this narrow pilot, but these outcomes do not establish broad coverage.

## Item-by-item review

`UG26` denotes the [official UG Admission 2026 page](https://www.iiitkottayam.ac.in/views/admission26.html), `FEES` the [official fee page](https://iiitkottayam.ac.in/views/fees.html), `SCH` the [scholarship page](https://iiitkottayam.ac.in/views/scholarship.html), and programme IDs their respective official pages. Candidate ranks refer to the saved *pre-fix hybrid candidate sheet*, not the final displayed evidence rank. Full IDs below identify the **pre-fix** local snapshot; do not copy them into current judgments without checking `chunks.jsonl`.

| ID | Verified evidence / answer fact | Candidate rank | Live app verdict |
| --- | --- | ---: | --- |
| q001 | `UG26::0cac27a80e2bc73a` says JEE Main followed by JoSAA/CSAB counselling; `UG26::6418d78d9e207cf2` gives the 2026 institute data-entry portal and final-submit step. | 3, 5 | **Partial.** Gives the JEE/JoSAA route but omits institute portal step. Do not imply DASA follows the same counselling route. |
| q002 | `UG26::0cac27a80e2bc73a`: JEE Main is used for B.Tech admission through JoSAA/CSAB. | 5 | **Pass.** |
| q003 | `UG26::6418d78d9e207cf2`: 2026 data-entry portal is `https://admission.iiitkottayam.ac.in/`; official [portal](https://admission.iiitkottayam.ac.in/) exists. | 2 | **Fail: false refusal.** Final evidence includes this chunk, but answer composition does not extract its URL. |
| q004 | `UG26` has separate 2026 JoSAA/CSAB and DASA verification checklists; e.g. `UG26::cd9201a5afe2de68` and `UG26::4e85d3743886f6ee`. | Both route sections appear | **Pass as clarification.** A single route-free checklist would mix requirements. This is **ambiguous**, not a conventional unanswerable question. |
| q005 | `FEES::8cf5ae1257ed36b1` and `UG26::cb7496ad5bca0382`: first-semester B.Tech tuition is ₹1,59,800 for 2026. | 1, 2 | **Pass.** |
| q006 | `FEES::c6776c9f1f8c82ba` and `UG26::a033080bf960331b`: first-semester hostel/facility maintenance is ₹37,500 for 2026. | 2, 1 | **Pass**, though the response copies the entire first-semester fee block. |
| q007 | `UG26::a033080bf960331b` and `FEES::c75c72f6011b8e69`: yes, a ₹14,000 one-time caution deposit is listed in first semester. | 3, outside top 15 | **Fail: wrong fact.** The app selects a tuition-only passage and answers ₹1,59,800 instead of caution deposit. The extracted `FEES` row also incorrectly appends a convocation-fee cell to the caution-deposit row. |
| q008 | Current 2026 sources provide 2026 payment context; this allowlist does **not** contain authoritative 2025 payment instructions or a statement that they remain valid. | — | **Pass as safe refusal.** Do not assert that 2025 instructions are valid or invalid solely from absence of evidence; point to current 2026 instructions instead. |
| q009 | `SCH::97cd825f583968a3`: the institute says it offers no direct financial assistance. | 1 | **Pass.** |
| q010 | Same `SCH` chunk: admitted students may apply directly to state governments or other authorities. | 1 | **Pass**, with an unnecessary preceding sentence about direct assistance. |
| q011 | Same `SCH` chunk: institute provides necessary documents and forwards scholarship applications to appropriate authorities. | 1 | **Fail: wrong sentence.** The app outputs the first two sentences, omitting the third sentence that actually answers the question. |
| q012 | `btech-ai::cc1129a601271986`: B.Tech CSE with AI and Data Science specialization is offered. | 1 | **Pass.** Answer describes the programme instead of saying an explicit “yes,” but is supported. |
| q013 | `btech-mnc::ebfcf7292356531f`: the official programme text explicitly says B.Tech in Mathematics and Computing. The [2026 admissions portal](https://admission.iiitkottayam.ac.in/index.php) also lists it. | 2 | **Fail: false refusal.** Final evidence rank 1 is the extraction fragment `btech-mnc::39c185632f1e2714` (“set that prepares…”); the answer generator inspects only that first passage. |
| q014 | `btech-cse::0c6c7d782ff9a313`: CSE curriculum description. | 1 | **Partial.** Description is relevant, but the response labels it “admission 2026” although the programme chunk itself has no admission-year metadata; that label is inherited from *other* selected evidence. |
| q015 | `btech-ece::d7818d2d1c0ae031`: ECE programme focus and curriculum. | 9 | **Fail: wrong task.** The app selects `btech-ece::07a51878836b62e6` (the admission boilerplate) and answers how admission works, not what ECE is. |
| q016 | `btech-cyber::40aebffdbc73def2`: B.Tech CSE with Cyber Security specialization. | 1 | **Pass.** Do not confuse it with postgraduate Cyber Security/Digital Forensics. |
| q017 | No 2030 deadline in this 2026-focused allowlist. | — | **Pass as safe refusal.** |
| q018 | No authoritative 2025 DASA fee schedule in this allowlist; 2026 fee entries cannot answer a 2025 question. | — | **Pass as safe refusal.** |
| q019 | A future 2028 placement rate cannot be verified from the applicant sources. | — | **Pass as safe refusal.** |
| q020 | History resolves “it” to a 2026 first-semester fee, but online payment instructions differ for JoSAA/CSAB versus DASA. `UG26::30cf81894dcfa490` names route-specific fee portals, though its extracted text lacks the actual portal link targets. | 11 (current candidate sheet) | **Pass as clarification.** The app uses the prior question and asks for the route. Do not turn this into a route-free “yes.” |

## What the code review shows

1. **Selection is not sufficiently fact-specific.** `backend/services/college_select.py::select_evidence` filters eligibility, then defaults to RRF plus any query-term overlap. “First semester” can select tuition for a caution-deposit question (q007); “B.Tech ECE” can select admission boilerplate over programme description (q015). This is a selection problem, not evidence absence.
2. **Answer composition discards useful selected evidence.** `backend/services/college_answer.py::grounded_answer` sets `limit = 1` for non-document topics, even when `select_evidence` returns three passages. That makes q003 and q013 false refusals when a poor first chunk wins. For scholarships, `sentences[:2]` mechanically excludes the answer-bearing third sentence in q011. Its sentence splitter also treats long HTML-joined text and URL punctuation poorly.
3. **Provenance is inferred from the whole evidence set.** `grounded_answer` collects `years` across selected passages before using only one of them. q014 therefore receives a 2026 label not established by the quoted programme-description chunk.
4. **Extraction creates misleading fragments.** `src/doc2dial_retrieval/college.py` yielded a standalone “set that prepares…” MnC chunk and a caution-deposit table row merged with a convocation-fee cell. Both can distort ranking or cited answers. Preserve source structure before treating those chunks as high-quality gold evidence.
5. **The annotation schema needs a clarification category.** `evaluation/annotation_guide.md` currently has only `answerable` true/false. q004 and q020 need a route clarification, so forcing them into a simple binary relevance label would conflate safe clarification with lack of source coverage. The 20 prompts are also concentrated in one admission year and closely related paraphrase families; they are a pilot, not a frozen 20-question test set.

## Review boundary and next gate

No `judgments.jsonl` was created, no benchmark was run, and no reranker was trained. Before measured comparison, independently confirm the answer facts and exact section IDs, define the clarification label, repair the malformed extracted chunks, and freeze a larger question-family split. A human reviewer should specifically adjudicate q001 (how much of the application workflow is required), q004/q020 (clarification handling), and q008 (what can be said about old payment instructions). Source facts and year-specific instructions should be rechecked if the official pages change after the 2026-10-08 snapshot.

## Post-fix functional rerun (2026-10-09)

The local raw sources were re-extracted into **96 chunks**, BM25/BGE-FAISS indexes were rebuilt, and the backend was restarted. `uv run python src/smoke_college.py` then observed **20/20 expected pilot API behaviors**. This checks answer fragments, refusals, and the fee follow-up's context flag; it does **not** independently judge completeness, source reachability, or answer correctness. The formerly failed q003, q007, q011, q013, and q015 now return the relevant portal, caution deposit, scholarship-support, Mathematics and Computing, and ECE-programme evidence respectively. q001 now includes both the JEE/JoSAA route and institute data-entry portal. The corrected current chunk IDs include `btech-fees-2026::5461a4efc2d2aaec` for the caution-deposit row and `btech-mnc::51bdc669d6853e50` for the MnC description.

The human review gate remains open: no `judgments.jsonl` exists, the 20 questions are not an independent held-out sample, and no training or retrieval-effectiveness claim follows from this smoke pass.

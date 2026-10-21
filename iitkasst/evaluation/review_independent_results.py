"""Apply the documented manual review to the frozen independent audit output."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/college/independent_evaluation.json"


def finding(
    classification: str,
    failure_type: str,
    roots: list[str],
    stage: str,
    severity: str,
    evidence: str,
    recommendation: str,
) -> dict:
    return {
        "classification": classification,
        "failure_type": failure_type,
        "root_causes": roots,
        "exact_failure_stage": stage,
        "severity": severity,
        "diagnostic_evidence": evidence,
        "recommended_correction": recommendation,
    }


REVIEWS = {
    "ind004": finding("incorrect", "irrelevant_answer", ["extractive_answer_composition_limitation"], "answer composition", "High", "The judged chunk is RRF rank 3 and selected rank 2, but composition quotes the login sentence from selected rank 3 instead of the mandatory seven-step statement.", "Rank candidate sentences against the complete question, including requested count/obligation terms, before composing."),
    "ind005": finding("unnecessary_abstention", "unnecessary_abstention", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "scope resolution / route gate", "High", "The two judged portal chunks are RRF ranks 1 and 2, but the word 'document' maps the question to a route-specific reporting checklist and forces route clarification.", "Separate requested output/document intent from admission-document-checklist intent; apply route requirements only to checklist/payment-route questions."),
    "ind007": finding("incorrect", "incomplete_answer", ["extractive_answer_composition_limitation"], "answer composition", "Medium", "The career-area chunk is RRF rank 1 and selected rank 2; composition emits a generic sentence from selected rank 1 and omits every requested area.", "Support list/enumeration answers and score list-bearing sentences for 'areas', 'fields', and career-list requests."),
    "ind010": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "intent resolution / evidence selection", "High", "The e-M.Tech list is RRF rank 1 but is not selected; 'admissions' wins over programme-list intent and the B.Tech admission process is returned.", "Recognize e-M.Tech/PhD programme-list requests before generic admission intent and preserve structural list evidence."),
    "ind011": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "extractive_answer_composition_limitation"], "intent resolution / answer composition", "High", "The PhD list is RRF rank 1 and selected rank 3, but composition quotes the B.Tech seat-allocation sentence.", "Represent PhD discipline-list intent and select the structural list text rather than a generic admission sentence."),
    "ind013": finding("unnecessary_abstention", "unnecessary_abstention", ["query_intent_or_context_resolution_failure", "bm25_or_dense_retrieval_failure"], "scope resolution", "High", "The Class 12 passing year 2024 is misread as admission year 2024 and the query is forced through a missing-route clarification; the judged chunk is absent from RRF top 10.", "Distinguish qualification/passing years from admission years and do not require a route when both official route checklists state the same condition."),
    "ind014": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "topic resolution / evidence selection", "High", "The Aadhaar checklist chunk is RRF rank 1, but 'photocopy' is not recognized as document intent, so general admission/reporting evidence is selected.", "Expand document-intent vocabulary and use the requested item plus route when selecting checklist rows."),
    "ind015": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "topic resolution / evidence selection", "High", "The DASA photograph chunk is RRF rank 2 but not selected because 'photos' is treated as generic admission rather than a document-list item.", "Recognize photographs/photos as document intent and prioritize exact checklist-item overlap."),
    "ind017": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "topic resolution / evidence selection", "High", "A vaccination-supporting reporting-notes chunk is RRF rank 1, yet the selector chooses a remaining-fee note because 'vaccination records' is not document intent.", "Recognize vaccination/medical records as document requirements and require subject-term support in selected evidence."),
    "ind019": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "bm25_or_dense_retrieval_failure", "evidence_eligibility_or_selection_failure"], "topic resolution / retrieval", "High", "'Mess advance' is classified as admissions, the canonical fee row is absent from RRF top 10, and the answer quotes orientation instead.", "Expand fee vocabulary to named charge types and retain semester terms in fee-row matching."),
    "ind020": finding("correct_and_complete", "", [], "none", "None", "The answer includes both requested fifth- and sixth-semester values. Extra correctly cited semester values are verbose but not false.", "Optional: trim table-row answers to the requested semesters for concision."),
    "ind022": finding("unnecessary_abstention", "unnecessary_abstention", ["query_intent_or_context_resolution_failure", "bm25_or_dense_retrieval_failure", "extractive_answer_composition_limitation"], "topic resolution / retrieval", "High", "'Charged' and 'amount' do not trigger fee intent; neither judged row appears in RRF top 10 and composition refuses despite a combined fee-summary chunk being selected.", "Recognize charge/amount as fee language and support comparison across two fee rows."),
    "ind023": finding("incorrect", "irrelevant_answer", ["extractive_answer_composition_limitation"], "answer composition", "High", "The total-fee chunk is RRF rank 2 and selected rank 2, but the composer returns first-semester tuition from selected rank 1 instead of the requested total.", "Give 'total' lexical/structural priority over component charges in fee questions."),
    "ind024": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "topic resolution / evidence selection", "Medium", "'Charge' and 'amount' do not trigger fee intent; the alumni row is only RRF rank 9 and is not selected.", "Normalize charge/amount to fee and prioritize exact named fee rows."),
    "ind027": finding("incorrect", "incomplete_answer", ["extractive_answer_composition_limitation"], "answer composition", "Medium", "The only scholarship chunk is correctly retrieved and selected, but the composer chooses its application-authority sentence rather than the requested forwarding-support sentence.", "Score action/object pairs such as forward + documents when selecting a sentence from a multi-fact chunk."),
    "ind029": finding("incorrect", "irrelevant_answer", ["evidence_eligibility_or_selection_failure", "extractive_answer_composition_limitation"], "evidence sufficiency / answer composition", "High", "The source contains no scheme names, amounts, or income limits, but a generic scholarship-policy sentence is returned instead of abstaining.", "Require coverage of requested attributes before answering; abstain when the evidence only links elsewhere."),
    "ind031": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "bm25_or_dense_retrieval_failure", "evidence_eligibility_or_selection_failure"], "intent resolution", "Critical", "'Secured jobs' is not recognized as placement intent; unrelated admission-document chunks dominate and a transfer-certificate row is returned.", "Expand placement language and enforce no-answer when selected evidence lacks employment/outcome terms."),
    "ind032": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "intent resolution", "Critical", "'Employers hired' is not recognized as placement intent; CSE programme text is selected and returned as if responsive.", "Recognize employer/hired/recruiter language and require recruiter evidence before answering."),
    "ind033": finding("unnecessary_abstention", "unnecessary_abstention", ["query_intent_or_context_resolution_failure", "extractive_answer_composition_limitation"], "intent resolution / answer composition", "High", "The judged ECE description is RRF and selected rank 1, but curriculum/mix wording is not mapped to a programme-description task and no sentence passes composition.", "Recognize curriculum/content questions as programme-description intent and normalize mix/blend wording."),
    "ind035": finding("incorrect", "irrelevant_answer", ["missing_official_source_coverage", "evidence_eligibility_or_selection_failure"], "evidence sufficiency", "High", "No department-head source exists; ECE extracurricular text is selected solely because it contains 'department'.", "Require person/role evidence for 'who is head' questions and abstain when the corpus lacks it."),
    "ind036": finding("incorrect", "irrelevant_answer", ["missing_official_source_coverage", "wrong_source_metadata", "evidence_eligibility_or_selection_failure"], "metadata / evidence sufficiency", "High", "No laboratory-location source exists, while a broad facilities tag on an AI admission chunk lets unrelated admission text answer.", "Tighten chunk-level facility metadata and require location/laboratory support before answering."),
    "ind037": finding("incorrect", "incorrect_answer", ["extractive_answer_composition_limitation"], "answer composition", "Critical", "The correct first-year housing chunk is RRF and selected rank 1, but the composer extracts its later sentence about second-year housing and omits the first-year arrangement.", "Resolve temporal qualifiers within a chunk and prefer the sentence explicitly matching first-year/2026 constraints."),
    "ind038": finding("incorrect", "irrelevant_answer", ["evidence_eligibility_or_selection_failure"], "evidence selection", "High", "The room-items chunk is RRF rank 1 but not selected; a general first-year hostel-arrangement chunk is returned.", "Require requested item nouns and cost terms in facilities evidence selection."),
    "ind039": finding("incorrect", "irrelevant_answer", ["extractive_answer_composition_limitation"], "answer composition", "High", "The correct conveyance chunk is RRF and selected rank 1, but the composer picks the second-year accommodation sentence instead of the free-transport sentence.", "Score travel/transport/conveyance equivalence and choose the sentence containing the requested service."),
    "ind040": finding("incorrect", "irrelevant_answer", ["missing_official_source_coverage", "extractive_answer_composition_limitation"], "evidence sufficiency", "High", "The corpus has only a hotel-list link, not hotel contacts or prices; the answer exposes institute phone numbers and no nightly prices.", "Detect requested attribute coverage and abstain rather than substituting nearby contact data."),
    "ind042": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "underspecification handling", "High", "The standalone question has no event/year, yet the system selects and quotes a DASA passport checklist row.", "Add a minimum resolved-scope/evidence-sufficiency requirement for underspecified standalone questions."),
    "ind043": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure"], "context detection", "Critical", "The follow-up does not match the narrow reference regex, context_used is false, the judged reporting chunk is outside RRF top 10, and a passport row is returned.", "Recognize show-up/in-person follow-ups and use conversational ellipsis/coreference beyond a small pronoun list."),
    "ind044": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure"], "context detection", "High", "'And the next semester?' does not trigger context, so the previous fee type and semester are lost; ECE content is returned.", "Recognize next/previous/same semester as contextual references and carry the fee component plus ordinal state."),
    "ind045": finding("incorrect", "irrelevant_answer", ["query_intent_or_context_resolution_failure", "evidence_eligibility_or_selection_failure"], "programme resolution", "High", "Context is used and the Cyber Security chunk is RRF rank 1, but programme parsing sees 'CSE' before 'Cyber Security', inherits generic B.Tech CSE, filters out the correct chunk, and returns regular CSE text.", "Resolve the most specific programme/specialization before generic CSE and preserve it through follow-up eligibility."),
}


def subset_summary(rows: list[dict]) -> dict:
    labels = [row["classification"] for row in rows]
    return {
        "cases": len(rows),
        "correct_and_complete": labels.count("correct_and_complete"),
        "correct_but_incomplete": labels.count("correct_but_incomplete"),
        "partially_correct": labels.count("partially_correct"),
        "incorrect": labels.count("incorrect"),
        "unsupported_or_hallucinated": labels.count("unsupported_or_hallucinated"),
        "unnecessary_abstention": labels.count("unnecessary_abstention"),
        "correct_abstention": labels.count("correct_abstention"),
    }


def main() -> None:
    report = json.loads(RESULT.read_text(encoding="utf-8"))
    for row in report["cases"]:
        row["automated_classification"] = row["classification"]
        review = REVIEWS.get(row["case_id"])
        if review:
            row.update(review)
        else:
            row["failure_type"] = ""
            row["root_causes"] = []
            row["exact_failure_stage"] = "none"
            row["severity"] = "None"
            row["diagnostic_evidence"] = "Manual review confirmed the automated strict classification."
            row["recommended_correction"] = ""
        row["manual_reviewed"] = True

    rows = report["cases"]
    answerable = [row for row in rows if row["answerable_from_current_corpus"]]
    unanswerable = [row for row in rows if not row["answerable_from_current_corpus"]]
    answered = [row for row in rows if not row["refused"]]
    categories: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        categories[row["category"]].append(row)
    summary = report["summary"]
    strict_correct = sum(row["classification"] in {"correct_and_complete", "correct_abstention"} for row in rows)
    summary.update(
        {
            "manual_review_completed": True,
            "strict_correct": strict_correct,
            "strict_correctness_rate": strict_correct / len(rows),
            "answerable_correct_and_complete": sum(row["classification"] == "correct_and_complete" for row in answerable),
            "answer_completeness_rate": sum(row["classification"] == "correct_and_complete" for row in answerable) / len(answerable),
            "correct_abstentions": sum(row["classification"] == "correct_abstention" for row in unanswerable),
            "unnecessary_abstentions": sum(row["classification"] == "unnecessary_abstention" for row in rows),
            "unnecessary_abstention_rate": sum(row["classification"] == "unnecessary_abstention" for row in answerable) / len(answerable),
            "unsupported_answer_count": sum(row["classification"] == "unsupported_or_hallucinated" for row in rows),
            "unsupported_answer_rate": sum(row["classification"] == "unsupported_or_hallucinated" for row in answered) / len(answered),
            "irrelevant_answer_count": sum(row.get("failure_type") == "irrelevant_answer" for row in rows),
            "citation_support_rate": sum(row["citation_supported"] for row in answered) / len(answered),
            "citation_support_denominator": len(answered),
            "subsets": {
                "answerable": subset_summary(answerable),
                "unanswerable": subset_summary(unanswerable),
                "standalone": subset_summary([row for row in rows if row["conversation_type"] == "standalone"]),
                "conversational": subset_summary([row for row in rows if row["conversation_type"] == "conversational"]),
            },
            "categories": {name: subset_summary(items) for name, items in sorted(categories.items())},
        }
    )
    RESULT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

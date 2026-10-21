from __future__ import annotations

from backend.services.college_answer import grounded_answer
from backend.services.college_query import eligible, resolve_scope
from backend.services.college_select import select_evidence
from doc2dial_retrieval.college import (
    _chunk_topics,
    _semantic_sections,
    _split_words,
    extract_html,
    load_manifest,
)
from doc2dial_retrieval.search import SearchEngine


def test_manifest_is_curated_and_official(tmp_path):
    path = tmp_path / "sources.json"
    path.write_text('{"schema_version":1,"sources":[{"id":"bad","fetch_url":"https://evil.example/x","source_url":"https://www.iiitkottayam.ac.in/x","document_type":"html"}]}')
    try:
        load_manifest(path)
    except ValueError as error:
        assert "Non-official" in str(error)
    else:
        raise AssertionError("External host was accepted")


def test_fee_table_keeps_first_semester_header():
    html = b"<div class='container'><h4>Fee Structure 2026</h4><table><tr><td></td><td>First Semester</td><td>Second Semester</td></tr><tr><td>Tuition Fee</td><td>100</td><td>200</td></tr></table></div>"
    rows = extract_html(html)
    assert any("Tuition Fee; First Semester: 100; Second Semester: 200" in text for _, text in rows)


def test_table_rows_keep_admission_route_heading():
    html = b"<div class='container'><h4>Admission 2026 [DASA]</h4><h5>Documents</h5><table><tr><td>1</td><td>Passport is required for verification</td></tr></table></div>"
    rows = extract_html(html)
    assert any("DASA" in heading and "Passport" in text for heading, text in rows)


def test_short_chunk_tail_is_merged_into_its_parent():
    parts = _split_words(" ".join(f"word{i}" for i in range(229)), 220)
    assert len(parts) == 1
    assert parts[0].endswith("word228")


def test_fee_table_does_not_merge_distinct_charges():
    html = b"<div class='container'><h4>Fees 2026</h4><table><tr><td></td><td>First Semester</td><td>Second Semester</td></tr><tr><td>Caution Deposit (One time Fee)</td><td colspan='2'>14,000/-</td><td colspan='2'>-</td><td colspan='2'>Convocation Fee (One-Time Fee)</td><td colspan='2'>5500/-</td></tr></table></div>"
    rows = [text for _, text in extract_html(html)]
    assert any(text.startswith("Caution Deposit") and "14,000" in text and "Convocation" not in text for text in rows)
    assert any(text.startswith("Convocation Fee") and "5500" in text for text in rows)


def test_mixed_programme_and_admission_block_is_structurally_split():
    text = "B.Tech/B.Tech-MS (1) CSE (2) ECE (3) Cyber Security Admission to the B.Tech/B.Tech-MS programme will be based on JEE Main through JoSAA. (1) Fee Structure for B.Tech"
    parts = _semantic_sections("Remaining fee details for DASA", text)
    assert [section for section, _ in parts] == ["Available B.Tech programmes", "B.Tech admission procedure"]
    assert "Fee Structure" not in parts[1][1]


def test_document_rows_do_not_inherit_source_level_programme_topic():
    topics = _chunk_topics(
        ["admissions", "documents", "fees", "portal", "programmes"],
        "The following documents are required for verification",
        "Category certificate must be produced during reporting.",
    )
    assert topics == ["documents"]


def test_follow_up_inherits_topic_but_new_programme_does_not():
    history = [{"role": "user", "content": "What is the B.Tech CSE admission fee for 2026?"}]
    follow_up = resolve_scope("Can I pay it online?", history)
    assert follow_up.use_context
    assert follow_up.programme == "B.Tech CSE"
    assert follow_up.admission_year == 2026
    new_topic = resolve_scope("What about ECE admission in 2025?", history)
    assert not new_topic.use_context
    assert new_topic.programme == "B.Tech ECE"
    assert new_topic.admission_year == 2025


def test_general_admission_process_and_programme_list_intents():
    admission = resolve_scope("How do I apply for B.Tech in 2026?", [])
    assert admission.topic == "admissions"
    assert admission.intent == "admission_process"
    courses = resolve_scope("what are the available courses", [])
    assert courses.topic == "programmes"
    assert courses.intent == "programmes_list"


def test_placement_department_and_facility_topics_are_explicit():
    assert resolve_scope("What is the placement rate?", []).topic == "placements"
    assert resolve_scope("Which academic departments are there?", []).topic == "departments"
    assert resolve_scope("What hostel facilities are available?", []).topic == "facilities"


def test_old_or_conflicting_year_cannot_answer_2026_fee():
    scope = resolve_scope("What is the B.Tech fee for 2026?", [])
    row = {"programme": "B.Tech", "admission_year": 2026, "year_conflict": False}
    assert eligible(row, scope)
    assert not eligible({**row, "admission_year": 2025}, scope)
    assert not eligible({**row, "year_conflict": True}, scope)
    assert not eligible({**row, "admission_year": None}, scope)


def test_unrelated_and_wrong_programme_evidence_is_rejected():
    scope = resolve_scope("What is the ECE tuition fee for 2026?", [])
    base = {"chunk_id": "a", "programme": "B.Tech ECE", "admission_year": 2026, "year_conflict": False, "title": "B.Tech fee structure", "section": "Fee", "text": "Tuition fee is listed for ECE admission 2026.", "rrf_score": .03, "bm25_score": 3.0}
    results = select_evidence(scope, [base, {**base, "chunk_id": "b", "programme": "B.Tech CSE"}, {**base, "chunk_id": "c", "text": "Unrelated material", "title": "Other", "section": "Other"}])
    assert [row["chunk_id"] for row in results] == ["a"]


def test_payment_method_followup_requires_admission_route():
    history = [{"role": "user", "content": "What is the B.Tech fee for 2026?"}]
    scope = resolve_scope("Can I pay it online?", history)
    assert scope.use_context and scope.requires_route
    assert not eligible({"programme": "B.Tech", "admission_year": 2026}, scope)
    explicit = resolve_scope("Can JoSAA students pay the 2026 B.Tech fee online?", [])
    assert explicit.admission_route == "JoSAA/CSAB"
    assert eligible({"programme": "B.Tech", "admission_year": 2026, "topics": ["fees"], "text": "JoSAA online payment"}, explicit)
    documents = resolve_scope("What documents do I need for JoSAA admission in 2026?", [])
    assert documents.requires_route and documents.admission_route == "JoSAA/CSAB"
    wrong_route = {"programme": "B.Tech", "admission_year": 2026, "topics": ["documents"], "heading_path": ["Admission 2026 [DASA] — Documents"], "text": "Passport required"}
    assert not eligible(wrong_route, documents)


def test_answer_is_extractive_and_cited():
    scope = resolve_scope("What is the B.Tech fee for 2026?", [])
    answer, refused = grounded_answer(scope, [{"text": "The B.Tech tuition fee for admission 2026 is listed as 1,59,800 rupees.", "admission_year": 2026}])
    assert not refused
    assert "1,59,800" in answer and "[1]" in answer
    answer, refused = grounded_answer(scope, [])
    assert refused


def _passage(chunk_id: str, text: str, section: str, rrf: float = .03, topic: str = "programmes") -> dict:
    return {"chunk_id": chunk_id, "doc_id": chunk_id, "programme": "", "admission_year": None,
            "year_conflict": False, "title": "Official applicant information", "section": section,
            "heading_path": [section], "text": text, "rrf_score": rrf, "bm25_score": 2.0,
            "topics": [topic]}


def test_portal_url_wins_over_reporting_details_and_is_answered():
    scope = resolve_scope("Where is the IIIT Kottayam admission data entry portal?", [])
    reporting = _passage("reporting", "Mode of Reporting: Offline at IIIT Kottayam Campus for admission 2026.", "Reporting Details", .04, "portal")
    portal = _passage("portal", "Admission Data Entry Portal: Enter candidate details at https://admission.iiitkottayam.ac.in/ and click FINAL SUBMIT.", "UG Admission 2026", .03, "portal")
    rows = select_evidence(scope, [reporting, portal])
    assert rows[0]["chunk_id"] == "portal"
    answer, refused = grounded_answer(scope, rows)
    assert not refused and "https://admission.iiitkottayam.ac.in/" in answer


def test_caution_deposit_does_not_answer_with_tuition():
    scope = resolve_scope("Is a caution deposit charged in the first semester?", [])
    tuition = _passage("tuition", "The first semester tuition fee is Rs 1,59,800/-.", "Fee Structure", .04, "fees")
    deposit = _passage("deposit", "Caution Deposit (One time Fee); First Semester: 14,000/-", "Fee Structure", .03, "fees")
    rows = select_evidence(scope, [tuition, deposit])
    assert rows[0]["chunk_id"] == "deposit"
    answer, refused = grounded_answer(scope, rows)
    assert not refused and "14,000" in answer and "1,59,800" not in answer


def test_canonical_fee_row_excludes_broad_multi_charge_summary():
    scope = resolve_scope("Is a caution deposit charged in the first semester?", [])
    canonical = _passage("deposit", "Caution Deposit (One time Fee); First Semester: 14,000/-", "Fee Structure", .03, "fees")
    summary = _passage("summary", "Tuition Fee (First Semester): 1,59,800/- Caution Deposit: 14,000/-", "Fee Structure", .04, "fees")
    rows = select_evidence(scope, [summary, canonical])
    answer, refused = grounded_answer(scope, rows)
    assert not refused and "14,000" in answer and "1,59,800" not in answer


def test_scholarship_documents_uses_answer_bearing_sentence():
    scope = resolve_scope("Does the institute support scholarship applications with documents?", [])
    passage = _passage("scholarship", "No direct financial assistance is available from the Institute. Students can apply to state governments for scholarships. The Institute supports such applications by providing necessary documents and forwarding them to the appropriate authorities.", "Scholarship", topic="scholarships")
    answer, refused = grounded_answer(scope, [passage])
    assert not refused and "providing necessary documents" in answer
    assert "No direct financial" not in answer


def test_direct_scholarship_question_uses_direct_assistance_fact():
    scope = resolve_scope("Does IIIT Kottayam directly provide scholarships?", [])
    passage = _passage("scholarship", "Note: No direct financial assistance is available from the Institute. After admission, students can apply for scholarships directly to State Governments.", "Scholarship", topic="scholarships")
    answer, refused = grounded_answer(scope, [passage])
    assert not refused and "No direct financial assistance" in answer


def test_admissions_question_rejects_fee_navigation_heading():
    scope = resolve_scope("How do I apply for B.Tech admission in 2026?", [])
    passage = {**_passage("admission", "Admission to the B.Tech programme will be based on JEE Main performance through JoSAA counselling. (1) Fee Structure for the B.Tech program (Admission 2026)", "Admission", topic="admissions"), "admission_year": 2026}
    answer, refused = grounded_answer(scope, [passage])
    assert not refused and "JEE Main" in answer and "Fee Structure" not in answer


def test_application_process_combines_counselling_and_portal_steps():
    scope = resolve_scope("How do I apply for B.Tech admission in 2026?", [])
    route = {**_passage("route", "Admission to B.Tech will be based on JEE Main through JoSAA counselling.", "UG Admission 2026", topic="admissions"), "admission_year": 2026}
    portal = {**_passage("portal", "Admission Data Entry Portal: Enter candidate details at https://admission.iiitkottayam.ac.in/ and click FINAL SUBMIT.", "UG Admission 2026", topic="admissions"), "admission_year": 2026}
    answer, refused = grounded_answer(scope, [route, portal])
    assert not refused and "JEE Main" in answer and "https://admission.iiitkottayam.ac.in/" in answer


def test_available_courses_rejects_document_rows_and_lists_programmes():
    scope = resolve_scope("what are the available courses", [])
    document = _passage("document", "Category certificate is available on the JoSAA website and is required for verification.", "Documents required", .05, "documents")
    programmes = _passage("programmes", "B.Tech/B.Tech-MS (1) Computer Science and Engineering (2) Electronics and Communication Engineering (3) Cyber Security", "Available B.Tech programmes", .03, "programmes")
    rows = select_evidence(scope, [document, programmes])
    assert [row["chunk_id"] for row in rows] == ["programmes"]
    answer, refused = grounded_answer(scope, rows)
    assert not refused and "Computer Science and Engineering" in answer
    assert "Category certificate" not in answer


def test_mnc_fragment_cannot_hide_programme_evidence():
    scope = resolve_scope("Does IIIT Kottayam offer B.Tech in Mathematics and Computing?", [])
    fragment = _passage("fragment", "set that prepares them to excel in various high-demand fields, including:", "B.Tech Mathematics and Computing", .04)
    description = _passage("description", "Our B.Tech in Mathematics and Computing is designed for students.", "B.Tech Mathematics and Computing", .03)
    rows = select_evidence(scope, [fragment, description])
    answer, refused = grounded_answer(scope, rows)
    assert not refused and "Our B.Tech in Mathematics and Computing" in answer


def test_ece_programme_description_beats_admission_boilerplate():
    scope = resolve_scope("What is the B.Tech ECE programme?", [])
    admissions = {**_passage("admission", "B.Tech/B.Tech-MS (1) CSE (2) ECE Admission to the B.Tech programme is based on JEE Main.", "Admission", .04), "programme": "B.Tech"}
    description = {**_passage("description", "Our BTech program in ECE covers electronics and communication engineering, signal processing and VLSI.", "B.Tech in ECE", .03), "programme": "B.Tech ECE"}
    rows = select_evidence(scope, [admissions, description])
    assert rows[0]["chunk_id"] == "description"
    answer, refused = grounded_answer(scope, rows)
    assert not refused and "signal processing" in answer and "JEE Main" not in answer


def test_generic_ece_description_includes_named_curriculum_fields():
    scope = resolve_scope("What is the B.Tech ECE programme?", [])
    description = {**_passage(
        "description",
        "Our BTech program in ECE builds practical skills. This program spans across prominent fields including Hardware/Software Co-Design, Signal Processing, VLSI and Embedded Systems.",
        "B.Tech in ECE",
    ), "programme": "B.Tech ECE"}
    answer, refused = grounded_answer(scope, [description])
    assert not refused and "Signal Processing" in answer


def test_specific_programme_attribute_beats_generic_overview():
    scope = resolve_scope("Does the ECE curriculum mix electronics with computer-science content?", [])
    description = {**_passage(
        "description",
        "Our BTech program in ECE builds practical skills. Our curriculum imparts a strong foundation on Electronics and Communication Engineering with a blend of Computer Science. This program spans across Signal Processing and VLSI.",
        "B.Tech in ECE",
    ), "programme": "B.Tech ECE"}
    answer, refused = grounded_answer(scope, [description])
    assert not refused and "blend of Computer Science" in answer
    assert "builds practical skills" not in answer


def test_answer_year_is_only_from_cited_passage():
    scope = resolve_scope("What is the B.Tech CSE programme?", [])
    description = {**_passage("description", "The B.Tech CSE programme builds a computer science foundation.", "CSE"), "admission_year": None}
    unrelated = {**_passage("admission", "Admission 2026 uses JEE Main.", "Admission"), "admission_year": 2026}
    answer, refused = grounded_answer(scope, [description, unrelated])
    assert not refused and "admission 2026" not in answer.lower()


def test_semester_words_are_resolved_in_both_orders_and_plural_lists():
    assert resolve_scope("What is the mess advance in semester three?", []).semesters == (3,)
    assert resolve_scope("Compare the fifth and sixth semesters", []).semesters == (5, 6)


def test_conversational_contraction_is_normalized_for_retrieval():
    assert SearchEngine.build_query("what's the mess advance?", []) == "what is the mess advance?"


def test_fee_answer_only_quotes_requested_semesters():
    scope = resolve_scope("What hostel maintenance applies in the fifth and sixth semesters?", [])
    row = _passage(
        "fees",
        "Hostel/facility maintenance fee; First Semester: 37,500/-; Fifth Semester: 45,500/-; Sixth Semester: 45,500/-; Seventh Semester: 50,100/-",
        "Fee Structure",
        topic="fees",
    )
    answer, refused = grounded_answer(scope, [row])
    assert not refused and "Fifth Semester: 45,500" in answer and "Sixth Semester: 45,500" in answer
    assert "37,500" not in answer and "50,100" not in answer


def test_laptop_and_hostel_items_use_structured_admission_note():
    text = (
        "Note 1: All students must have a laptop at the time of admission with a minimum configuration of: "
        "i5/i7 processor or equivalent with at least 8 GB RAM, and Linux Installation (UBUNTU 22.04 or higher preferred). "
        "Note 2: Hostel rooms will be equipped with a mattress, pillow, bucket, and mug. "
        "All are to purchase these items mandatorily for a cost of Rs 2,650."
    )
    row = _passage("note", text, "Admission requirements", topic="documents")
    laptop = resolve_scope("What minimum laptop setup must a new student have when reporting?", [])
    laptop_rows = select_evidence(laptop, [row])
    answer, refused = grounded_answer(laptop, laptop_rows)
    assert not refused and "i5/i7" in answer and "8 GB RAM" in answer and "UBUNTU 22.04" in answer
    hostel = resolve_scope("Which basic hostel room items must I buy and what do they cost?", [])
    hostel_rows = select_evidence(hostel, [row])
    answer, refused = grounded_answer(hostel, hostel_rows)
    assert not refused and all(item in answer for item in ("mattress", "pillow", "bucket", "mug", "2,650"))

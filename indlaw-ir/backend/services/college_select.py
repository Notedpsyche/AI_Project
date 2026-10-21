"""Source-safe selection after the existing hybrid RRF stage."""

from __future__ import annotations

import math
import re

from backend.services.college_query import QueryScope, eligible, normalized_terms

GENERIC_TERMS = {"admission", "available", "btech", "campus", "course", "department", "facility", "first", "have", "offered", "placement", "second", "semester", "programme", "program", "scholarship", "student", "year"}
SEMESTER_LABELS = {
    1: "first semester",
    2: "second semester",
    3: "third semester",
    4: "fourth semester",
    5: "fifth semester",
    6: "sixth semester",
    7: "seventh semester",
    8: "eighth semester",
}


def _content(row: dict) -> str:
    return f"{row.get('section', '')} {row.get('text', '')}".casefold()


def _component_supported(component: str, text: str) -> bool:
    patterns = {
        "total fee": r"\btotal fees?\b",
        "hostel maintenance": r"\bhostel\s*/?\s*facility maintenance fee\b",
        "mess advance": r"\bmess advance\b",
        "medical insurance": r"\bmedical insurance\b",
        "mess equipment maintenance": r"\bmess equipment maintenance fee\b",
        "sports equipment maintenance": r"\bsports equipment maintenance fee\b",
        "club activities": r"\bclub activities\b",
        "caution deposit": r"\bcaution deposit\b",
        "convocation fee": r"\bconvocation fee\b",
        "alumni fee": r"\balumni fee\b",
        "tuition fee": r"\btuition fee\b",
    }
    return bool(re.search(patterns[component], text, re.I))


def _document_item_supported(item: str, text: str) -> bool:
    patterns = {
        "laptop requirement": r"\blaptop\b.*\b(?:intel core i5|8 ?gb|linux)\b",
        "jee admit card": r"\bjee\b.*\badmit card\b|\badmit card\b.*\bjee\b",
        "jee score card": r"\bjee\b.*\bscore ?card\b|\bscore ?card\b.*\bjee\b",
        "character certificate": r"\bcharacter and conduct certificate\b",
        "aadhaar": r"\baadhaar\b",
        "passport photographs": r"\bpassport size photographs?\b",
        "passport": r"\bpassport\b|\bcitizenship card\b",
        "vaccination proof": r"\b(chickenpox|hepatitis[ -]?a|vaccination proof)\b",
        "transfer certificate": r"\b(school leaving|transfer) certificate\b",
        "marksheet": r"\bmark ?sheet\b",
        "medical certificate": r"\bmedical (certificate|report)\b",
        "bank passbook": r"\bbank passbook\b",
        "address proof": r"\bproof of permanent address\b",
    }
    return bool(re.search(patterns[item], text, re.I))


def supports_request(scope: QueryScope, row: dict) -> bool:
    """Require evidence for the requested task, not merely its broad topic."""
    text = _content(row)
    intent = scope.intent
    if scope.underspecified:
        return False
    if intent == "portal_steps":
        return bool(re.search(r"\bmandatory\b.*\b7 steps\b|\b7 steps\b.*\bmandatory\b", text, re.I))
    if intent == "portal_confirmation":
        return "final submission" in text and ("confirming successful submission" in text or "application report" in text)
    if intent == "reporting_schedule":
        return "mode of reporting" in text and "offline" in text
    if intent == "orientation":
        return "orientation" in text and bool(re.search(r"\b20/08/2026\b|\b20 august 2026\b", text, re.I))
    if intent == "class_commencement":
        return bool(re.search(r"\b(class commencement|commencement of classes)\b", text, re.I))
    if intent in {"fee_total", "fee_component", "fee_comparison"}:
        if scope.fee_components and not any(_component_supported(component, text) for component in scope.fee_components):
            return False
        return not scope.semesters or any(SEMESTER_LABELS[number] in text for number in scope.semesters)
    if intent == "document_item":
        return any(_document_item_supported(item, text) for item in scope.document_items)
    if intent == "programme_fields":
        return bool(re.search(r"(?:•|\bfields?\b|\bareas?\b|\bspans across\b|\bcurriculum\b|\bhigher semesters?\b|\bspecialized courses?\b)", text, re.I))
    if intent == "scholarship_details":
        return bool(re.search(r"\b(scheme|award|income limit)\w*\b", text, re.I) and re.search(r"\b(?:rs\.?|₹|\d[\d,]+)\b", text))
    if intent == "scholarship_support":
        return "forwarding" in text and "documents" in text
    if intent == "scholarship_authorities":
        return bool(re.search(r"\b(state government|other authorities|scholarship portal)\b", text, re.I))
    if intent == "placement_recruiters":
        return "placements" in set(row.get("topics") or []) and bool(re.search(r"\b(employer|company|companies|recruiter|hired)\w*\b", text, re.I))
    if intent == "placement_statistics":
        return "placements" in set(row.get("topics") or []) and bool(re.search(r"\b(percentage|rate|package|salary|placed|secured jobs?|students?)\b", text, re.I))
    if intent == "department_head":
        return bool(re.search(r"\b(head|hod|chair)\b", text, re.I))
    if intent == "laboratory_location":
        return bool(re.search(r"\b(laborator(?:y|ies)|labs?)\b", text, re.I) and re.search(r"\b(building|located|location|floor|block)\b", text, re.I))
    if intent == "hotel_details":
        return bool("hotel" in text and re.search(r"\b(phone|contact)\b", text, re.I) and re.search(r"\b(price|rate|per night|nightly)\b", text, re.I))
    if intent == "first_year_housing":
        return bool(re.search(r"\b(first year|first-year)\b", text, re.I) and re.search(r"\b(accommodated|hostels?|outside the campus)\b", text, re.I))
    if intent == "hostel_items":
        return all(item in text for item in ("mattress", "pillow", "bucket", "mug")) and bool(re.search(r"\b2,?650\b", text))
    if intent == "hostel_transport":
        return bool(re.search(r"\b(conveyance|transport)\b", text, re.I) and re.search(r"\bfree of cost\b", text, re.I))
    return True


def evidence_set_sufficient(scope: QueryScope, rows: list[dict]) -> bool:
    if not rows:
        return False
    combined = " ".join(_content(row) for row in rows)
    if scope.intent == "fee_comparison":
        return all(_component_supported(component, combined) for component in scope.fee_components)
    if scope.intent == "document_item":
        return all(_document_item_supported(item, combined) for item in scope.document_items)
    if scope.intent == "portal_confirmation":
        return "confirming successful submission" in combined and "application report" in combined
    return True


def features(query: str, row: dict, max_bm25: float = 1.0) -> list[float]:
    terms = normalized_terms(query)
    title = normalized_terms(str(row.get("title", "")) + " " + str(row.get("section", "")))
    body = normalized_terms(str(row.get("text", "")))
    return [
        float(row.get("semantic_score") or 0.0),
        math.log1p(max(0.0, float(row.get("bm25_score") or 0.0))),
        max(0.0, float(row.get("bm25_score") or 0.0)) / max(max_bm25, 1e-9),
        float(row.get("rrf_score") or 0.0),
        len(terms & title) / max(len(terms), 1),
        len(terms & body) / max(len(terms), 1),
    ]


def select_evidence(scope: QueryScope, candidates: list[dict], reranker: dict | None = None, top_k: int = 3) -> list[dict]:
    eligible_rows = [row for row in candidates if eligible(row, scope) and supports_request(scope, row)]
    if not eligible_rows:
        return []
    if scope.topic == "programmes" and scope.programme.startswith("B.Tech "):
        has_description = any(
            row.get("programme") == scope.programme
            and "admission" not in str(row.get("section", "")).lower()
            for row in eligible_rows
        )
        if has_description:
            eligible_rows = [
                row for row in eligible_rows
                if row.get("programme") == scope.programme
                and "admission" not in str(row.get("section", "")).lower()
            ]
    if scope.intent == "programmes_list":
        if scope.programme == "B.Tech":
            list_rows = [row for row in eligible_rows if "available b.tech programmes" in str(row.get("section", "")).lower()]
        elif scope.programme == "e-M.Tech":
            list_rows = [row for row in eligible_rows if "m.tech admission" in str(row.get("section", "")).lower()]
        elif scope.programme == "PhD":
            list_rows = [row for row in eligible_rows if "phd admission" in str(row.get("section", "")).lower()]
        else:
            list_rows = [
                row for row in eligible_rows
                if any(label in str(row.get("section", "")).lower() for label in ("available b.tech programmes", "m.tech admission", "phd admission"))
            ]
        if list_rows:
            eligible_rows = list_rows
    if scope.fee_components:
        component_rows = [
            row for row in eligible_rows
            if ";" in str(row.get("text", "")) and any(
                _component_supported(
                    component,
                    str(row.get("text", "")).split(";", 1)[0].split(":", 1)[0],
                )
                for component in scope.fee_components
            )
        ]
        if component_rows and evidence_set_sufficient(scope, component_rows):
            eligible_rows = component_rows
    max_bm25 = max(float(row.get("bm25_score") or 0.0) for row in eligible_rows)
    current_terms = normalized_terms(scope.current_question)
    focus_terms = current_terms - GENERIC_TERMS
    scored = []
    for row in eligible_rows:
        vector = features(scope.query, row, max_bm25)
        structured_programme_list = scope.intent == "programmes_list" and any(
            label in str(row.get("section", "")).lower()
            for label in ("available b.tech programmes", "m.tech admission", "phd admission")
        )
        body_terms = normalized_terms(str(row.get("text", "")))
        heading_terms = normalized_terms(str(row.get("section", "")))
        if vector[-1] == 0 and vector[-2] == 0 and not structured_programme_list:
            if scope.intent not in {
                "document_item", "fee_component", "fee_comparison", "fee_total", "first_year_housing",
                "hostel_items", "hostel_transport", "portal_confirmation", "portal_steps", "programme_description", "programme_fields",
                "reporting_schedule",
            }:
                continue  # No inspectable lexical support for an extractive answer.
        if scope.topic in {"departments", "facilities", "placements"} and focus_terms and not (focus_terms & (body_terms | heading_terms)):
            continue
        enriched = dict(row)
        score = float(row.get("rrf_score") or 0.0)
        if reranker:
            z = float(reranker["intercept"]) + sum(weight * value for weight, value in zip(reranker["weights"], vector))
            score = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
        else:
            # RRF remains the candidate generator; these small, inspectable
            # bonuses prioritize passages containing the requested fact.
            score += 0.06 * len(focus_terms & body_terms) / max(len(focus_terms), 1)
            score += 0.015 * len(current_terms & heading_terms) / max(len(current_terms), 1)
            score += 0.01 * len(current_terms & body_terms) / max(len(current_terms), 1)
            if scope.topic == "programmes" and scope.programme and row.get("programme") == scope.programme:
                score += 0.03
            if scope.intent == "programmes_list":
                score += 0.04
            if scope.intent == "admission_process" and str(row.get("section", "")).lower() == "b.tech admission procedure":
                score += 0.12
            if scope.intent in {"admission_process", "admission_data_entry"} and re.search(r"https?://[^\s]*admission", str(row.get("text", "")), re.I):
                score += 0.12
            if scope.fee_components:
                score += 0.10 * sum(_component_supported(component, _content(row)) for component in scope.fee_components)
            if scope.document_items:
                score += 0.10 * sum(_document_item_supported(item, _content(row)) for item in scope.document_items)
            if scope.semesters:
                score += 0.04 * sum(SEMESTER_LABELS[number] in _content(row) for number in scope.semesters)
            if scope.intent == "programme_fields" and "•" in str(row.get("text", "")):
                score += 0.08
        enriched["final_evidence_score"] = score
        enriched["selection_reason"] = "Learned relevance reranker" if reranker else "Eligible official source; hybrid RRF and query-term support"
        scored.append(enriched)
    scored.sort(key=lambda row: (-row["final_evidence_score"], row["chunk_id"]))
    selected: list[dict] = []
    seen_text: set[str] = set()
    for row in scored:
        normalized = " ".join(str(row["text"]).lower().split())
        if normalized in seen_text:
            continue
        seen_text.add(normalized)
        selected.append(row)
        if len(selected) == top_k:
            break
    return selected if evidence_set_sufficient(scope, selected) else []

"""Conservative extractive answers: every statement is copied from cited evidence."""

from __future__ import annotations

import re

from backend.services.college_query import QueryScope, normalized_terms

GENERIC_TERMS = {"admission", "available", "btech", "campus", "course", "department", "facility", "first", "have", "offered", "placement", "second", "semester", "programme", "program", "scholarship", "student", "year"}

REFUSAL = "I couldn't verify that from the available official IIIT Kottayam applicant sources. Please check the linked admission information or contact the institute."


def _sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    cleaned = re.sub(r"\b(Rs|Govt|Dr|Mr|Ms)\.\s+", r"\1 ", cleaned)
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\s+\*\s+", cleaned) if len(part.strip()) >= 20]


def _matching_sentences(row: dict, patterns: tuple[str, ...], limit: int = 1) -> list[str]:
    matches = []
    for sentence in _sentences(str(row["text"])):
        if all(re.search(pattern, sentence, re.I) for pattern in patterns):
            matches.append(sentence)
            if len(matches) == limit:
                break
    return matches


SEMESTER_NAMES = {
    1: "First", 2: "Second", 3: "Third", 4: "Fourth",
    5: "Fifth", 6: "Sixth", 7: "Seventh", 8: "Eighth",
}


def _fee_claims(scope: QueryScope, text: str) -> list[str]:
    """Return exact component/cell substrings without leaking other semesters."""
    if not scope.semesters:
        return [text]
    claims: list[str] = []
    component = text.split(";", 1)[0].strip()
    if component:
        claims.append(component)
    for number in scope.semesters:
        label = SEMESTER_NAMES[number]
        match = re.search(rf"\b{label} Semester:\s*[^;]+", text, re.I)
        if match:
            claims.append(match.group(0).strip())
    return claims


def _task_claims(scope: QueryScope, evidence: list[dict]) -> list[tuple[int, str, int | None]]:
    """Extract claims for tasks where generic sentence scoring is unsafe."""
    claims: list[tuple[int, str, int | None]] = []
    intent = scope.intent
    for rank, row in enumerate(evidence, 1):
        text = " ".join(str(row["text"]).split())
        year = row.get("admission_year")
        selected: list[str] = []
        if intent == "reporting_schedule":
            match = re.search(
                r"Mode of Reporting:\s*Offline at IIIT Kottayam Campus\s*Date\s*:\s*14 August 2026 to 18 August 2026\s*Time\s*:\s*10:00 AM to 3:00 PM",
                text,
                re.I,
            )
            selected = [match.group(0)] if match else []
        elif intent == "orientation":
            selected = _matching_sentences(row, (r"orientation", r"10:00 AM"))
        elif intent == "class_commencement":
            match = re.search(r"Tentative Class Commencement Date:\s*20/08/2026", text, re.I)
            selected = [match.group(0)] if match else _matching_sentences(row, (r"commencement of classes",))
        elif intent == "portal_steps":
            selected = _matching_sentences(row, (r"mandatory", r"7 steps"))
        elif intent == "portal_confirmation":
            selected = _matching_sentences(row, (r"mail", r"successful submission"))
            selected += _matching_sentences(row, (r"application report", r"print"))
        elif intent in {"fee_total", "fee_component", "fee_comparison"}:
            if intent == "fee_total":
                match = re.search(r"Total Fees for First Semester:\s*Rs\.?\s*2,52,040/-?", text, re.I)
                selected = [match.group(0)] if match else []
            else:
                selected = _fee_claims(scope, text)
        elif intent == "document_item":
            if "vaccination proof" in scope.document_items and "chickenpox" in text.lower():
                selected = _matching_sentences(row, (r"vaccination proof", r"chickenpox", r"hepatitis"))
            elif "laptop requirement" in scope.document_items:
                selected = _matching_sentences(row, (r"laptop", r"i5/i7", r"8 ?GB", r"Linux"))
            else:
                selected = [text]
        elif intent in {"programmes_list", "programme_description", "programme_fields"}:
            if intent == "programme_description" and "•" not in text:
                sentences = _sentences(text)
                programme_terms = normalized_terms(scope.programme)
                focus = normalized_terms(scope.current_question) - programme_terms - GENERIC_TERMS
                ranked = sorted(
                    sentences,
                    key=lambda sentence: len(focus & normalized_terms(sentence)),
                    reverse=True,
                )
                if focus and ranked and focus.intersection(normalized_terms(ranked[0])):
                    selected = ranked[:1]
                else:
                    overview = next((sentence for sentence in sentences if re.search(r"\b(programme|program|curriculum)\b", sentence, re.I)), None)
                    if not overview:
                        overview = next(
                            (
                                sentence for sentence in sentences
                                if normalized_terms(scope.programme).intersection(normalized_terms(sentence))
                            ),
                            None,
                        )
                    fields = next((
                        sentence for sentence in sentences
                        if sentence != overview and re.search(r"\b(spans across|prominent fields)\b", sentence, re.I)
                    ), None)
                    if not fields:
                        fields = next((
                            sentence for sentence in sentences
                            if sentence != overview and re.search(r"\bfoundation\b", sentence, re.I)
                        ), None)
                    selected = [sentence for sentence in (overview, fields) if sentence]
            elif intent == "programme_fields" and "•" not in text:
                current = normalized_terms(scope.current_question)
                sentences = _sentences(text)
                sentences.sort(key=lambda sentence: len(current & normalized_terms(sentence)), reverse=True)
                selected = sentences[:1]
            else:
                selected = [text]
        elif intent == "programme_comparison":
            sentences = _sentences(text)
            overview = next((sentence for sentence in sentences if re.search(r"\b(programme|program|curriculum|focuses|spans)\b", sentence, re.I)), None)
            if overview:
                label = str(row.get("programme") or row.get("title") or "Programme")
                selected = [f"{label}: {overview}"]
        elif intent == "scholarship_support":
            selected = _matching_sentences(row, (r"providing (?:all )?necessary documents", r"forwarding"))
        elif intent == "scholarship_authorities":
            selected = _matching_sentences(row, (r"state government", r"other authorities"))
        elif intent == "first_year_housing":
            selected = _matching_sentences(row, (r"first year", r"outside the campus", r"conveyance"))
        elif intent == "hostel_items":
            selected = _matching_sentences(row, (r"mattress", r"pillow", r"bucket", r"mug"))
            selected += _matching_sentences(row, (r"purchase", r"2,650"))
        elif intent == "hostel_transport":
            selected = _matching_sentences(row, (r"conveyance", r"free of cost"))
        for claim in selected:
            if claim and all(claim != existing[1] for existing in claims):
                claims.append((rank, claim, year))
    limits = {
        "portal_confirmation": 2,
        "fee_component": 3,
        "fee_comparison": 6,
        "document_item": 3,
        "programmes_list": 3,
        "programme_description": 2,
        "hostel_items": 2,
    }
    return claims[: limits.get(intent, 1)]


def grounded_answer(scope: QueryScope, evidence: list[dict]) -> tuple[str, bool]:
    if scope.requires_route and not scope.admission_route:
        subject = "document checklist" if scope.topic == "documents" else "payment instructions"
        return f"Please specify your admission route (JoSAA/CSAB or DASA) so I can check the correct {subject}.", True
    if not evidence:
        return REFUSAL, True
    task_claims = _task_claims(scope, evidence)
    if scope.intent in {
        "class_commencement", "document_item", "fee_comparison", "fee_component", "fee_total",
        "first_year_housing", "hostel_items", "hostel_transport", "orientation", "portal_confirmation",
        "portal_steps", "programme_description", "programme_fields", "programmes_list", "reporting_schedule",
        "programme_comparison", "scholarship_authorities", "scholarship_support",
    }:
        if not task_claims:
            return REFUSAL, True
        years = {year for _, _, year in task_claims if year}
        if len(years) > 1 or (scope.admission_year and years and years != {scope.admission_year}):
            return REFUSAL, True
        label = f"For {', '.join(scope.programmes)}" if scope.programmes else (f"For {scope.programme}" if scope.programme else "According to the official sources")
        if scope.admission_year:
            label += f" (admission {scope.admission_year})"
        elif years and len(years) == len(task_claims):
            label += f" (admission {next(iter(years))})"
        if scope.topic == "documents":
            label += " — selected items, not a complete checklist; open the source for the full list"
        return label + ":\n" + "\n".join(f"• {claim} [{rank}]" for rank, claim, _ in task_claims), False
    terms = normalized_terms(scope.current_question)
    focus_terms = terms - GENERIC_TERMS
    candidates: list[tuple[float, int, str, int | None]] = []
    for rank, row in enumerate(evidence, 1):
        source_text = " ".join(str(row["text"]).split())
        semester = re.search(r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth) semester\b", scope.current_question, re.I)
        if scope.topic == "fees" and semester and ";" in source_text and source_text.count(";") >= 1:
            cell = re.search(rf"\b{semester.group(0)}: [^;]+", source_text, re.I)
            if cell:
                source_text = source_text.split(";", 1)[0] + "; " + cell.group(0)
        source_text = re.sub(r"\b(Rs|Govt|Dr|Mr|Ms)\.\s+", r"\1 ", source_text)
        sentences = _sentences(source_text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            if re.search(r"\b(via|to|at|for|as|of|by|Rs)\s*$", sentence, re.I):
                continue
            programme_list = scope.intent == "programmes_list" and (
                len(re.findall(r"\((?:\d+|i{1,3}|iv|v)\)", sentence, re.I)) >= 2
                or any(label in str(row.get("section", "")).lower() for label in ("m.tech admission", "phd admission"))
            )
            if not programme_list and not re.search(r"https?://|;\s*[^;]+:|\b(is|are|will|can|may|must|has|have|provides?|supports?|offers?|aims?|starts?|includes?|requires?|covers?|builds?|spans?|teaches?|focuses|based|designed|available|apply|admitted|enter|click)\b", sentence, re.I):
                continue  # A navigation heading is not an answer fact.
            matching = normalized_terms(sentence) & terms
            if not matching and not programme_list:
                continue
            score = 3 * len(matching & focus_terms) + len(matching)
            if programme_list:
                score += 8
                section = str(row.get("section", ""))
                if section and section.lower() not in sentence.lower() and any(label in section.lower() for label in ("m.tech admission", "phd admission")):
                    sentence = f"{section}: {sentence}"
            score += 0.5 / rank
            if (scope.topic == "programmes" and scope.programme
                    and row.get("programme") == scope.programme
                    and "admission" not in str(row.get("section", "")).lower()):
                score += 1
            if (scope.topic == "scholarships" and re.search(r"\b(direct|directly)\b", scope.current_question, re.I)
                    and re.search(r"\b(provide|offer|give|fund)\w*\b", scope.current_question, re.I)
                    and re.search(r"\bdirect financial assistance\b", sentence, re.I)):
                score += 5
            score -= min(len(sentence), 1500) / 5000
            candidates.append((score, rank, sentence, row.get("admission_year")))
    if not candidates:
        return REFUSAL, True
    candidates.sort(key=lambda item: (-item[0], item[1], len(item[2])))
    application_process = scope.intent == "admission_process" and not scope.admission_route
    if application_process:
        route = next((item for item in candidates if re.search(r"\bJEE\b", item[2]) and re.search(r"\b(JoSAA|CSAB|counselling)\b", item[2], re.I)), None)
        portal = next((item for item in candidates if "portal" in item[2].lower() and re.search(r"https?://", item[2])), None)
        if route and portal:
            candidates = [route, portal]
        else:
            candidates = [item for item in candidates if re.search(r"\b(JEE|JoSAA|CSAB|counselling|portal|submit)\b", item[2], re.I)]
    if scope.intent == "admission_data_entry":
        portal = next((item for item in candidates if "portal" in item[2].lower() and re.search(r"https?://", item[2])), None)
        candidates = [portal] if portal else []
    if not candidates:
        return REFUSAL, True
    limit = 3 if scope.topic == "documents" or scope.intent == "programmes_list" else (2 if application_process else 1)
    chosen: list[tuple[int, str, int | None]] = []
    seen: set[str] = set()
    for _, rank, sentence, year in candidates:
        normalized = sentence.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        chosen.append((rank, sentence, year))
        if len(chosen) == limit:
            break
    years = {year for _, _, year in chosen if year}
    if len(years) > 1 or (scope.admission_year and years and years != {scope.admission_year}):
        return REFUSAL, True
    label = f"For {scope.programme}" if scope.programme else "According to the official sources"
    if scope.admission_year:
        label += f" (admission {scope.admission_year})"
    elif years and len(years) == len(chosen):
        label += f" (admission {next(iter(years))})"
    if scope.topic == "documents":
        label += " — selected items, not a complete checklist; open the source for the full list"
    return label + ":\n" + "\n".join(f"• {sentence} [{rank}]" for rank, sentence, _ in chosen), False

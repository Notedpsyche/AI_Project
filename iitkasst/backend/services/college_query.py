"""Resolve applicant-question scope without importing Doc2Dial agency profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass

YEAR_RE = re.compile(r"\b(20[2-3][0-9])\b")
REFERENCE_RE = re.compile(
    r"\b(it|that|this|those|they|them|there|online|how long|how much|what about|"
    r"next|previous|same|later|then|also|in person|show up)\b",
    re.I,
)
STOPWORDS = {"a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is", "it", "my", "of", "on", "or", "the", "to", "what", "when", "where", "with", "you", "your", "iiit", "kottayam", "institute", "college", "btech", "tech"}
SEMESTERS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
}
CARDINAL_SEMESTERS = {
    "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8,
}
FEE_COMPONENT_PATTERNS = (
    ("total fee", r"\b(total|overall|complete)\b.*\b(fees?|charges?|amount|pay)\b|\ball first[- ]semester charges\b"),
    ("hostel maintenance", r"\b(hostel|facility)\b.*\b(maintenance|fee|charge|amount)\b"),
    ("mess advance", r"\bmess advance\b"),
    ("medical insurance", r"\bmedical insurance\b"),
    ("mess equipment maintenance", r"\bmess equipment\b"),
    ("sports equipment maintenance", r"\bsports[- ]?equipment\b"),
    ("club activities", r"\bclub activit(?:y|ies)\b"),
    ("caution deposit", r"\bcaution deposit\b"),
    ("convocation fee", r"\bconvocation\b"),
    ("alumni fee", r"\balumni\b"),
    ("tuition fee", r"\btuition\b"),
)
DOCUMENT_ITEM_PATTERNS = (
    ("laptop requirement", r"\blaptop\b|\b(?:minimum|required) (?:computer|system) (?:configuration|setup|requirements?)\b"),
    ("jee admit card", r"\bjee\b.*\badmit card\b|\badmit card\b.*\bjee\b"),
    ("jee score card", r"\bjee\b.*\bscore ?card\b|\bscore ?card\b.*\bjee\b"),
    ("character certificate", r"\bcharacter(?: and conduct)? certificate\b"),
    ("aadhaar", r"\baadhaar\b"),
    ("passport photographs", r"\bpassport[- ]size (?:photos?|photographs?)\b"),
    ("passport", r"\bpassport\b"),
    ("vaccination proof", r"\b(vaccination|vaccine|chickenpox|hepatitis)\b"),
    ("transfer certificate", r"\b(?:school leaving|transfer) certificate\b"),
    ("marksheet", r"\bmark ?sheet\b"),
    ("medical certificate", r"\bmedical (?:certificate|report)\b"),
    ("bank passbook", r"\bbank passbook\b"),
    ("address proof", r"\b(?:permanent )?address proof\b|\bproof of permanent address\b"),
)


@dataclass(frozen=True)
class QueryScope:
    query: str
    current_question: str
    use_context: bool
    reason: str
    programme: str
    programmes: tuple[str, ...]
    admission_year: int | None
    qualification_year: int | None
    year_sensitive: bool
    topic: str
    intent: str
    admission_route: str
    requires_route: bool
    semesters: tuple[int, ...]
    fee_components: tuple[str, ...]
    document_items: tuple[str, ...]
    underspecified: bool
    inherited_slots: tuple[str, ...]


def topic_in(text: str) -> str:
    low = text.lower()
    if re.search(r"\b(mattress|pillow|bucket|mug|room items?|basic\b.{0,20}\bitems?)\b", low) and re.search(r"\b(hostel|room|cost|price|purchase)\b", low):
        return "facilities"
    if programme_in(text) and re.search(r"\b(programme|program|degree|curriculum|fields?|areas?|topics?|later semesters?|higher semesters?)\b", low):
        return "programmes"
    if programme_in(text) and not re.search(r"\b(fee|tuition|cost|admission|apply|eligib|document|reporting)\b", low):
        return "programmes"
    if re.search(r"\b(e-?m\.?\s*tech|ph\.?\s*d)\b", low) and re.search(r"\b(subject|group|discipline|field|area|programme|program)\w*\b", low):
        return "programmes"
    if re.search(r"\b(placements?|recruit\w*|hiring|hired|employers?|jobs?|salary packages?|packages?|career outcomes?|secured jobs?)\b", low):
        return "placements"
    if re.search(r"\b(departments?|academic units?)\b", low):
        return "departments"
    if re.search(r"\b(scholarships?|financial assistance)\b", low):
        return "scholarships"
    if re.search(
        r"\b(fees?|tuition|payment|pay|cost|deposit|charges?|amount|mess advance|maintenance|"
        r"insurance|alumni|convocation|club activit|sports equipment)\w*\b",
        low,
    ):
        return "fees"
    if re.search(
        r"\b(documents?|certificates?|verification|proof|records?|admit card|score ?card|aadhaar|"
        r"passport|photos?|photographs?|vaccination|vaccine|marksheet|mark sheet|laptop|computer configuration)\b",
        low,
    ):
        return "documents"
    if re.search(r"\b(portal|data entry|sign in|log in)\b", low):
        return "portal"
    if re.search(r"\b(orientation|reporting|show up|in person|class commencement|commencement of classes)\b", low):
        return "admissions"
    if re.search(r"\b(hostels?|campus|facilit|library|laborator|sports facilit|accommodation|housed|room items?|conveyance|transport|travel|hotels?)\w*\b", low):
        return "facilities"
    if re.search(r"\b(admission|apply|eligib|jee|josaa|csab|dasa)\w*\b", low):
        return "admissions"
    if re.search(r"\b(programme|program|branch|course|speciali[sz]ation|curriculum|degree|e-?m\.?tech|ph\.?d)\w*\b", low):
        return "programmes"
    return ""


def route_in(text: str) -> str:
    dasa = bool(re.search(r"\bDASA\b", text, re.I))
    josaa = bool(re.search(r"\b(JoSAA|CSAB)\b", text, re.I))
    if dasa and josaa:
        return ""
    if dasa:
        return "DASA"
    if josaa:
        return "JoSAA/CSAB"
    return ""


def programmes_in(text: str) -> tuple[str, ...]:
    """Return every explicitly named programme in textual order.

    The legacy application uses ``programme`` in several places, but comparisons
    must not lose their second (or later) target before eligibility filtering.
    """
    low = text.lower()
    patterns = (
        ("e-M.Tech", r"\be-?m\.?\s*tech\b"),
        ("PhD", r"\bph\.?\s*d\b|\bdoctoral\b"),
        ("B.Tech Cyber Security", r"\b(cyber security|cybersecurity|digital forensics)\b"),
        ("B.Tech AI and Data Science", r"\b(ai\s*(?:&|and)\s*(?:data science|ds)|artificial intelligence and data science)\b"),
        ("B.Tech Mathematics and Computing", r"\b(mathematics and computing|mnc)\b"),
        ("B.Tech ECE", r"\b(ece|electronics and communication|electronics (?:degree|programme|program))\b"),
        ("B.Tech CSE", r"\b(cse|computer science and engineering)\b"),
    )
    matches = [(match.start(), label) for label, pattern in patterns if (match := re.search(pattern, low))]
    specific_btech = any(label.startswith("B.Tech ") for _, label in matches)
    if not specific_btech and re.search(r"\b(b\.?tech|bachelor of technology|ug|undergraduate)\b", low):
        generic = re.search(r"\b(b\.?tech|bachelor of technology|ug|undergraduate)\b", low)
        if generic:
            matches.append((generic.start(), "B.Tech"))
    ordered = [label for _, label in sorted(matches) if label]
    return tuple(dict.fromkeys(ordered))


def programme_in(text: str) -> str:
    """Compatibility wrapper for singular callers."""
    return next(iter(programmes_in(text)), "")


def query_terms(text: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[a-zA-Z]{3,}", text) if word.lower() not in STOPWORDS}


def normalized_terms(text: str) -> set[str]:
    """Normalize simple inflections for matching a question to cited words."""
    terms = set()
    for word in query_terms(text):
        if word.endswith("ies") and len(word) > 5:
            word = word[:-3] + "y"
        elif word.endswith("ly") and len(word) > 5:
            word = word[:-2]
        elif word.endswith("s") and len(word) > 4 and not word.endswith(("ss", "us")):
            word = word[:-1]
        if word == "programme":
            word = "program"
        if word in {"apply", "application", "admissions"}:
            word = "admission"
        if word in {"courses", "degree", "degrees", "branches"}:
            word = "program"
        if word in {"charged", "charge", "charges", "amount", "cost"}:
            word = "fee"
        if word in {"photo", "photos", "photograph", "photographs"}:
            word = "photograph"
        if word in {"hired", "hiring", "employer", "employers", "recruiter", "recruiters", "jobs"}:
            word = "placement"
        if word in {"travel", "transport"}:
            word = "conveyance"
        if word in {"mix", "mixed"}:
            word = "blend"
        if word in {"later", "higher"}:
            word = "advanced"
        if word in {"emails", "email"}:
            word = "mail"
        terms.add(word)
    return terms


def semester_numbers(text: str, previous: str = "") -> tuple[int, ...]:
    low = text.lower()
    has_semester_context = bool(re.search(r"\b(?:semesters?|terms?)\b", low))
    found = [number for word, number in SEMESTERS.items() if has_semester_context and re.search(rf"\b{word}\b", low)]
    found.extend(
        number for word, number in CARDINAL_SEMESTERS.items()
        if re.search(rf"\b(?:{word}[- ](?:semester|term)|(?:semester|term)[- ]{word})s?\b", low)
    )
    found.extend(int(number) for number in re.findall(r"\b([1-8])(?:st|nd|rd|th)?[- ]semester\b", low))
    if re.search(r"\bnext semester\b", low) and previous:
        previous_numbers = semester_numbers(previous)
        if previous_numbers and max(previous_numbers) < 8:
            found.append(max(previous_numbers) + 1)
    return tuple(dict.fromkeys(found))


def fee_components_in(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in FEE_COMPONENT_PATTERNS if re.search(pattern, text, re.I))


def implied_tuition_fee(text: str, topic: str, semesters: tuple[int, ...], components: tuple[str, ...]) -> bool:
    """Resolve an unqualified per-semester fee to the labelled tuition row.

    The fee table has several rows that carry semester columns (including
    one-time charges whose later-semester cell is ``-``).  A question phrased
    as "the fee for the second semester" therefore needs a conservative,
    explicit default rather than treating every row as an interchangeable fee.
    Requests that name a component keep that component unchanged.
    """
    return bool(
        topic == "fees"
        and semesters
        and not components
        and re.search(r"\b(?:the\s+)?fee\b[^?.!]{0,60}\b(?:for|in)\b[^?.!]{0,60}\bsemester\b", text, re.I)
    )


def document_items_in(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in DOCUMENT_ITEM_PATTERNS if re.search(pattern, text, re.I))


def qualification_year_in(text: str) -> int | None:
    match = re.search(
        r"\b(?:class\s*12|12th|qualifying examination|passed|passing|finished|completed)\b[^.]{0,35}\b(20[2-3][0-9])\b",
        text,
        re.I,
    )
    return int(match.group(1)) if match else None


def intent_in(text: str, topic: str, programme: str) -> str:
    low = text.lower()
    if topic == "placements":
        if re.search(r"\b(employers?|companies|recruiters?|hired)\b", low):
            return "placement_recruiters"
        return "placement_statistics"
    if topic == "scholarships":
        if re.search(r"\b(which|what|who)\b.*\b(bodies|authorities|organisations?|organizations?|agencies)\b|\b(state government|other authorities)\b", low):
            return "scholarship_authorities"
        if re.search(r"\b(schemes?|award amounts?|income limits?|eligibility limits?)\b", low):
            return "scholarship_details"
        if re.search(r"\b(forward|paperwork|documents?|support)\b", low):
            return "scholarship_support"
        return "scholarships"
    if re.search(r"\b(?:department|unit) head\b|\bwho\b.*\bhead\b", low):
        return "department_head"
    if re.search(r"\b(laborator(?:y|ies)|labs?)\b.*\b(where|building|located|location)\b|\bwhich buildings?\b.*\blaborator", low):
        return "laboratory_location"
    if re.search(r"\bhotels?\b", low) and re.search(r"\b(phone|contact|price|rate|nightly|cost)\w*\b", low):
        return "hotel_details"
    if topic == "facilities":
        if re.search(r"\b(mattress|pillow|bucket|mug|room items?|basic items?)\b", low):
            return "hostel_items"
        if re.search(r"\b(conveyance|transport|travel|commute)\b", low):
            return "hostel_transport"
        if re.search(r"\b(first[- ]year|freshmen|male students?|boy students?)\b.*\b(hostel|housed|accommodat)", low):
            return "first_year_housing"
        return "facilities"
    if topic == "fees":
        if "total fee" in fee_components_in(text):
            return "fee_total"
        if len(fee_components_in(text)) > 1 or re.search(r"\b(both|same amount|compare)\b", low):
            return "fee_comparison"
        return "fee_component" if fee_components_in(text) else "fees"
    if topic in {"admissions", "portal"} and re.search(r"\bhow many\b.*\b(sections?|steps?)\b|\bmandatory\b.*\bsteps?\b", low):
        return "portal_steps"
    if topic in {"admissions", "portal", "documents"} and re.search(r"\b(after|once)\b.*\b(final|last)\b.*\b(submit|submission)\b|\bconfirmation\b.*\b(report|document|mail|email)\b", low):
        return "portal_confirmation"
    if topic == "documents":
        return "document_item" if document_items_in(text) else "document_checklist"
    if topic == "admissions" and re.search(r"\b(eligib(?:ility|le)?|qualif(?:y|ication)|minimum requirement)\b", low):
        return "eligibility"
    if topic == "admissions" and re.search(r"\b(deadline|last date|closing date|apply by|application closes?)\b", low):
        return "admission_deadline"
    if topic == "admissions" and re.search(r"\b(report|reporting|show up|in person)\b", low):
        return "reporting_schedule"
    if topic == "admissions" and re.search(r"\borientation\b", low):
        return "orientation"
    if topic == "admissions" and re.search(r"\b(class(?:es)?|semester)\b.*\b(start|begin|commence)|\bcommencement\b", low):
        return "class_commencement"
    if topic == "admissions" and re.search(
        r"\b(how\s+(?:do|can|should)\s+\w*\s*(?:apply|get admission)|how\s+to\s+apply|application\s+process|admission\s+process|steps?\s+to\s+apply)\b",
        low,
    ):
        return "admission_process"
    if topic in {"admissions", "portal"} and re.search(
        r"\b(enter|submit|fill)\w*\b.*\b(applicant|application|admission|institute)?\s*(details?|data)\b|\bdata entry\b",
        low,
    ):
        return "admission_data_entry"
    if topic == "programmes" and programme.startswith("B.Tech ") and re.search(r"\b(what is|tell me about|describe)\b", low):
        return "programme_description"
    if topic == "programmes" and programme in {"e-M.Tech", "PhD"} and re.search(
        r"\b(name|which|what|list|both|subject groupings?|disciplines?|areas?)\b", low
    ):
        return "programmes_list"
    if topic == "programmes" and (
        re.search(r"\b(available|offered|offer)\b.*\b(programmes?|programs?|courses?|branches|degrees?)\b", low)
        or re.search(r"\b(?:what|which)\b.*\b(programmes?|programs?|courses?|branches|degrees?)\b", low)
        or "academic offerings" in low
    ):
        return "programmes_list"
    if topic == "programmes" and re.search(r"\b(fields?|areas?|topics?|careers?|research areas?|disciplines?|later semesters?|higher semesters?)\b", low):
        return "programme_fields"
    if topic == "programmes" and programme:
        return "programme_description"
    if topic == "departments" and re.search(r"\b(list|available|offered)\b.*\bdepartments?\b|\b(?:what|which)\s+(?:academic\s+)?departments?\s+(?:are|exist)", low):
        return "departments_list"
    return topic or "general"


def resolve_scope(message: str, conversation: list[dict[str, str]]) -> QueryScope:
    previous = next((item["content"] for item in reversed(conversation[-6:]) if item.get("role") == "user" and item.get("content", "").strip()), "")
    current_programmes = programmes_in(message)
    current_qualification_year = qualification_year_in(message)
    current_years = [int(year) for year in YEAR_RE.findall(message)]
    current_year = next((year for year in current_years if year != current_qualification_year), None)
    has_reference = bool(REFERENCE_RE.search(message))
    current_topic_name = topic_in(message)
    continuation = has_reference or bool(re.match(r"\s*(and|also|then)\b", message, re.I))
    continuation = continuation or bool(re.search(r"\b(show up|in person|next semester|later semesters?)\b", message, re.I))
    underspecified_follow_up = continuation and (not current_topic_name or len(query_terms(message)) <= 5)
    # Explicit programme/year changes are new scopes, even in a short message.
    previous_programmes = programmes_in(previous)
    programme_change = bool(current_programmes and previous_programmes and current_programmes != previous_programmes)
    previous_admission_years = [int(year) for year in YEAR_RE.findall(previous) if int(year) != qualification_year_in(previous)]
    previous_year = previous_admission_years[0] if previous_admission_years else None
    year_change = bool(current_year and previous_year and current_year != previous_year)
    use_context = bool(previous and underspecified_follow_up and not (programme_change or year_change))
    effective = f"{previous}\nCURRENT QUESTION: {message.strip()}" if use_context else message.strip()
    inherited_slots: list[str] = []
    programmes = current_programmes or (previous_programmes if use_context else ())
    if use_context and not current_programmes and programmes:
        inherited_slots.append("programmes")
    programme = next(iter(programmes), "")
    year = current_year or (previous_year if use_context else None)
    if use_context and not current_year and year is not None:
        inherited_slots.append("admission_year")
    qualification_year = current_qualification_year or (qualification_year_in(previous) if use_context else None)
    year_sensitive = bool(year or re.search(r"\b(fee|cost|admission|apply|eligib|deadline|date|schedule|documents?|reporting|payment)\w*\b", effective, re.I))
    reason = "Follow-up inherits the previous user question." if use_context else "Standalone question or explicit new scope."
    current_route = route_in(message)
    route = current_route or (route_in(previous) if use_context else "")
    if use_context and not current_route and route:
        inherited_slots.append("admission_route")
    topic = current_topic_name or (topic_in(previous) if use_context else "")
    intent = intent_in(effective, topic, programme)
    if topic == "programmes" and len(programmes) > 1:
        intent = "programme_comparison"
    current_items = document_items_in(message)
    items = current_items or (document_items_in(previous) if use_context else ())
    if use_context and not current_items and items:
        inherited_slots.append("document_items")
    requires_route = (intent == "document_checklist" or bool(re.search(r"\b(online|payment process|remaining fee|where to pay)\b", message, re.I) and topic == "fees"))
    current_semesters = semester_numbers(message, previous if use_context else "")
    semesters = current_semesters or (semester_numbers(previous) if use_context else ())
    if use_context and not current_semesters and semesters:
        inherited_slots.append("semesters")
    current_fee_components = fee_components_in(message)
    fee_components = current_fee_components or (fee_components_in(previous) if use_context else ())
    if implied_tuition_fee(message, topic, current_semesters, current_fee_components):
        # The official table labels the recurring semester charge "Tuition Fee".
        # Do not apply this default to named components or vague fee questions.
        current_fee_components = ("tuition fee",)
        fee_components = current_fee_components
        intent = "fee_component"
    if use_context and not current_fee_components and fee_components:
        inherited_slots.append("fee_components")
    standalone_underspecified = not use_context and not topic and not programme and len(query_terms(message)) <= 4
    return QueryScope(
        effective,
        message.strip(),
        use_context,
        reason,
        programme,
        programmes,
        year,
        qualification_year,
        year_sensitive,
        topic,
        intent,
        route,
        requires_route,
        semesters,
        fee_components,
        items,
        standalone_underspecified,
        tuple(inherited_slots),
    )


def eligible(chunk: dict, scope: QueryScope) -> bool:
    if scope.underspecified:
        return False
    if scope.requires_route and not scope.admission_route:
        return False
    heading_route = route_in(str(chunk.get("heading_path", [""])[-1]))
    if scope.topic == "documents" and scope.intent not in {"portal_confirmation", "portal_steps"}:
        if "documents" not in set(chunk.get("topics") or []):
            return False
        if scope.admission_route and heading_route != scope.admission_route:
            return False
    if scope.admission_route and heading_route and heading_route != scope.admission_route:
        return False
    section = " ".join(chunk.get("heading_path", [])) + " " + str(chunk.get("text", ""))
    if scope.admission_route == "DASA" and re.search(r"\b(JoSAA|CSAB)\b", section, re.I) and not re.search(r"\bDASA\b", section, re.I):
        return False
    if scope.admission_route == "JoSAA/CSAB" and re.search(r"\bDASA\b", section, re.I) and not re.search(r"\b(JoSAA|CSAB)\b", section, re.I):
        return False
    chunk_topics = set(chunk.get("topics") or [])
    if scope.intent in {"admission_process", "admission_data_entry", "portal_steps", "portal_confirmation"}:
        if not chunk_topics.intersection({"admissions", "portal"}) or chunk_topics.intersection({"documents", "fees"}):
            return False
    elif scope.intent == "programmes_list":
        if "programmes" not in chunk_topics or chunk_topics.intersection({"documents", "fees", "portal"}):
            return False
    elif scope.intent == "departments_list":
        if "departments" not in chunk_topics or "available departments" not in str(chunk.get("heading_path", [""])[-1]).lower():
            return False
    elif scope.intent in {"placement_statistics", "placement_recruiters"} and "placements" not in chunk_topics:
        return False
    elif scope.intent in {"department_head"} and "departments" not in chunk_topics:
        return False
    elif scope.intent in {"laboratory_location", "hotel_details"}:
        if "facilities" not in chunk_topics:
            return False
    elif scope.intent in {"hostel_items", "hostel_transport", "first_year_housing"}:
        if not chunk_topics.intersection({"facilities", "documents", "admissions"}):
            return False
    elif scope.topic and chunk_topics and scope.topic not in chunk_topics:
        return False
    source_programme = str(chunk.get("programme") or "")
    requested_programmes = scope.programmes or ((scope.programme,) if scope.programme else ())
    # A comparison has a closed entity set. Generic admission-overview chunks
    # cannot stand in for either requested programme merely because they happen
    # to mention both names in passing.
    if scope.intent == "programme_comparison":
        return source_programme in requested_programmes
    if requested_programmes and source_programme:
        compatible = any(
            source_programme == requested
            or (source_programme == "B.Tech" and requested.startswith("B.Tech"))
            or (requested == "B.Tech" and source_programme.startswith("B.Tech"))
            for requested in requested_programmes
        )
        if not compatible:
            return False
    source_year = chunk.get("admission_year")
    if scope.admission_year and source_year and int(source_year) != scope.admission_year:
        return False
    if scope.year_sensitive and chunk.get("year_conflict"):
        return False
    # A source without year metadata must not answer an explicit year-specific question.
    if scope.admission_year and not source_year and scope.year_sensitive:
        return False
    return True

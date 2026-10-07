# Doc2Dial Closed-Domain IR — Current Implementation Diagnosis

> Read-only diagnosis. No implementation code was modified.

## Pipeline trace

```text
POST /chat
→ backend/api/routes.py:chat (lines 44-51)
→ backend/services/retrieval_service.py:RetrievalService.search (line 15)
→ backend/services/context_service.py:decide_context (line 68)
→ context_query (line 116) only when context is accepted
→ src/doc2dial_retrieval/search.py:SearchEngine.search_all (line 58)
→ SearchEngine._retrieve (line 49)
→ BM25 + BGE dense retrieval
→ hybrid() RRF merge
→ backend/services/evidence_selector.py:select_evidence (line 136)
→ backend/services/answer_service.py:grounded_answer (line 96)
```

`routes.py:49` passes the current message and conversation to `RetrievalService.search()`.

`retrieval_service.py:22` calls `decide_context()`. The resulting effective query is passed through `SearchEngine.search_all()`.

`search.py:52-54` builds a history-aware query and sends it to both BM25 and BGE. The hybrid RRF result is converted into candidates at `retrieval_service.py:30`.

`retrieval_service.py:37` calls `select_evidence()`. Only its selected results are passed to `grounded_answer()` by `routes.py:50-51`; the full RRF candidate pool is not passed to answer generation.

---

## Failure 1 — Short conversational follow-up

### Reproduction

```text
User: How do I replace my Social Security card?
User: How long does it take?
```

### Where the follow-up decision is made

The decision is made by:

```text
backend/services/context_service.py:68-113
decide_context()
```

The retrieval service calls it at `backend/services/retrieval_service.py:22`.

### Signals used by the decision

`decide_context()` uses:

- the latest previous user query;
- token/Jaccard overlap;
- broad intent groups;
- `REFERENCE_RE` reference phrases;
- `EXPLICIT_TASK_RE` task phrases;
- BGE cosine similarity between current and previous user queries;
- an `information_change` penalty for disjoint intent groups.

The relevant code is `context_service.py:78-100`:

```python
previous = users[-1]["content"].strip()
current_tokens, previous_tokens = _tokens(message), _tokens(previous)
overlap = len(current_tokens & previous_tokens) / max(
    len(current_tokens | previous_tokens), 1
)
current_groups = _intent_groups(message)
previous_groups = _intent_groups(previous)
reference = bool(REFERENCE_RE.search(message))
explicit_task = bool(EXPLICIT_TASK_RE.search(message))
information_change = bool(
    current_groups
    and previous_groups
    and current_groups.isdisjoint(previous_groups)
)
```

The context score is computed from semantic similarity, reference detection, and topic continuity. If `information_change` is true, `0.55` is subtracted and all context acceptance branches are blocked.

### Exact reason this case fails

The intent groups are defined in `context_service.py:17-24`:

```python
"card": {"card", "replace", "replacement", "number"}
"status": {"status", "check", "where", "when", "long"}
```

The two queries are therefore classified approximately as:

```text
previous_groups = {card}
current_groups  = {status}
```

This makes the following expression true at `context_service.py:87`:

```python
information_change = True
```

The context score is reduced at lines 93-94:

```python
if information_change:
    score -= 0.55
```

Every context branch at lines 97-100 requires `not information_change`, so context is rejected even though `REFERENCE_RE` recognizes `how long`.

The root cause is:

> The context detector interprets a duration/status question as a new task instead of as a dependent question about the previous task.

Low lexical overlap and potentially low BGE similarity make the query more fragile, but the decisive blocker is `information_change=True`.

### Is reformulation happening?

For this failing case, no.

At `context_service.py:111-113`:

```python
recent = [users[-1]]
effective = context_query(message, recent) if use_context else message.strip()
```

Since `use_context` is false, the effective query remains:

```text
How long does it take?
```

`context_query()` is not called.

When context is accepted, reformulation does happen and produces:

```text
USER: How do I replace my Social Security card?
CURRENT QUESTION: How long does it take?
```

That augmented query is then used by BM25 and BGE through `SearchEngine.build_query()` and `_retrieve()`.

### Where conversation history is stored and passed

The API schema stores conversation messages at `backend/api/schemas.py:11`:

```python
conversation: list[Message] = Field(default_factory=list)
```

The route passes them at `routes.py:49`.

`bounded_history()` at `context_service.py:45-48` keeps the latest messages. `_user_turns()` at lines 64-65 filters them to user messages only. If context is accepted, `retrieval_service.py:24-27` passes only the immediately previous user query:

```python
recent = (
    [{"role": "user", "content": user_turns[-1]["content"]}]
    if decision.use_context
    else []
)
```

The previous assistant answer is deliberately excluded from reformulation. It is not propagated into retrieval.

### Smallest correct fix location

```text
backend/services/context_service.py:decide_context()
```

The relevant interaction is between `REFERENCE_RE`, `_intent_groups()`, `information_change`, and the `use_context` conditions. This must be corrected before BM25, BGE, RRF, evidence selection, or answer generation.

---

## Failure 2 — Wrong task despite relevant retrieval

### Reproduction

```text
What documents do I need to apply for Social Security?
```

### How task intent is represented

Intent is represented by `backend/services/intent_service.py:23-28`:

```python
QueryIntent(
    text,
    task_groups,
    task_terms,
    answer_type,
)
```

`classify_intent()` is at lines 35-48. The example query is likely classified as:

```text
task_groups = {application}
answer_type = requirements
```

The task groups are broad lexical categories:

```text
address, application, benefits, complaint, card, fraud, status
```

They do not represent precise tasks such as:

```text
social_security_benefit_application
social_security_card_replacement
social_security_address_change
```

### Does the system distinguish the Social Security tasks?

Only partially. Application and card evidence can share terms such as:

```text
documents, proof, application, identity
```

The system therefore does not robustly distinguish benefits application from card application/replacement using a precise information-need representation.

### Where evidence is scored and selected

Selection occurs in:

```text
backend/services/evidence_selector.py:136-203
select_evidence()
```

Each candidate receives semantic, BM25, RRF, domain, lexical intent, quality, task-match, and contradiction values. The final score at lines 160-169 is:

```python
score = (
    config.semantic_weight * semantic[index]
    + config.bm25_weight * bm25[index]
    + config.rrf_weight * rrf[index]
    + config.domain_weight * domains[index]
    + config.intent_weight * intent
    + config.quality_weight * quality
    + config.task_weight * task
    - config.contradiction_weight * contradiction
    - intent_conflict_penalty
)
```

The task component comes from `backend/services/intent_service.py:51-65`, `task_match()`. It compares broad group intersection and lexical overlap.

### Is relevance only semantic similarity?

No. The selector uses both retrieval scores and task-aware features. However, the task signal is a lightweight lexical heuristic, not precise task classification.

### Why card evidence can survive

The existing card/application conflict rule is at `intent_service.py:57-62`:

```python
card_application_conflict = (
    "application" in query.task_groups
    and "card" in candidate.task_groups
    and not re.search(
        r"\b(retirement|benefit|benefits|medicare)\b",
        candidate_lower,
    )
)
```

This guard depends on candidate lexical classification and is narrow. Card evidence can remain eligible if:

- its text is not classified into the `card` group;
- it shares application/document vocabulary;
- it contains benefit-related terms that disable this conflict rule;
- or its semantic, BM25, RRF, and same-domain scores remain high.

Candidates are removed only when `contradiction_penalty == 1.0` and compatible candidates exist, at `evidence_selector.py:174-176`. Broad same-domain scoring keeps Social Security candidates together but does not distinguish Social Security card content from Social Security benefits content.

The root cause is:

> Evidence selection has task-aware scoring, but its task representation is too coarse and its contradiction rule is too narrow to reliably separate benefits-application requirements from card-document requirements.

### Why the answer becomes weak or partial

`grounded_answer()` calls `_relevant_sentences()` at `answer_service.py:101`. That function applies the same coarse task matcher to selected sentences. For a requirements query, the answer branch at lines 133-141 keeps claims containing words such as `document`, `proof`, `identity`, `required`, `need`, or `eligibility`.

If card evidence is selected, the answer generator cannot recover correct benefits-application facts from candidates already discarded by the selector. It may emit card-document claims or return:

```text
The available documents provide only partial information about the requirements.
```

The answer generator exposes the selection error; it is not the first source of the wrong task.

### Smallest correct fix location

```text
backend/services/intent_service.py:task_match()
backend/services/evidence_selector.py:select_evidence()
```

The task distinction and contradiction/filtering logic should be corrected before final evidence selection. Do not change BM25, BGE, or RRF for this problem.

Only if testing shows that correct benefits-application evidence is selected but card claims still leak should `answer_service.py` be changed.

---

## D. Root-cause summary

### Failure 1

- **Function/file:** `backend/services/context_service.py:decide_context()`
- **Current behavior:** `How long does it take?` becomes `status`; the previous card question becomes `card`.
- **Why it fails:** Disjoint groups set `information_change=True`, blocking every context path.
- **Consequence:** The effective query remains standalone, so reformulation does not run.
- **Missing information:** The detector does not represent duration/status as a follow-up to the previous task.

### Failure 2

- **Functions/files:** `backend/services/intent_service.py:classify_intent()` and `task_match()`, plus `backend/services/evidence_selector.py:select_evidence()`
- **Current behavior:** Broad application/card/benefits groups overlap through document vocabulary.
- **Why it fails:** Wrong-task card evidence can remain competitive on semantic, BM25, RRF, domain, and lexical scores.
- **Consequence:** Only selected wrong evidence reaches answer generation.
- **Missing information:** A precise distinction between benefits application, card replacement, address change, and other Social Security tasks.

---

## E. Required focused tests

### 1. Card replacement → duration follow-up

```text
User: How do I replace my Social Security card?
User: How long does it take?
```

Assert:

```text
context_used == true
context_decision == "USE_CONTEXT"
reformulated_query contains the prior card question and current question
selected evidence concerns Social Security card processing/time
```

### 2. Address change → online follow-up

```text
User: How do I change my address with Social Security?
User: Can I do it online?
```

Assert:

```text
context_used == true
selected evidence concerns address changes
answer addresses whether the task can be completed online
```

### 3. Benefits application requirements

```text
User: What documents do I need to apply for Social Security?
```

Assert:

```text
information_need identifies application/benefits intent
selected evidence is benefits-application evidence
selected evidence is not exclusively Social Security-card evidence
answer claims do not describe obtaining or replacing a Social Security card
```

### 4. New-topic isolation

```text
User: How do I replace my Social Security card?
User: How do I register a vehicle?
```

Assert:

```text
context_used == false
context_decision == "STANDALONE"
results concern vehicle registration
the effective query does not inherit the Social Security card topic
```

## Final diagnosis

```text
Failure 1 → context detection/gating
             reformulation is skipped before retrieval

Failure 2 → task-aware evidence selection
             coarse intent compatibility allows wrong-task evidence to survive
```

The current implementation does not indicate that BGE, BM25, or RRF should be replaced. The first correction point is context gating. The second correction point is task representation and contradiction logic used by evidence selection.

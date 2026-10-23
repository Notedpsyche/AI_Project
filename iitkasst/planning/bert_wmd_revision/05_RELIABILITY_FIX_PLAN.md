# Reliability Fix Plan

## Presentation-safe boundary

Implement only four confirmed, bounded defects before WMD. Corpus expansion, hierarchical ingestion, fee aggregation, complete FSM, removal of all hard-coded answer facts, and independent evaluation move to the post-presentation track.

## Fix 1 — Closed evidence sufficiency

- **Severity/effort/risk:** Critical / medium / medium.
- **Files:** `backend/services/college_select.py`, `backend/services/college_query.py`, `tests/test_college_reliability_regressions.py`.
- **Current defect:** `supports_request` and `evidence_set_sufficient` default to true for unmodeled requests, allowing same-domain but wrong-attribute evidence.
- **Implementation:** introduce explicit `eligibility` and `admission_deadline` intents. Dispatch every recognized intent to a named support predicate. `general`, unknown, and incomplete operations return false. Preserve known current behavior by explicitly covering each existing intent rather than using a generic allow-all fallback.
- **Invariant:** an official passage is accepted only when programme/year/route eligibility and intent/attribute support both pass.
- **Tests:** PhD eligibility cannot use B.Tech admission text; a deadline question cannot use “FINAL SUBMIT”; unknown intent yields no selected evidence; existing admission-process and programme-list evidence still pass.
- **Acceptance:** complete default suite passes; known irrelevant-answer regressions abstain when required evidence is absent.
- **Rollback:** revert only the contract dispatch and new intents; no index/data change.

## Fix 2 — Preserve multiple programmes

- **Severity/effort/risk:** Critical / medium / medium.
- **Files:** `backend/services/college_query.py`, `backend/services/college_select.py`, narrow branch in `college_answer.py`, regression tests.
- **Current defect:** `programme_in` returns one value; “CSE and ECE” collapses to ECE and eligibility removes CSE.
- **Implementation:** add `programmes_in`; keep `programme` as first target for compatibility; add tuple field to `QueryScope`. Eligibility accepts candidates for any requested target. Comparison sufficiency requires at least one directly supported passage for every target. The answer branch emits labeled extractive claims only when complete.
- **Invariant:** no mentioned programme disappears between scope, candidate filtering, selected evidence, and cited output.
- **Tests:** CSE/ECE and B.Tech/e-M.Tech parsing; one-target compatibility; incomplete comparison abstains; complete comparison returns evidence for both; unrelated programme excluded.
- **Acceptance:** trace contains both targets and selected evidence groups; existing API schema remains unchanged.
- **Rollback:** compatibility wrapper allows tuple field/branches to be reverted without affecting existing singular callers.

## Fix 3 — Compatible typed slot inheritance

- **Severity/effort/risk:** High / low-medium / medium.
- **Files:** `backend/services/college_query.py`, regression tests.
- **Current defect:** accepted follow-ups inherit text/programme/year but `semesters` is recomputed mainly from the current message; fee/document slots are inconsistently reconstructed.
- **Implementation:** parse current and previous slots separately. If `use_context` and the current turn has no explicit replacement, inherit programme(s), admission year, route, semester(s), fee component(s), and document item(s). Record `inherited_slots`. Explicit programme/year/route/topic change resets incompatible inherited slots.
- **Invariant:** inheritance is slot-by-slot, never unconditional whole-state copying; explicit current values win.
- **Tests:** first-semester fee → “How much is that?” retains semester 1 and tuition; “What about the second semester?” replaces semester; new PhD/2027 topic does not inherit B.Tech/2026; standalone short ambiguity remains unsupported when no compatible history exists.
- **Acceptance:** context regression matrix passes without changing public request payload.
- **Rollback:** remove new inheritance helper and tuple field; previous text-concatenation path remains.

## Fix 4 — Metadata-sensitive deduplication

- **Severity/effort/risk:** High / low / low.
- **Files:** `src/doc2dial_retrieval/retrieval.py`, regression tests.
- **Current defect:** same/near-identical text is deduplicated before eligibility without considering route, year, programme, topic, or conflict flags.
- **Implementation:** compute a normalized scope signature. Only collapse duplicate text when signatures are compatible. Keep stable rank order and current `k` behavior.
- **Invariant:** duplicates that differ in programme, admission year, route, topic set, or year-conflict state both survive.
- **Tests:** identical JoSAA/DASA text survives; 2025/2026 survives; same-scope exact duplicate collapses; near-duplicate threshold behavior remains; hybrid fields preserved.
- **Acceptance:** no correctly scoped fixture is removed before eligibility and existing search tests pass.
- **Rollback:** revert the signature guard; no index rebuild is required because dedupe is runtime-only.

## Fix order and gates

1. Freeze baseline.
2. Closed evidence contracts.
3. Multi-programme scope/selection/answer compatibility.
4. Slot inheritance.
5. Metadata-sensitive dedupe.
6. Run all Python tests, Ruff, API smoke, and the 45-case development regression before adding POT.

Each fix is a separate commit candidate, although this planning task performs no commits. Do not continue to WMD if a fix lowers the known development suite or changes `/api/chat` response shape.

## Deferred defects

| Defect | Why deferred | Post-presentation work |
|---|---|---|
| Missing source coverage | Requires source review and corpus/index rebuild. | Versioned official-source expansion. |
| Flattened tables/headings | Ingestion migration is broader than demo scope. | Hierarchical nodes and atomic table/list facts. |
| Total eight-semester fees | Requires complete structured components and deterministic arithmetic. | Operation-aware evidence/answer plan. |
| Full dialogue FSM | Current slot inheritance is a safe bridge only. | Explicit state machine and clarification states. |
| Hard-coded source facts | Broad composer refactor risks demo stability. | Move all facts to corpus-derived structures. |
| Independent accuracy | Cannot be created credibly overnight. | Human-authored, adjudicated held-out set. |

WMD does not address any of these defects and must not be presented as doing so.


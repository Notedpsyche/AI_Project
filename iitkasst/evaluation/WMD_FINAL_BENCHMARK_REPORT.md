# BERT + exact WMD final benchmark report

**Run date:** 23 October 2026  
**Scope:** user-approved, source-checked pilot only; this is not an independent held-out evaluation.  
**Production impact:** none. The React/FastAPI application remains on BM25 + BGE-base + FAISS + RRF.

## Dataset finalization

The original proposal file, `wmd_proposed_annotations.jsonl`, remains unchanged. The scored input is [wmd_reviewed_verified_pilot.jsonl](wmd_reviewed_verified_pilot.jsonl). It has nine source-checked cases and preserves the explicit field `verification_status: user-approved; ... not an independent evaluation` on every row.

Direct refetch verification was performed before scoring. Each official current response exactly matched the SHA-256 held in the local corpus inventory:

| Source document | Official fetch URL | Snapshot match |
| --- | --- | --- |
| UG Admission 2026 | `https://www.iiitkottayam.ac.in/views/admission26.html` | Yes — `d8ec0f7e…39debc` |
| B.Tech fee structure 2026 | `https://www.iiitkottayam.ac.in/views/fees.html` | Yes — `ef92941a…4bbb9c` |
| Scholarships | `https://www.iiitkottayam.ac.in/views/scholarship.html` | Yes — `04d4bd77…eebe3` |
| B.Tech CSE | `https://www.iiitkottayam.ac.in/views/btech_cs_home.html` | Yes — `3cf76c67…3a557c` |
| B.Tech ECE | `https://www.iiitkottayam.ac.in/views/btech_ec_home.html` | Yes — `283b1263…0dd973` |
| 2026 portal guide | `https://www.iiitkottayam.ac.in/data/pdf/BTech_Admission_Student_Application_Process_2026.pdf` | Yes — `d759d913…eec72` |

### Scored cases: 9

| ID | Gold evidence/fact treatment |
| --- | --- |
| P01 | `ug-admission-2026::2aa547656f2faa42` — complete 2026 B.Tech programme list. |
| P03 | `btech-cse::0c6c7d782ff9a313` — direct CSE programme overview. |
| P04 | `btech-cse::0c6c7d782ff9a313` **and** `btech-ece::d7818d2d1c0ae031` — complete-evidence-set required. |
| A01 | `ug-admission-2026::6e63924cd2367402` — primary B.Tech route/process. Portal pages are graded supporting evidence. |
| A05 | `admission-portal-guide-2026::ebc44eab8e3de09f` — seven mandatory steps. |
| A06 | Canonical: `ug-admission-2026::afd0bf3c287a9f77`; equivalent route duplicate retained: `ug-admission-2026::3dc991be67644879`. |
| F01 | Canonical: `btech-fees-2026::8cf5ae1257ed36b1`; equivalent official tuition statement retained: `ug-admission-2026::cb7496ad5bca0382`. Recall/MRR use the canonical fact to avoid duplicate-fact inflation. |
| S01 | `scholarships::97cd825f583968a3` — State Government/other authorities. |
| C01 | `ug-admission-2026::60f72dbfdfa73745` — mattress, pillow, bucket, mug. The gold fact preserves the source wording: it says **all students**, not first-year students only. |

### Excluded cases: 8

| ID(s) | Reason |
| --- | --- |
| P02 | “Undergraduate computing degrees” has no agreed inclusion policy. |
| A03, A04 | Each full route checklist is split over 18/19 document rows. Treating every row as ordinary gold would cap Recall@10 below 1.0; these require grouped checklist-coverage evaluation. |
| F02 | Conversational follow-up. It needs F01 as prior user context; the current WMD runner is intentionally single-turn. |
| P05, A02, F03, X01 | Candidate abstention cases still require a corpus-coverage review before they become verified no-positive judgments. |

## Ranking comparison

All systems used the same nine queries and current local corpus. WMD reranked only the first 15 metadata-eligible RRF candidates using exact balanced optimal transport. This is therefore **RRF → WMD reranking**, not standalone WMD retrieval.

| Method | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| BM25 | 0.8889 | 0.8889 | 0.7500 | 0.8166 |
| BGE-base dense retrieval | 0.8889 | 0.8889 | 0.8333 | 0.8534 |
| BM25 + BGE RRF | **0.8889** | **0.8889** | **0.8889** | **0.8835** |
| RRF → BERT + exact WMD | 0.7778 | 0.7778 | 0.5278 | 0.6155 |

### Candidate recall before WMD

The top-15 eligible RRF pool contained the canonical gold fact for **8/9 cases (88.9%)**. A06 had no eligible candidate because its current query scope resolves to `general`; WMD therefore had no candidate to recover. P04 contained both required programme chunks in the top 15.

### Complete-evidence-set result for P04

Both CSE and ECE passages were within the top 10 for every method:

| Method | CSE rank | ECE rank | Complete at 10 |
| --- | ---: | ---: | --- |
| BM25 | 1 | 4 | Yes |
| BGE | 1 | 2 | Yes |
| RRF | 1 | 2 | Yes |
| RRF → WMD | 1 | 4 | Yes |

WMD did not break completeness, but it demoted the ECE evidence relative to BGE/RRF.

## Per-question outcomes

Values are first canonical-gold rank. `—` means no eligible retrieved candidate. WMD ranks are within the same RRF top-15 candidate pool.

| ID | BM25 | BGE | RRF | WMD | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| P01 | 1 | 1 | 1 | 1 | Tie. |
| P03 | 1 | 1 | 1 | 4 | WMD worse. |
| P04 | 1 | 1 | 1 | 1 | First hit tied; ECE fell from 2 to 4. |
| A01 | 4 | 2 | 1 | 4 | WMD worse; it demoted the primary procedure evidence. |
| A05 | 1 | 1 | 1 | 1 | Tie. |
| A06 | — | — | — | — | Both approaches fail before reranking; gold never enters the eligible pool. |
| F01 | 2 | 1 | 1 | 12 | WMD substantially worse; it demoted the canonical tuition-table row outside top 10. |
| S01 | 1 | 1 | 1 | 1 | Tie. |
| C01 | 1 | 1 | 1 | 4 | WMD worse. |

**WMD better:** none in this pilot.  
**WMD worse:** P03, P04 secondary evidence, A01, F01, C01.  
**Both fail:** A06.  
**Gold absent from RRF top-15:** A06 only.

## Latency

Warmed component timing used three passes over the same nine queries on the local RTX 4050 environment. Mean end-to-end RRF time is the measured BM25 + BGE + RRF/final-filter component sum; WMD is the additional reranking work over at most 15 candidates.

| Path | Mean ms/query | p50 ms | p95 ms |
| --- | ---: | ---: | ---: |
| BM25 only | 53.8 | 44.3 | 97.7 |
| BGE dense only | 50.7 | 43.4 | 96.0 |
| BM25 + BGE + RRF/filter | 143.1 | — | — |
| Exact WMD increment | 54.2 | 9.2 | 31.0 |
| RRF + exact WMD | 197.3 | 132.8 | 266.3 |

The WMD mean includes one approximately 1.06 s first-use event when a query introduced uncached terms and the lazy BERT encoder loaded. Its repeat pass for that same query took 8.9 ms. The p50/p95 values better describe the warm reranking work; cold model/first-miss cost must be shown separately in a demo.

## Failure analysis and academic interpretation

1. **This pilot does not support deploying WMD.** It reduced every reported ranking metric relative to RRF and produced no per-query improvement.
2. **Exact WMD cannot repair candidate loss.** A06 fails in scope/eligibility before WMD sees a passage; its top-15 candidate recall is zero.
3. **WMD can harm structured factual retrieval.** It moved the exact CSE overview, primary admission procedure, tuition-table row, and hostel-item passage down the ranking despite their direct factual support.
4. **The experiment is still academically valid.** The implementation uses the pinned BERT model, exact `ot.emd2` optimal transport, fixed provenance-checked corpus, and a controlled RRF top-15 candidate pool. The correct conclusion is negative for this small pilot: exact WMD added latency and did not improve ranking.
5. **Do not generalize these values.** Nine user-approved, source-checked pilot cases are neither independent nor a held-out test set. Finish the unresolved annotation protocol before making a broader effectiveness claim.

## Exact commands

```powershell
uv run python src/build_wmd_cache.py --config configs/wmd_experiment.yaml
uv run python src/evaluate_wmd.py --questions evaluation/wmd_reviewed_verified_pilot.jsonl --config configs/wmd_experiment.yaml --output evaluation/wmd_runs/final_verified_pilot
uv run python -m pytest -q
uv run ruff check .
```

The raw per-query benchmark artifact is intentionally ignored by Git at `evaluation/wmd_runs/final_verified_pilot/raw_results.json`.

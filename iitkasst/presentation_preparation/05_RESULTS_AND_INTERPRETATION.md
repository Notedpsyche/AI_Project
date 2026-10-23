# Experimental results and defensible interpretation

## Evaluation status

These numbers were verified against `evaluation/WMD_FINAL_BENCHMARK_REPORT.md`. They cover **nine user-approved, source-checked pilot queries**. They are development/presentation evidence, not an independent held-out accuracy estimate and not a statistically significant universal comparison.

## Metrics

### Recall@k

\[
Recall@k=\frac{|\text{relevant chunks}\cap\text{top-k chunks}|}{|\text{relevant chunks}|}.
\]

It asks whether the known evidence was retrieved by cutoff `k`. With one canonical gold chunk, it is 1 if that chunk appears and 0 otherwise. Multi-evidence questions can receive fractional recall.

### MRR@10

For query `i`, reciprocal rank is `1/r_i` where `r_i` is the first relevant rank up to 10, otherwise 0:

\[
MRR@10=\frac{1}{Q}\sum_{i=1}^{Q}\frac{1}{r_i}.
\]

Rank 1 gives 1, rank 2 gives 0.5, rank 10 gives 0.1. MRR emphasizes how quickly the first useful evidence appears.

### nDCG@10

\[
DCG@10=\sum_{r=1}^{10}\frac{2^{rel_r}-1}{\log_2(r+1)},\qquad
nDCG@10=\frac{DCG@10}{IDCG@10}.
\]

It supports graded relevance and rewards highly relevant evidence near the top. Dividing by the ideal ordering makes the value range from 0 to 1.

## Verified comparison

| Method | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.8889 | 0.8889 | 0.7500 | 0.8166 |
| BGE-base | 0.8889 | 0.8889 | 0.8333 | 0.8534 |
| BM25+BGE RRF | **0.8889** | **0.8889** | **0.8889** | **0.8835** |
| RRF→BERT+exact WMD | 0.7778 | 0.7778 | 0.5278 | 0.6155 |

RRF had the strongest ranking quality in this pilot. Its recall tied the individual retrievers, but its better MRR and nDCG show that it placed relevant passages earlier and in a better graded order.

## Per-question evidence

| ID | BM25 | BGE | RRF | WMD | Observation |
|---|---:|---:|---:|---:|---|
| P01 | 1 | 1 | 1 | 1 | tie |
| P03 | 1 | 1 | 1 | 4 | WMD demoted CSE overview |
| P04 | 1 | 1 | 1 | 1 | first hit tied; ECE moved 2→4 |
| A01 | 4 | 2 | 1 | 4 | RRF best; WMD demoted procedure |
| A05 | 1 | 1 | 1 | 1 | tie |
| A06 | — | — | — | — | gold absent before WMD |
| F01 | 2 | 1 | 1 | 12 | exact fee evidence heavily demoted |
| S01 | 1 | 1 | 1 | 1 | tie |
| C01 | 1 | 1 | 1 | 4 | WMD worse |

For P04, both CSE and ECE evidence remained in the top ten for all methods; WMD preserved completeness but worsened the ECE rank.

## Candidate recall limitation

The eligible RRF top-15 pool contained canonical gold for 8 of 9 cases: 88.9%. A06 resolved to a general query scope and produced no eligible gold candidate. Since WMD sees only this pool, its maximum possible success for A06 was zero. A reranker can reorder candidates; it cannot retrieve an absent item.

## Latency

| Path | Mean ms/query | p50 ms | p95 ms |
|---|---:|---:|---:|
| BM25 | 53.8 | 44.3 | 97.7 |
| BGE | 50.7 | 43.4 | 96.0 |
| BM25+BGE+RRF/filter | 143.1 | not recorded | not recorded |
| Exact-WMD increment | 54.2 | 9.2 | 31.0 |
| RRF+WMD | 197.3 | 132.8 | 266.3 |

The WMD mean includes one approximately 1.06-second first-use event caused by lazy BERT loading for uncached query terms; the repeat was 8.9 ms. Thus the warm median better describes repeated use, while the cold event matters in a live demo. Memory also includes the BERT model, the 521×768 cache, and optimal-transport working matrices.

## Why RRF likely worked well

The following are **reasonable interpretations**, not isolated causal proofs:

1. College questions contain exact entities—years, programme names, routes, fee labels—where BM25 is strong.
2. Paraphrases still benefit from BGE’s full-sequence, retrieval-trained embedding.
3. RRF rewards agreement without trying to calibrate incompatible score scales.
4. Metadata eligibility protects programme/year/route boundaries after retrieval.

## Why WMD likely performed worse

Evidence-backed observations:

- all metrics declined;
- no evaluated query improved;
- several exact passages moved downward;
- F01 moved from RRF rank 1 to WMD rank 12;
- A06 was unavailable to WMD;
- WMD added latency.

Plausible explanations:

- words are encoded independently, so sentence context is lost;
- WMD uses a bag-of-terms distribution, losing syntax and table relationships;
- semantic proximity between `fee`, `deposit`, and `tuition` may not preserve the exact requested component;
- normalized isolated-word geometry is not specifically trained for passage ranking;
- title/heading/passage truncation can omit decisive text;
- transport similarity does not itself enforce year, programme, or answer sufficiency.

## Does this contradict the paper?

No. A paper result is conditional on its corpus, labels, representation, system design, and evaluation. This project uses a small college corpus, bounded RRF candidates, isolated-word `[CLS]` vectors, and nine source-checked pilot cases. The correct statement is:

> We implemented a paper-inspired exact-WMD reranker. On this pilot and configuration, it did not improve the existing hybrid ranker, so it was not deployed.

Do not say “WMD is worse than BGE” without the qualifiers “in this pilot” and “under this implementation.”

## Threats to validity

- Only nine scored cases.
- User-approved/source-checked labels, not an untouched independent test set.
- Eight proposed cases excluded for unresolved protocols.
- One candidate-generation failure affects every method.
- No confidence interval, randomization test, or statistical significance test.
- Corpus is only 98 chunks and covers a narrow applicant scope.
- Results are tied to exact preprocessing, token limits, BERT layer selection, and candidate depth.

## Defensible conclusion

The pilot supports a local engineering decision: keep BM25+BGE+RRF as production retrieval and keep BERT+WMD isolated as an academic experiment. It does not establish a universal model ranking. The negative result is still valuable because it demonstrates controlled implementation, measurement, and evidence-based model selection.


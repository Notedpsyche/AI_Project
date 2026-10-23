# Presentation MVP Plan

## Definition of done

The presentation MVP is successful when the existing web application still runs unchanged, the four focused correctness regressions pass, and a separate command demonstrates real exact WMD over 15 eligible RRF candidates with inspectable distances, source metadata, and timing. WMD does not need to outperform BGE to be academically valid.

## Realistic scope

### Required before presentation

1. Record baseline Git/hash/test/demo state.
2. Implement and test the four bounded correctness fixes.
3. Add POT and direct Transformers declarations after a Windows preflight.
4. Implement preprocessing, BERT word encoder, exact WMD, strict cache, and top-15 reranker.
5. Build the current-corpus cache once.
6. Run unit tests and a five-query smoke comparison.
7. Prepare one reproducible CLI demo and one tiny mathematical transport example.

### Explicitly postponed

Corpus expansion, hierarchical parsing, structured fee arithmetic, complete FSM, full independent evaluation, cross-encoder work, production WMD/API integration, and all RAG work.

## Setup commands

Run from `iitkasst/` in PowerShell:

```powershell
uv run python -m pytest -q
uv run ruff check .
uv add "transformers>=5.19,<6" "POT==0.9.7"
uv run python -c "import ot, transformers; print(ot.__version__, transformers.__version__)"
uv run python -m pytest -q tests/test_wmd_distance.py
```

The dependency step updates `pyproject.toml` and `uv.lock`. If POT cannot install/import on Windows, stop WMD implementation; do not substitute another metric.

## Cache and demo commands

```powershell
uv run python src/build_wmd_cache.py --config configs/wmd_experiment.yaml
uv run python src/run_wmd_experiment.py --query "What B.Tech programmes are available?" --top 5
uv run python src/run_wmd_experiment.py --query "What is the first-semester tuition fee for B.Tech in 2026?" --top 5 --json evaluation/wmd_runs/fee_demo.json
uv run python src/run_wmd_experiment.py --query "What are the eligibility requirements for PhD admission?" --top 5
```

After the model is cached, verify offline reproducibility:

```powershell
$env:HF_HUB_OFFLINE = "1"
uv run python src/run_wmd_experiment.py --query "Compare CSE and ECE programmes." --top 5
Remove-Item Env:HF_HUB_OFFLINE
```

Expected output fields:

```text
query, effective_query, scope
baseline.bm25[] / baseline.bge[] / baseline.rrf[]
wmd_reranked[]: rank, chunk_id, title, heading, source_url,
                original_rrf_rank, wmd_distance, elapsed_ms
timing: baseline_ms, query_encoding_ms, wmd_ms, total_ms
model/cache/corpus identifiers
```

Do not promise a particular ranking or latency before measurement.

## Five-query smoke set

1. Exact keyword: available B.Tech programmes.
2. Semantic paraphrase: “Which undergraduate computing degrees can applicants choose?”
3. Fee scope: first-semester B.Tech tuition for 2026.
4. Known selection failure: PhD eligibility.
5. Missing/unsupported: a question with no official evidence.

The smoke set checks execution and trace clarity, not accuracy. Gold chunks must be reviewed from the current official corpus before any metric is stated.

## Mathematical demonstration

Use a solver-only deterministic example independent of BERT:

- query masses `a=[0.5,0.5]`;
- document masses `b=[0.5,0.5]`;
- ground matrix `[[0,1],[1,0]]`;
- exact transport keeps both half-masses on zero-cost diagonal, so `ot.emd2(...) = 0`.

Then change the second document vector so its transport cost is positive and show that the total distance increases. Explain that real ground costs come from Euclidean distances between normalized BERT word vectors and lower WMD ranks closer passages.

## Test commands

```powershell
uv run python -m pytest -q tests/test_college_reliability_regressions.py
uv run python -m pytest -q tests/test_wmd_preprocessing.py tests/test_wmd_distance.py tests/test_wmd_cache.py tests/test_wmd_ranker.py
uv run python -m pytest -q
uv run ruff check .
uv run python -m pytest -q -m model tests/test_wmd_encoder_integration.py tests/test_wmd_experiment_integration.py
```

The model-marked suite runs only after the pinned BERT artifact is available.

## Estimated focused effort

| Work | Estimate | Risk |
|---|---:|---|
| Baseline freeze and regression fixtures | 1–1.5 hours | Low |
| Four correctness fixes | 3–5 hours | Medium due existing 45-case compatibility |
| WMD dependency/preprocessing/solver/cache/ranker | 5–8 hours | Medium-high |
| CLI, smoke benchmark, presentation notes | 2–3 hours | Medium |

Total is approximately 11–17 focused engineering hours. Under a next-day deadline, the safe cutoff is to keep reliability fixes already passing and demonstrate solver + cache + CLI on a smaller reviewed query set. UI integration is not attempted.

## Go/no-go and fallback

Go if: existing 58 tests plus new regressions pass; cache manifest validates; exact mathematical tests pass; top-15 CLI completes repeatedly; source metadata survives; baseline API smoke remains unchanged.

No-go for live WMD if: POT/model/cache fails, output is nonfinite/unstable, warmed reranking is too slow for a smooth live run, GPU pressure affects the backend, or WMD code causes any baseline regression. Fallback: demonstrate the unchanged web app, show the exact solver unit example, and run/describe WMD from recorded reproducible CLI JSON. Never relabel centroid cosine as WMD.


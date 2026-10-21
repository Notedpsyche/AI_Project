# IIIT Kottayam Applicant Assistant

A local, source-grounded applicant assistant for public IIIT Kottayam admissions, B.Tech programmes, fees, and scholarships. It reuses the project's BM25 + BGE-base + FAISS + reciprocal-rank-fusion retrieval engine. Answers are short extracts from displayed official evidence, not generated claims. Missing, wrong-year, or unsupported evidence should result in abstention.

This is an **independent academic prototype, not an official institute service**. Verify consequential dates, requirements, and payments on the linked official source. The local corpus is curated and incomplete.

## Clean setup (Windows PowerShell)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Node.js. From the `indlaw-ir` directory:

```powershell
uv sync
uv run python src/prepare_college.py all
uv run python src/index.py
uv run uvicorn backend.main:app --reload
```

In a second terminal:

```powershell
cd app\frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The API is at `http://localhost:8000/api`. First use downloads the pretrained BGE model. Index building uses CUDA when available, otherwise CPU. If indexes are absent, backend startup reports the exact preparation commands instead of silently using Doc2Dial data.

Only 10 explicitly listed official URLs in `configs/college_sources.json` are collected, with a 0.5-second delay between requests. The site currently exposes no populated sitemap for these pages, so the collector does not crawl arbitrary links. Inspect and update the allowlist and institute access rules before expanding coverage. Source content, prepared chunks, indexes, trained models, judgments, and results are ignored by Git; **do not commit downloaded pages/PDFs** without permission. The collector records URL, document type, programme, admission year, fetch time, content hash, and derived section/table-row IDs.

## API

- `GET /api/health`: model and device status.
- `POST /api/search` with `{"query":"..."}`: retrieval-only evidence view.
- `POST /api/chat` with `{"message":"...","conversation":[{"role":"user","content":"..."}]}`: extractive answer and ranked sources.

Evidence includes `source_url`, `programme`, `admission_year`, `retrieved_at`, `document_type`, and retrieval diagnostics. The client holds the conversation and sends bounded recent turns to the backend. New programme/year scopes do not inherit the preceding query. No uncalibrated absolute cosine threshold is used to decide whether to answer.

## Evaluation and required training experiment

`evaluation/question_bank.jsonl` contains **20 unjudged pilot prompts**, not ground truth. Follow `evaluation/annotation_guide.md` to create ignored local `evaluation/judgments.jsonl` after checking the official sources and passage IDs. The intended final set is approximately 60 train / 20 development / 20 untouched test questions. Do not claim the 16/20 answer-quality target until those answers are independently reviewed.

```powershell
uv run python src/annotation_candidates.py
uv run python src/evaluate_college.py
uv run python src/train_reranker.py
```

Evaluation reports equal-cutoff BM25, dense, and hybrid Recall@5, MRR@10, nDCG@10, per-query rankings, and warmed retrieval latency. Training learns a small logistic relevance reranker from **human-labeled** positive passages and hard negatives. It saves a candidate artifact with `deploy: false`. Deploy only after held-out ranking and answer-safety review; otherwise the application continues to use RRF. Without a reviewed judgment file, evaluation/training intentionally stop with an explanatory error.

## Validation

```powershell
uv run pytest -q
uv run ruff check .
cd app\frontend
npm run build
```

The old Doc2Dial-specific modules and tests remain in the repository as historical material. Earlier Doc2Dial metrics are **not** evidence that this college assistant meets its targets; the old 200-turn evaluation sampled DMV only and has other comparison limitations.

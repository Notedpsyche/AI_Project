# Doc2Dial AI — Hybrid Retrieval Demonstrator

Local, closed-domain, context-aware conversational retrieval over Doc2Dial v1.0.1. The application combines BM25 lexical search with BAAI/bge-base-en-v1.5 semantic retrieval, fuses candidates with Reciprocal Rank Fusion, and answers only from displayed evidence.

Source dataset: `C:\Users\Saivarad KG\Downloads\archive`

The original Streamlit prototype remains available for debugging, but the documented application is React + FastAPI. No external API, cloud LLM, fine-tuning, or black-box reranker is used.

The semantic refusal threshold remains `0.67`, chosen by the existing validation work. The indexed corpus contains 14,738 chunks and the BGE-base index has 768-dimensional normalized vectors.

## Run locally

From `indlaw-ir`:

```powershell
uv sync
uv run uvicorn backend.main:app --reload
```

In another terminal:

```powershell
cd app\frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The backend health check is available at `http://localhost:8000/api/health`; retrieval-only debugging is available through `POST /api/search` and chat through `POST /api/chat`.

## Architecture

React → FastAPI → bounded context query → BM25 + BGE-base → RRF → distinct evidence selection → confidence/refusal → deterministic grounded answer → sources and scores.

The post-RRF selector uses configurable semantic, BM25, RRF, source/domain, intent, quality, and redundancy signals. It applies diversity-aware greedy selection with a default of three evidence items and logs both the RRF candidate preview and final selection.

## Demo queries

- `How do I change my address with Social Security?`
- Follow up with `Can I do it online?` to show context-aware retrieval.
- `What should I do if I need to report a complaint?`
- `What is the capital of France?` to demonstrate closed-domain refusal.

## Validation

```powershell
uv run pytest -q
uv run ruff check .
cd app\frontend
npm run build
```

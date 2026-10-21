# Doc2Dial AI — Project Documentation

## 1. Project overview

Doc2Dial AI is a local, closed-domain conversational information-retrieval system for government-service questions. It answers only from the indexed Doc2Dial corpus.

The system combines BM25 lexical retrieval, BAAI `bge-base-en-v1.5` semantic retrieval, Reciprocal Rank Fusion (RRF), conversation context detection, task-aware evidence selection, confidence checking, closed-domain refusal, and deterministic grounded answer generation.

The documented application is a React frontend connected to a FastAPI backend. A Streamlit prototype remains available for debugging.

## 2. Dataset

The active source dataset is Doc2Dial v1.0.1. The runtime expects the extracted files in `data/raw/doc2dial/`:

```text
doc2dial_doc.json
doc2dial_dial_train.json
doc2dial_dial_validation.json
doc2dial_dial_test.json
```

The active implementation does **not** use `C:\Users\Saivarad KG\Downloads\archive`. That folder contains a different Indian legal dataset. The loader reads `data/raw/doc2dial/doc2dial_doc.json` and the Doc2Dial dialogue files.

Dataset loading and structure-aware chunking are implemented in `src/doc2dial_retrieval/data.py`.

## 3. Architecture

```text
React frontend
  → FastAPI /api/chat
  → context detection and follow-up reformulation
  → BM25 + BGE semantic retrieval
  → RRF hybrid merge
  → task-aware evidence selection
  → confidence/refusal check
  → grounded deterministic answer
  → answer, evidence, scores, and debug data
```

Important components:

| Component | Location | Responsibility |
|---|---|---|
| FastAPI startup | `backend/main.py` | Starts the backend and loads retrieval |
| API routes | `backend/api/routes.py` | `/api/health`, `/api/search`, `/api/chat` |
| Context detection | `backend/services/context_service.py` | Standalone versus follow-up decision |
| Retrieval orchestration | `backend/services/retrieval_service.py` | Connects context, search, and selection |
| Dataset loader | `src/doc2dial_retrieval/data.py` | Reads and normalizes Doc2Dial |
| Search engine | `src/doc2dial_retrieval/search.py` | Loads indexes and executes search |
| Retrieval algorithms | `src/doc2dial_retrieval/retrieval.py` | BM25, dense retrieval, and RRF |
| Intent representation | `backend/services/intent_service.py` | Task groups and specific task profiles |
| Evidence selector | `backend/services/evidence_selector.py` | Scores, filters, and diversifies evidence |
| Answer generation | `backend/services/answer_service.py` | Produces grounded answers |
| React frontend | `app/frontend/` | Desktop-oriented user interface |

## 4. Work completed

### 4.1 Conversational follow-up fix

Previously, the system classified:

```text
How do I replace my Social Security card? → card
How long does it take?                  → status
```

The disjoint groups caused the second question to be treated as standalone.

`backend/services/context_service.py` now recognizes generic underspecified follow-ups involving duration, quantity, cost, location, online/offline questions, document requirements without a complete task, and references such as `it`, `that`, `there`, and `what about`.

It does not hardcode individual questions. Complete new tasks such as `How do I register a vehicle?` remain standalone.

For a valid follow-up, the effective query is:

```text
USER: How do I replace my Social Security card?
CURRENT QUESTION: How long does it take?
```

That combined meaning is sent to both BM25 and BGE retrieval.

### 4.2 Task-aware evidence-selection fix

Previously, broad groups allowed unrelated tasks to share generic words such as `documents`, `proof`, and `application`.

`backend/services/intent_service.py` now identifies compact task profiles including:

- Social Security benefits application;
- Social Security card replacement;
- Social Security card-document requirements;
- Social Security address change;
- benefit status;
- vehicle/DMV tasks.

Card profiles remain compatible with one another when appropriate, but card evidence conflicts with a benefits-application query.

The existing selector in `backend/services/evidence_selector.py` still preserves semantic, BM25, RRF, domain, quality, and redundancy signals. The improved task compatibility and contradiction values make wrong-task evidence lose to correct-task evidence.

## 5. GitHub repository and layout

Repository: [Notedpsyche/AI_Project](https://github.com/Notedpsyche/AI_Project)

The project is at the repository root under `iitkasst/`.

```text
iitkasst/
├── app/                 React frontend and Streamlit prototype
├── backend/             FastAPI backend and services
├── configs/             Retrieval configuration
├── docs/                Project and dataset notes
├── src/                 Dataset, indexing, retrieval, and evaluation code
├── tests/               Unit and regression tests
├── pyproject.toml       Python project configuration
├── requirements.txt     Dependency reference
└── uv.lock              Reproducible uv lockfile
```

Generated or machine-specific artifacts such as virtual environments, logs, raw/generated data, and large local indexes are excluded from the source commit.

## 6. Prerequisites

- Python 3.11 or newer;
- `uv` for Python environment and dependency management;
- Node.js and npm for the React frontend;
- CUDA-capable GPU for the current BGE index-generation workflow;
- Doc2Dial v1.0.1 files in `data/raw/doc2dial/`.

The configured semantic model is `BAAI/bge-base-en-v1.5`.

## 7. Setup from GitHub

```powershell
git clone https://github.com/Notedpsyche/AI_Project.git
cd AI_Project\iitkasst
uv sync
```

Install frontend dependencies:

```powershell
cd app\frontend
npm install
cd ..\..
```

Place the extracted Doc2Dial files in `data/raw/doc2dial/`. Do not point the application at `Downloads\archive`.

## 8. Build the local corpus and indexes

The source commit excludes large generated indexes. If indexes are not already available locally, prepare the chunks first:

```powershell
uv run python src\prepare.py
```

This writes `data/processed/chunks.jsonl` and `data/processed/chunk_stats.json`.

Then build BM25 and BGE/FAISS indexes:

```powershell
uv run python src\index.py
```

The current index command requires CUDA for BGE embedding generation. It creates `indexes/bm25/` and `indexes/faiss_bge_base/`.

The retrieval paths and settings are configured in `configs/config.yaml`.

## 9. Run the backend

From `AI_Project\iitkasst`:

```powershell
uv run uvicorn backend.main:app --reload
```

Backend URL: `http://localhost:8000`

Health endpoint: `http://localhost:8000/api/health`

Available API endpoints:

```text
GET  /api/health
POST /api/search
POST /api/chat
```

## 10. Run the frontend

Open a second terminal:

```powershell
cd AI_Project\iitkasst\app\frontend
npm run dev
```

Open `http://localhost:5173` in a browser.

## 11. Example behavior

### Follow-up context

```text
User: How do I replace my Social Security card?
User: How long does it take?
```

The second query inherits the card-replacement task and is not sent to retrieval as the isolated phrase `How long does it take?`.

### Address follow-up

```text
User: How do I change my address with Social Security?
User: Can I do it online?
```

The second query inherits the address-change task.

### New-topic isolation

```text
User: How do I replace my Social Security card?
User: How do I register a vehicle?
```

The vehicle question remains standalone and does not inherit Social Security context.

### Closed-domain refusal

```text
What is the capital of France?
```

The answer layer refuses when confidence is below the configured threshold or suitable evidence is unavailable.

## 12. Validation

Focused regression tests are in `tests/test_requested_regressions.py`. They cover card-duration follow-up, address-online follow-up, benefits-application evidence versus card evidence, and new-topic isolation.

Command:

```powershell
uv run pytest tests/test_requested_regressions.py -q
```

Result:

```text
4 passed
```

No full benchmark was run for the focused implementation task. BM25, BGE, RRF, the corpus, and embeddings were not replaced.

## 13. Current configuration

```text
Dense model:        BAAI/bge-base-en-v1.5
BM25 candidates:    50
BGE candidates:     50
RRF k:              60
Evidence top-k:     3
Refusal threshold:  0.67
```

The answer generator is deterministic and grounded in selected evidence. It does not call an external language model or cloud API.

## 14. Summary

The completed system provides Doc2Dial v1.0.1 closed-domain retrieval with BM25, BGE semantic search, RRF fusion, generic conversational follow-up handling, task-aware evidence compatibility, grounded answers, refusal behavior, a React/FastAPI application, and focused regression coverage.

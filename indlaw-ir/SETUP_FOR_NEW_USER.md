# Set up the IIIT Kottayam Applicant Assistant

This guide starts a fresh local copy of the IIIT Kottayam Applicant Assistant. The application is a local React + FastAPI system that retrieves from a curated set of official IIIT Kottayam pages and PDFs. It does not require an OpenAI, Gemini, or other LLM API key.

## 1. Requirements

Install these before starting:

- Git
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 20 or newer with npm

Optional: an NVIDIA GPU can make BGE embedding/index creation faster. CPU works too, but the first index build will take longer.

## 2. Clone the repository

```powershell
git clone https://github.com/Notedpsyche/AI_Project.git
cd AI_Project\indlaw-ir
```

All commands below must be run from the `indlaw-ir` directory unless another directory is explicitly shown.

## 3. Install Python dependencies

```powershell
uv sync
```

This creates a local `.venv` and installs FastAPI, BM25, FAISS, PyTorch, Sentence Transformers, and development tools.

## 4. Collect the local corpus and build indexes

```powershell
uv run python src/prepare_college.py all
uv run python src/index.py
```

The first command downloads only the allowlisted official IIIT Kottayam sources in `configs/college_sources.json`, extracts versioned sections/table rows, and saves them locally. The second command builds BM25 and FAISS indexes using `BAAI/bge-base-en-v1.5`.

The downloaded pages/PDFs, processed chunks, embeddings, and indexes are intentionally ignored by Git. A new user must run these commands after cloning. Do not commit the collected source content unless redistribution permission is confirmed.

If a source URL changes or you edit the source allowlist, repeat both commands.

## 5. Start the backend

Open a PowerShell terminal in `indlaw-ir`:

```powershell
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Wait for `Application startup complete`. Check it in a browser or PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected result: a JSON object with `status: "ok"`.

## 6. Start the frontend

Open a second PowerShell terminal:

```powershell
cd AI_Project\indlaw-ir\app\frontend
npm ci
npm run dev
```

Open the URL printed by Vite, normally `http://127.0.0.1:5173`.

## 7. Try the assistant

Example questions:

- `How do I apply for B.Tech in 2026?`
- `What are the available courses?`
- `What is the mess advance in semester three?`
- `What minimum laptop setup must a new student have when reporting?`

The assistant is extractive: it should cite official evidence rather than inventing an answer. It should abstain when the curated local sources do not establish the requested fact.

## 8. Run checks

From `indlaw-ir`:

```powershell
uv run pytest -q
uv run ruff check .
uv run python src/smoke_college.py
```

To check the frontend production build:

```powershell
cd app\frontend
npm run build
```

`src/smoke_college.py` needs the backend running at `http://127.0.0.1:8000`.

## Troubleshooting

### Backend says indexes are missing

Run these commands from `indlaw-ir`:

```powershell
uv run python src/prepare_college.py all
uv run python src/index.py
```

### Port 8000 or 5173 is already in use

Stop the terminal process using that port, or choose another port. If you change the backend port, update the frontend API configuration accordingly.

### The first startup is slow

The BGE model may download on first use. Later runs use the local model cache and local indexes.

### Answers are missing a fact

Use the source link shown with the answer. The current corpus is intentionally limited to the official pages/PDFs in the allowlist; it is not a full copy of the institute website.

## Project layout

| Location | Purpose |
| --- | --- |
| `backend/` | FastAPI routes and answer/retrieval services |
| `app/frontend/` | React/Vite chat interface |
| `configs/college_sources.json` | Curated official-source allowlist |
| `src/prepare_college.py` | Fetch and extract local source data |
| `src/index.py` | Build BM25, BGE embeddings, and FAISS indexes |
| `tests/` | Python unit and regression tests |
| `QUALITY_IMPROVEMENT_REPORT.md` | Latest implementation and development-regression report |

For known limits and test results, see `QUALITY_IMPROVEMENT_REPORT.md`.

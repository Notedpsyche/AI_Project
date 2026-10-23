# Live demo, recovery guide, and final cheat sheet

## Before the presentation

From `C:\Users\Saivarad KG\Documents\AI project\iitkasst`, verify once—not during the talk:

```powershell
uv sync
uv run python -m pytest -q
uv run ruff check .
cd app\frontend
npm ci
npm run build
```

Do not rebuild the corpus, main indexes, or WMD cache on presentation day if the current verified artifacts are present.

## Exact demo commands

### Terminal 1 — FastAPI

```powershell
cd "C:\Users\Saivarad KG\Documents\AI project\iitkasst"
uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Wait for application startup, then check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health | ConvertTo-Json
```

### Terminal 2 — React/Vite

```powershell
cd "C:\Users\Saivarad KG\Documents\AI project\iitkasst\app\frontend"
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`.

### Normal API query

```powershell
$demoBody = @{
  message = "What is the first-semester B.Tech tuition fee in 2026?"
  conversation = @()
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/chat `
  -ContentType application/json `
  -Body $demoBody | ConvertTo-Json -Depth 8
```

### BERT+WMD comparison

```powershell
cd "C:\Users\Saivarad KG\Documents\AI project\iitkasst"
uv run python src/run_wmd_experiment.py `
  --query "What is the first-semester B.Tech tuition fee in 2026?" `
  --top 5
```

Explain that this shows baseline rankings and reranks at most 15 eligible RRF candidates. It does not change the website.

### Display the recorded benchmark

```powershell
Get-Content evaluation\WMD_FINAL_BENCHMARK_REPORT.md
```

Or open the website’s **Presentation brief** page for the concise table. If explicitly asked to reproduce the benchmark:

```powershell
uv run python src/evaluate_wmd.py `
  --questions evaluation/wmd_reviewed_verified_pilot.jsonl `
  --config configs/wmd_experiment.yaml `
  --output evaluation/wmd_runs/final_verified_pilot
```

Prefer the recorded report during the talk: rerunning models adds avoidable delay.

## Five source-verified demo questions

These correspond to source-checked benchmark evidence. Rehearse them once after starting the backend.

1. **What B.Tech programmes are available at IIIT Kottayam?**  
   Verify that the source is `UG Admission 2026`, chunk `ug-admission-2026::2aa547656f2faa42`.

2. **How do I apply for B.Tech in 2026?**  
   Verify that the response cites the official admission route/process; canonical benchmark evidence is `ug-admission-2026::6e63924cd2367402`.

3. **How many mandatory steps are in the 2026 admission portal process?**  
   Verify the portal-guide source and chunk `admission-portal-guide-2026::ebc44eab8e3de09f`.

4. **What is the first-semester B.Tech tuition fee in 2026?**  
   Verify the official fee-table row `btech-fees-2026::8cf5ae1257ed36b1`. Do not paraphrase a different fee component as the total fee.

5. **Which authorities provide scholarships that IIIT Kottayam students can apply for?**  
   Verify `scholarships::97cd825f583968a3` and preserve the source’s distinction between institute assistance and external authorities.

Avoid placement statistics, recruiter lists, and other topics absent from the current allowlist. A refusal there is expected, not a retrieval demo failure.

## Suggested five-minute live sequence

1. Show the header badge `BM25 + BGE + RRF` and explain there is no generative LLM.
2. Ask the programme-list question; open its official citation.
3. Ask the tuition question; show that only the requested row/cell is quoted.
4. Open **Explore evidence** to show BM25, semantic, and RRF diagnostics.
5. Open **Presentation brief** and discuss the negative WMD result.
6. If time permits, run the WMD CLI and point to `original_rrf_rank`, `wmd_rank`, and `wmd_distance`.

## Recovery guide

### Backend fails to start

1. Confirm the terminal is at `iitkasst`.
2. Run `uv sync`.
3. Check whether port 8000 is occupied:
   `Get-NetTCPConnection -LocalPort 8000 -State Listen`.
4. Read the exact startup error. Missing-index errors deliberately print the required commands.
5. Use `/api/health` before opening the demo.

### Frontend is inaccessible

1. Keep the backend running.
2. In `app\frontend`, run `npm ci` and `npm run dev -- --host 127.0.0.1`.
3. Open the exact URL Vite prints, normally `http://127.0.0.1:5173/`.
4. If the UI says Offline, verify `http://127.0.0.1:8000/api/health`; the frontend default uses `localhost:8000/api`.

### Main FAISS/BM25 indexes are missing or stale

Only if the local source files/indexes genuinely need rebuilding:

```powershell
uv run python src/prepare_college.py all
uv run python src/index.py
```

This fetches the ten official sources and may depend on network availability. For presentation reliability, preserve and test the existing local artifacts beforehand.

### CUDA is unavailable

The code selects CPU automatically. Startup/indexing will be slower. Do not promise GPU-only behavior. If a cached PyTorch CUDA installation has a host issue, demonstrate with the already built indexes and allow model loading time.

### WMD cache is unavailable

The website still works because WMD is isolated. Skip the live WMD command and show the recorded report. If rebuilding before the presentation:

```powershell
uv run python src/build_wmd_cache.py --config configs/wmd_experiment.yaml
```

The builder refuses to overwrite an existing cache; do not delete artifacts during the talk.

### A demo query fails

1. Do not improvise an unsupported answer.
2. Open **Explore evidence** and explain the separation between retrieval and answer sufficiency.
3. Use one of the five source-verified questions above.
4. If the topic is absent from the corpus, explain that safe abstention is intended.
5. Keep the benchmark report and screenshots available as fallback evidence.

## Final cheat sheet

### Four equations

**BM25**

\[
\sum_{t\in q}IDF(t)\frac{f(t,d)(k_1+1)}{f(t,d)+k_1(1-b+b|d|/avgdl)}
\]

`k1=1.5`, `b=0.75`.

**Cosine similarity**

\[
cos(x,y)=\frac{x\cdot y}{\|x\|\|y\|};\quad \text{for unit vectors }cos=x\cdot y.
\]

**RRF**

\[
RRF(d)=\sum_s\frac{1}{60+rank_s(d)}.
\]

**WMD**

\[
\min_{T\ge0}\sum_{i,j}T_{ij}\|e_i-v_j\|_2,
\quad T\mathbf1=p,\;T^T\mathbf1=q.
\]

### BERT versus BGE

| BERT experiment | Production BGE |
|---|---|
| `google-bert/bert-base-uncased` | `BAAI/bge-base-en-v1.5` |
| generic pretrained encoder | retrieval-trained embedding model |
| isolated surface word → layer-11 `[CLS]` | full query/passage → one vector |
| 768-D word vectors for WMD | 768-D text vectors for FAISS |
| not deployed | production dense branch |
| no fine-tuning | no project fine-tuning |

### Important parameters

- Corpus: 10 allowlisted sources, 98 current chunks.
- BM25: `k1=1.5`, `b=0.75`, top 50.
- BGE prefix: `Represent this sentence for searching relevant passages: `.
- BGE/FAISS: normalized float32, 768-D, `IndexFlatIP`, top 50.
- RRF: `k=60`.
- Evidence: normally at most 3 selected passages.
- WMD: top 15 eligible RRF candidates; query 32 terms; document 12 title + 20 heading + 32 passage terms.
- BERT cache: 521 vocabulary vectors, 98 document measures.

### Files to remember

- Corpus: `configs/college_sources.json`, `src/doc2dial_retrieval/college.py`.
- Indexing: `src/index.py`.
- Retrieval: `src/doc2dial_retrieval/retrieval.py`, `search.py`.
- Context/scope: `backend/services/college_query.py`.
- Evidence: `backend/services/college_select.py`.
- Answers/API: `backend/services/college_answer.py`, `backend/api/routes.py`.
- UI: `app/frontend/src/App.tsx`.
- WMD: `src/doc2dial_retrieval/wmd/`, `src/run_wmd_experiment.py`.
- Results: `evaluation/WMD_FINAL_BENCHMARK_REPORT.md`.

### Benchmark numbers

| Method | MRR@10 | nDCG@10 |
|---|---:|---:|
| BM25 | 0.7500 | 0.8166 |
| BGE | 0.8333 | 0.8534 |
| RRF | **0.8889** | **0.8835** |
| RRF→WMD | 0.5278 | 0.6155 |

RRF Recall@10: 88.89%. WMD Recall@10: 77.78%. Pilot: 9 source-checked, non-independent questions.

### Five limitations

1. Small, incomplete curated corpus.
2. Rule-based context and intent coverage.
3. Task-specific deterministic extraction patterns.
4. Nine-case non-independent WMD pilot.
5. Local prototype without production refresh/security/monitoring.

### Five strongest contributions

1. Reproducible official-source collection with hashes and provenance.
2. Complementary BM25+BGE exact/semantic retrieval with transparent RRF.
3. Programme/year/route/task-aware evidence validation and abstention.
4. Deterministic cited answers with inspectable source cards.
5. Genuine exact BERT+WMD implementation and honest negative evaluation.

## Final 60-second summary

“My project is a closed-domain applicant-information retrieval assistant for IIIT Kottayam. I curate official pages and PDFs, preserve their programme, year, table structure, URL, retrieval time, and hash, and index the same chunks in two ways. BM25 retrieves exact terms such as programme names, years, and fee labels. BGE-base converts full text into normalized 768-dimensional semantic vectors, and FAISS performs exact inner-product search. Reciprocal Rank Fusion combines both rankings without mixing incompatible raw scores. A rule-based context resolver and evidence layer then verify the requested programme, year, route, task, semester, and component. The answer composer copies supported source text and refuses when evidence is missing; it does not use a generative LLM.

Inspired by the reference paper, I also implemented pinned BERT word vectors and exact Word Mover’s Distance using optimal transport over the top 15 RRF candidates. On nine source-checked pilot questions, RRF achieved 0.8889 MRR and 0.8835 nDCG, while WMD achieved 0.5278 and 0.6155. Therefore I kept RRF in production. This does not prove WMD is universally worse; it shows that, for this small structured college corpus and experiment, the hybrid retriever was more reliable.”


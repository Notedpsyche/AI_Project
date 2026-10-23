# Exact code walkthrough

## Successful trace: “What is the first-semester B.Tech tuition fee in 2026?”

The values below distinguish static implementation facts from a previously observed live trace. No vector coordinates are invented.

### 1. React receives the message

**File/function:** `app/frontend/src/App.tsx`, `App()` and nested `submit()`.

The controlled `<input>` stores the text in `input`. Form submission prevents the browser default and calls `submit()`. `query = text.trim()` rejects an empty query and the UI sets `loading=true`.

**Input:** user string. **Output:** a pending user `Message` and HTTP request.

### 2. React constructs the request

For the chat page, the client maps all displayed messages to `{role, content}` and sends:

```json
{
  "message": "What is the first-semester B.Tech tuition fee in 2026?",
  "conversation": []
}
```

to `POST http://localhost:8000/api/chat` unless `VITE_API_URL` overrides the base URL. Evidence display fields include title, section, URL, programme, year, retrieval date, type, and diagnostic scores.

### 3. FastAPI handles it

**Files/functions:**

- `backend/main.py::lifespan()` constructs one `RetrievalService(ROOT)` at startup.
- `backend/api/schemas.py::ChatRequest` validates message length 1–4000 and conversation messages.
- `backend/api/routes.py::chat()` obtains the initialized service or returns HTTP 503.

`chat()` starts a timer and calls `service.search(message, conversation)`.

### 4. Scope and context resolution

**File/function:** `backend/services/college_query.py::resolve_scope()`.

The resolver uses regular expressions and normalized terms:

- `programmes_in()` recognizes generic B.Tech or specializations;
- `topic_in()` detects `fees`;
- admission-year extraction separates admission years from qualification years;
- `semester_numbers()` identifies first semester;
- `fee_components_in()` identifies `tuition fee`;
- `intent_in()` returns `fee_component`.

Expected scope fields are programme `B.Tech`, year `2026`, topic `fees`, intent `fee_component`, semesters `(1,)`, fee components `("tuition fee",)`, and no context inheritance for this standalone question.

Context is bounded and rule-based. `resolve_scope()` searches the last six conversation items for the latest **user** message. It inherits missing slots only for a short/reference-like continuation and blocks inheritance when the user explicitly changes programme or admission year. This is not an LLM, neural context classifier, or explicit hierarchical FSM.

### 5. Retrieval service builds the query

**File/function:** `backend/services/retrieval_service.py::RetrievalService.search()`.

If context is used, it forwards only the previous user message to `SearchEngine`; otherwise history is empty. `SearchEngine.build_query()` normalizes contractions such as `what’s→what is`. With history it constructs:

```text
USER: <previous user question>
CURRENT QUESTION: <current question>
```

For this standalone query, the retrieval text stays the question itself.

### 6. BM25 retrieves lexical candidates

**Files/functions:** `src/doc2dial_retrieval/search.py::_retrieve()` and `src/doc2dial_retrieval/retrieval.py::BM25Store.search()`.

`tokenize()` lowercases and extracts `\w+`. The persisted `BM25Okapi` scores the query against heading path plus passage text with `k1=1.5`, `b=0.75`. Configuration requests the top 50. Each result records `bm25_score` and `bm25_rank`, then metadata-sensitive near-duplicates are removed.

### 7. BGE embeds and FAISS searches

**File/functions:** `DenseStore.encode_query()`, `DenseStore.search_vector()`.

The exact encoded query starts with:

```text
Represent this sentence for searching relevant passages:
```

`SentenceTransformer` produces one normalized float32 `(1,768)` vector. `faiss.IndexFlatIP.search(...,50)` returns exact inner-product neighbours. Because vectors are unit normalized, inner product equals cosine similarity. Integer positions map to the aligned dense metadata list.

### 8. RRF combines lists

**File/function:** `src/doc2dial_retrieval/retrieval.py::hybrid()`.

For each chunk:

```text
rrf_score += 1 / (60 + bm25_rank), if present
rrf_score += 1 / (60 + semantic_rank), if present
```

The 50 BM25 and 50 dense candidates are merged by `chunk_id`, sorted, and deduplicated without collapsing different programme/year/route/topic scopes.

### 9. Metadata eligibility filters candidates

**File/function:** `backend/services/college_query.py::eligible()`.

It rejects underspecified questions, unresolved required routes, route conflicts, topic conflicts, wrong programme for comparisons, requested-year mismatches, and chunks marked with conflicting years. A 2026 fee question therefore cannot be supported by a different-year fee chunk.

### 10. Evidence selection checks task support

**File/functions:** `backend/services/college_select.py::supports_request()`, `evidence_set_sufficient()`, `select_evidence()`.

For `fee_component`:

- the row must contain the requested component (`tuition fee`);
- it must contain the requested semester label;
- component filtering prefers a semicolon-structured table row whose row label itself is the requested component;
- small transparent bonuses reward current focus terms, heading overlap, component support, and semester support;
- at most three distinct passages are selected.

This protects against a source being official but irrelevant. For example, a `Caution Deposit; Second Semester: -` row cannot answer a tuition-fee request.

### 11. Deterministic answer composition

**File/functions:** `backend/services/college_answer.py::_fee_claims()` and `grounded_answer()`.

For a structured fee task, `_fee_claims()` copies the row label and only the requested semester cell. It does not generate a value. `grounded_answer()` checks evidence exists and rejects mixed years. A representative result is:

```text
For B.Tech (admission 2026):
• Tuition Fee [1]
• First Semester: 1,59,800/- [1]
```

The bullets are extracts from evidence; `[1]` is the selected evidence rank.

### 12. Citation metadata is attached

**File/function:** `backend/api/routes.py::chat()`.

The route extracts citation numbers using `re.findall(r"\[(\d+)\]", answer)`. Only selected rows whose rank is cited are converted to `Evidence` response objects. Refusals return no evidence. This prevents uncited candidate passages from appearing as answer support.

The canonical fee chunk recorded in the benchmark is:

- `btech-fees-2026::8cf5ae1257ed36b1`
- source: `https://www.iiitkottayam.ac.in/views/fees.html`
- title: `B.Tech fee structure 2026`
- programme: `B.Tech`; admission year: `2026`.

A live check after the semester-fee correction observed the same chunk for the second-semester form of the question. It had semantic rank 10, semantic score about `0.642817`, RRF `0.0142857`, and final evidence score `0.2242857`; BM25 was absent from that serialized fused row. These are observed trace values, not guaranteed constants.

### 13. React renders answer and source

`submit()` appends the assistant response. `EvidenceCard` shows the title, section/programme, text excerpt, official-source link, retrieval date, and expandable diagnostics. The header labels context use and refusals. React does not create or alter the factual answer.

## Failure trace: “What are the placement statistics?”

### Where it begins

`topic_in()` correctly resolves `placements`; `intent_in()` resolves `placement_statistics`. Retrieval may find loosely related chunks, but the curated manifest has no placement-statistics source. The current ten-source allowlist covers admissions, fees, scholarships, programme pages, and the portal guide.

### Where it is stopped

`eligible()` requires the `placements` topic for placement intents. `supports_request()` additionally requires statistical language such as percentage, package, salary, placed students, or secured jobs. No current chunk satisfies that contract, so `select_evidence()` returns an empty list.

`grounded_answer()` therefore returns:

```text
I couldn't verify that from the available official IIIT Kottayam applicant sources.
Please check the linked admission information or contact the institute.
```

### Diagnosis

This failure begins at **corpus coverage**, not BM25, BGE, FAISS, or answer generation. The refusal is correct behavior for the current corpus. Supporting placement questions requires curating and verifying official placement sources, rebuilding indexes, and adding judgments; it should not be solved by weakening evidence checks.

## Stage-to-code reference

| Stage | File | Main symbol | Input → output |
|---|---|---|---|
| UI | `app/frontend/src/App.tsx` | `submit()` | text/history → JSON request |
| API | `backend/api/routes.py` | `chat()` | `ChatRequest` → `ChatResponse` |
| Scope | `backend/services/college_query.py` | `resolve_scope()` | question/history → `QueryScope` |
| Retrieval orchestration | `backend/services/retrieval_service.py` | `search()` | scope/query → candidates |
| BM25 | `retrieval.py` | `BM25Store.search()` | tokens → lexical ranks |
| BGE/FAISS | `retrieval.py` | `DenseStore.search()` | query → vector ranks |
| Fusion | `retrieval.py` | `hybrid()` | two rankings → RRF ranking |
| Metadata | `college_query.py` | `eligible()` | chunk + scope → boolean |
| Support | `college_select.py` | `supports_request()` | chunk + task → boolean |
| Selection | `college_select.py` | `select_evidence()` | candidates → ≤3 passages |
| Answer | `college_answer.py` | `grounded_answer()` | scope/evidence → cited text/refusal |
| Rendering | `App.tsx` | `EvidenceCard` | evidence JSON → visible citation |


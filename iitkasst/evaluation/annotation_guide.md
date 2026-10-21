# College applicant evaluation protocol

The question bank is **unlabeled**. Do not treat a retrieved result, generated question, or model score as ground truth. A reviewer must inspect the official source and create the ignored local file `evaluation/judgments.jsonl`.

Each JSONL row must contain `query_id`, `query`, `split` (`train`, `dev`, or `test`), `gold_chunk_ids` (zero or more IDs from the current local chunk file), `answerable` (boolean), and `answer_fact` (short independently verified fact, or empty for unanswerable). `gold_chunk_ids` must be empty when `answerable` is false. Add `question_family` to group paraphrases and keep the entire family in one split. Record reviewer name/date separately if available.

Also record `expected_behavior`: `answer`, `clarify`, or `abstain`. An `answer` row has `answerable: true`, one or more gold chunks, and an independently verified `answer_fact`. A `clarify` row has `answerable: false`, no gold chunks, and a `clarification_needed` field naming the missing route/programme/year. An `abstain` row has `answerable: false` and no gold chunks. This distinguishes q004/q020 (route clarification) from genuinely unsupported requests. The retrieval ranking metrics apply only to `answer` rows; clarification and abstention require separate manually reviewed behavior checks.

Use `uv run python src/annotation_candidates.py` to produce an **ignored** candidate sheet. Judge source passages from the official site, not from the model ranking alone. Inspect off-top-k sources when necessary. Mark obsolete, cross-year, and unrelated programme passages nonrelevant. Do not label a query answerable merely because a semantically similar passage exists.

Before final reporting, freeze the split and current corpus manifest hash. Target roughly 60/20/20 train/dev/test questions, with an untouched test set. The scripts permit a smaller pilot but label it a pilot; a passing test is not a performance claim.

The agent-authored `PILOT_REVIEW.md` is a review aid, not human gold. The functional command `uv run python src/smoke_college.py` checks 20 expected API behaviors against a running backend; it is not a relevance or answer-quality benchmark. Independently verify each fact and current chunk ID before creating `judgments.jsonl`.

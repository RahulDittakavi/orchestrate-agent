# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (run from repo root)
pip install -r code/requirements.txt

# One-time setup: scrape support sites, then build vector DB
python code/scraper.py
python code/corpus_builder.py

# Run the agent on the input CSV (produces output.csv and log.txt)
python code/agent.py

# Interactive single-ticket testing
python code/agent.py --interactive
```

Environment: copy `code/.env.example` → `code/.env` and set `GEMINI_API_KEY`.

## Architecture

The pipeline processes support tickets in six steps (`pipeline.py: TriagePipeline.process`):

1. **Input cleaning** — strips whitespace, rejects tickets under 5 chars.
2. **Company inference** — if company field is missing/ambiguous, calls Gemini with `DOMAIN_CLASSIFIER_PROMPT` to resolve it to `HackerRank`, `Claude`, `Visa`, or `Unknown`.
3. **Risk assessment** (`risk.py: assess_risk`) — rule-based keyword scan runs *before* the LLM. Any fraud, account-security, billing-dispute, legal, or Visa payment keyword triggers an immediate escalation without hitting the LLM.
4. **RAG retrieval** (`retriever.py: Retriever`) — queries a single ChromaDB collection named `support_corpus` (persisted at `data/chroma_db/`). Filters by `{"source": "hackerrank"|"claude"|"visa"}` when company is known; falls back to unfiltered if the filtered query fails. Uses `all-MiniLM-L6-v2` sentence-transformers embeddings (local, no API cost).
5. **LLM triage** — calls Gemini 1.5 Pro (`gemini-1.5-pro`) with `TRIAGE_PROMPT` (from `prompts.py`), which injects the retrieved docs and demands a JSON-only response. Temperature is set to 0.1 for consistency.
6. **Validation & output** — parses JSON from the LLM response (strips markdown fences, regex-extracts `{...}` on failure). Falls back to escalation if parsing fails.

### Data flow

```
scraper.py  →  data/corpus/{hackerrank,claude,visa}/doc_*.txt
corpus_builder.py  →  data/chroma_db/  (ChromaDB collection: "support_corpus")
agent.py  reads  data/support_issues/support_issues.csv
         writes  output.csv  (repo root) + log.txt  (repo root)
```

Sample/reference tickets live in `data/sample_tickets/` and are not read by `agent.py` directly.

### Allowed output values (Orchestrate constraints)

These are the only valid values — never use anything else:

| Field | Allowed values |
|---|---|
| `status` | `"replied"` · `"escalated"` |
| `request_type` | `"product_issue"` · `"feature_request"` · `"bug"` · `"invalid"` |

### Key file responsibilities

| File | Role |
|---|---|
| `agent.py` | Entry point; CSV batch mode + interactive mode; writes `output.csv` |
| `pipeline.py` | Core orchestration; owns Gemini client and `TriagePipeline` class |
| `retriever.py` | ChromaDB queries; `format_docs_for_prompt` converts results to prompt text |
| `risk.py` | Keyword-based pre-LLM escalation gate |
| `prompts.py` | All LLM prompts; edit here to tune behaviour without touching logic |
| `logger.py` | Writes `log.txt` transcript |
| `scraper.py` | One-time BFS crawl of three support sites (max 100 pages each) |
| `corpus_builder.py` | Chunks `.txt` files (500-word chunks, 50-word overlap) and upserts to ChromaDB |

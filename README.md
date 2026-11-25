# Enterprise Incident Response AI Copilot

An on-call engineer opens an incident, describes symptoms ("RDS CPU at 98%, API p99 4s"),
and gets ranked troubleshooting steps with citations to the runbook, SOP or postmortem they
came from. A LangGraph **Self-RAG** graph grades its own retrieval, rewrites weak queries,
falls back to **Tavily** web search when internal docs don't cover it, checks its answer for
hallucinations and usefulness, and remembers each incident's conversation in **SQLite**.
Every request is audit-logged.

**Stack:** LangGraph · local LLMs via **Ollama** (`qwen2.5:7b`, `nomic-embed-text`) or OpenAI · Pinecone
serverless · Tavily · FastAPI · plain HTML/CSS/JS · SQLite · Docker

---

## How it works

```
                ┌──────────────┐
  question ───► │ contextualize│  follow-up → standalone question (uses chat memory)
                └──────┬───────┘
                       ▼
                ┌──────────────┐
          ┌───► │   retrieve   │  Pinecone top-k
          │     └──────┬───────┘
          │            ▼
          │     ┌──────────────┐
          │     │grade_documents│ drop irrelevant chunks (gpt-4o-mini, yes/no)
          │     └──────┬───────┘
          │            ▼  decide_to_generate
          │   ┌────────┼──────────────┬───────────┐
          │   ▼        ▼              ▼           ▼
   ┌──────────────┐ generate ◄── web_search    give_up
   │transform_query│   │  ▲     (rewrites used up)  │
   └──────────────┘   │  │ not grounded → retry     │
          ▲           ▼  │                          │
          │     grade_generation ─── useful ──► finalize ──► END
          └──── not useful
```

Loop caps (`MAX_REWRITES=2`, `MAX_GENERATIONS=3`) guarantee the graph always ends. When a cap
is hit it returns "insufficient evidence, escalate" instead of guessing.

## Project layout

```
app/
  main.py              FastAPI app: routers + static UI
  config.py            settings from .env (keys, models, loop limits)
  api/                 health, incidents, chat, ingest, audit endpoints
  graph/
    state.py           GraphState TypedDict
    prompts.py         every prompt in one place
    nodes/             contextualize, retrieve, grade_documents, transform_query,
                       web_search, generate (+ finalize, give_up), graders
    edges.py           decide_to_generate, grade_generation routers
    builder.py         StateGraph wiring + SqliteSaver checkpointer
  ingestion/           loaders (pdf/md/txt/docx), chunker, pipeline (hash→dedupe→embed→upsert)
  services/            llm.py (OpenAI), vectorstore.py (Pinecone), audit.py
  db/                  SQLite schema + connection helper
  static/              index.html, styles.css, app.js
data/
  sample_runbooks/     seed docs (RDS, K8s, Sev1 SOP, TLS postmortem) — add more
  sqlite/              checkpoints.db, app.db (Docker volume)
scripts/               check_setup.py, seed_ingest.py, ask.py
tests/                 unit/, integration/, e2e/
```

---

## Phase-by-phase procedure

Each phase ends with a **done check**. Don't move on until it passes.

### Phase 0 — Setup (Day 1, ~1 h)

1. **Install Ollama and pull the local models** (free, runs on your Mac)
   ```bash
   brew install ollama
   brew services start ollama          # keeps the Ollama server running in the background
   ollama pull qwen2.5:7b              # ~4.7 GB, answers + graders
   ollama pull nomic-embed-text        # ~270 MB, embeddings (768 dims)
   ollama list                         # both should be listed
   ```
   No Homebrew? Download the app from https://ollama.com/download instead.
   To use OpenAI instead, set `LLM_PROVIDER=openai` and the OpenAI model names in `.env`
   (see `.env.example`), with `EMBEDDING_DIM=1536` and a matching index name.
2. **Get API keys**
   - OpenAI (only if `LLM_PROVIDER=openai`): https://platform.openai.com/api-keys
   - Pinecone: https://app.pinecone.io → API Keys
   - Tavily: https://app.tavily.com
3. **Create your env file**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and paste the three keys.
4. **Create the virtualenv and install**
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   (or `make install`). In VS Code: `Cmd+Shift+P` → *Python: Select Interpreter* → `.venv`.
5. **Check the model + Pinecone** — this also creates the `incident-kb-768` index (768 dims, cosine):
   ```bash
   python scripts/check_setup.py
   ```

✅ **Done when** it prints `Embedding OK, dim=768` and `Pinecone OK, match: setup-check`.

Files: `app/config.py`, `app/services/llm.py`, `app/services/vectorstore.py`

### Phase 1 — Ingestion pipeline (Day 1, ~3 h)

1. Add more docs to `data/sample_runbooks/` (aim for 8–10: Redis eviction, DNS outage,
   rollback SOP, IAM access denied…). File names drive the doc type: `runbook_*`, `sop_*`,
   `postmortem_*`; the second word becomes the `service` metadata.
2. Read through `app/ingestion/` — loaders → chunker (~800 tokens, 100 overlap) → pipeline,
   which hashes each file (SHA-256) so re-uploads are skipped and a changed file replaces its
   old vectors.
3. Seed Pinecone:
   ```bash
   python scripts/seed_ingest.py
   ```

✅ **Done when** every doc prints `ingested`, a second run prints `duplicate` for all of them,
and in the Pinecone console a query for "database CPU spike" returns the RDS runbook.

### Phase 2 — Baseline RAG (Day 1, ~2–3 h)

1. `app/services/vectorstore.py:get_retriever` returns top-k (optionally filtered by service).
2. `app/graph/prompts.py:GENERATE_PROMPT` forces the answer format: Probable cause /
   Troubleshooting steps / Escalation / Sources.
3. Try it from the CLI:
   ```bash
   python scripts/ask.py INC-test "RDS CPU at 98%, queries slow"
   ```

✅ **Done when** 5 sample questions return answers citing the right doc.

### Phase 3 — Self-RAG LangGraph (Day 2, ~4–5 h)

The core of the project. Open these side by side:
- `app/graph/state.py` — what flows between nodes (`question`, `documents`, `generation`,
  `rewrite_count`, `generation_count`, `route_trace`, `messages`…)
- `app/graph/nodes/graders.py` — three structured yes/no graders: **relevance**,
  **hallucination** (grounded?), **usefulness** (answers the question?)
- `app/graph/edges.py` — the two routers that make it self-correcting
- `app/graph/builder.py` — the wiring shown in the diagram above

Work through it:
1. Run `scripts/ask.py` with a vague question ("db is cooked") and watch `route:` show a
   `transform_query` loop.
2. Tune grader prompts if everything is graded "no" (common first problem).
3. Run the unit tests: `pytest tests/unit -q`.

✅ **Done when** scenarios S1–S7 from the plan reproduce and `route_trace` matches the expected path.

### Phase 4 — Web fallback + persistent memory (Day 2, ~2–3 h)

1. **Tavily**: `app/graph/nodes/web_search.py` runs after rewrites are used up; web results
   are tagged `doc_type: web` and the prompt labels those steps "external, verify before applying".
   Try something not in your KB: `python scripts/ask.py INC-web "Azure Front Door 502 errors"`.
2. **Memory**: `builder.get_graph()` compiles with `SqliteSaver` at `data/sqlite/checkpoints.db`.
   `thread_id` = incident id, so each incident has its own history.
   `nodes/contextualize.py` rewrites follow-ups into standalone questions.
   ```bash
   python scripts/ask.py INC-1 "RDS CPU at 98%"
   python scripts/ask.py INC-1 "what if that doesn't help?"
   ```

✅ **Done when** the second question is understood as being about RDS, even when run as a
separate process (memory survives restarts).

### Phase 5 — FastAPI + audit logging (Day 3, ~2–3 h)

```bash
uvicorn app.main:app --reload --port 8000     # or: make run
```
Open http://localhost:8000/docs (Swagger) and try each endpoint:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | key + SQLite checks |
| POST | `/api/incidents` | create incident `{title, service, severity}` |
| GET | `/api/incidents` | list incidents |
| POST | `/api/chat` | `{incident_id, message}` → answer, sources, route_trace |
| GET | `/api/chat/{incident_id}/history` | conversation from the checkpointer |
| POST | `/api/ingest` | multipart upload (pdf/md/txt/docx, ≤10 MB) |
| GET | `/api/documents` | indexed documents |
| GET | `/api/audit` | audit rows, filter by `incident_id` / `status` |

Every chat call writes one row to `audit_log` (user from the `X-User` header, question,
doc ids, `web_used`, `route_trace`, grader scores, latency, status/error).

TODO in this phase: deep health checks (`?deep=true`), retry with backoff on upstream calls,
audit `degraded` status when Tavily fails.

✅ **Done when** every endpoint works in Swagger and each chat call adds exactly one audit row.

### Phase 6 — Incident management UI (Day 3, ~2–3 h)

Open http://localhost:8000. The starter UI in `app/static/` already has:
incident list + "New incident" form · chat with source chips (green = internal, orange = web)
and a "How I got this" route trace · runbook upload · audit table.

Improve: loading spinners, markdown rendering of answers, audit filters, status changes.

✅ **Done when** in the browser you can create an incident, ask, follow up, upload a new
runbook, ask again and see it cited.

### Phase 7 — Docker, tests, demo (Day 3, ~2 h)

```bash
docker compose up --build -d       # or: make docker-up
docker compose exec copilot python scripts/seed_ingest.py
docker compose logs -f
```
Open http://localhost:8000. SQLite files live in the `sqlite_data` volume, so
`docker compose restart` keeps incidents, memory and the audit log.

Tests:
```bash
pytest -q
```
Fill in `tests/integration/test_graph_paths.py` (mock the LLM + Tavily, assert
`route_trace` per scenario) and `tests/e2e/test_api_smoke.py`.

✅ **Done when** `docker compose up` on a clean machine serves the UI, memory survives a
restart, and all tests pass.

---

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` (local) or `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Docker overrides to `host.docker.internal` |
| `OPENAI_API_KEY` | — | only for `LLM_PROVIDER=openai` |
| `PINECONE_API_KEY` | — | required |
| `TAVILY_API_KEY` | — | required for web fallback |
| `LLM_MODEL` | `qwen2.5:7b` | final answer model |
| `GRADER_MODEL` | `qwen2.5:7b` | graders, rewrites, contextualize |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | `nomic-embed-text` / `768` | must match the index |
| `PINECONE_INDEX` / `_CLOUD` / `_REGION` | `incident-kb-768` / `aws` / `us-east-1` | serverless index |
| `RETRIEVAL_K` | `4` | chunks retrieved |
| `MAX_REWRITES` / `MAX_GENERATIONS` | `2` / `3` | Self-RAG loop caps |
| `WEB_RESULTS` | `3` | Tavily results |
| `CHECKPOINT_DB` / `APP_DB` | `data/sqlite/...` | SQLite paths |
| `MAX_UPLOAD_MB` | `10` | upload limit |

## Common commands

```bash
make install     # venv + deps
make check       # Phase 0 check
make seed        # ingest sample runbooks
make ask         # CLI question
make run         # dev server with reload
make test        # pytest
make docker-up   # build + run container
```

## Troubleshooting

- **`Connection refused` on port 11434** → Ollama isn't running: `brew services start ollama`.
- **Slow answers** → each question makes several model calls (graders); `qwen2.5:7b` takes a few seconds each on Apple Silicon. Try `qwen2.5:14b` for quality or `qwen2.5:3b` for speed.

- **Everything goes to web search** → grader too strict; loosen `GRADE_DOCUMENT_PROMPT` and
  check that `seed_ingest.py` actually ingested docs.
- **`dimension mismatch` from Pinecone** → index was created with a different dim; delete it
  in the console and rerun `check_setup.py`.
- **`database is locked`** → keep a single uvicorn worker (SQLite checkpointer is per process).

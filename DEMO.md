# Demo script (about 10 minutes)

Shows the four headline behaviours from the plan: a grounded answer (S1), a follow-up that
uses memory (S9), the web fallback (S4) and the safety net (S7), plus ingestion and the audit log.

## Before the demo

```bash
ollama list                                   # qwen2.5:7b and nomic-embed-text present
docker compose up --build -d                  # or: make docker-up
docker compose exec copilot python scripts/seed_ingest.py   # first time only (make docker-seed)
make e2e                                      # 8 end-to-end checks, about 25 s
```

Open http://localhost:8000 and type your name in the top bar. Hover the health dot: every
check should be ✓ (click it for a deep check that calls Ollama, embeddings and Pinecone).

## 1. Grounded answer from a runbook (S1), about 1 minute

1. Create an incident: **"Orders API slow, RDS CPU 98%"**, service `rds`, **Sev2**.
2. Ask: **"RDS CPU at 98%, queries slow"**.
3. Point out: the cause / numbered steps / escalation format, `CONFIRM FIRST` highlighted on the
   destructive step, the green 📘 `runbook_rds_high_cpu` chip and the `ok` badge.
4. Open **How I got this**: `contextualize → retrieve → grade_documents → generate → check_answer → finalize`,
   with the draft graded *grounded, useful* on the first try.

## 2. Follow-up with memory (S9), about 1 minute

1. Click the suggestion **"What if that doesn't help?"** (or type "who should I page?").
2. Point out: the copilot knew "that" meant the RDS CPU problem. The follow-up was rewritten
   into a standalone question before searching, and the answer still cites the RDS runbook.
3. Optional: run `docker compose restart`, reload the page, open the incident: the conversation
   is still there (SQLite checkpoints in the `sqlite_data` volume).

## 3. Something the runbooks don't cover: web fallback (S4), about 1 minute

1. New incident **"Azure Front Door 502s"**, ask **"Azure Front Door 502 errors"**.
2. Point out in **How I got this**: two `transform_query` rewrites (orange), then `web_search`.
3. The sources are orange 🌐 chips that open the Microsoft pages, and the answer says to verify
   external steps before applying them.

## 4. Add a runbook live and see it cited, about 2 minutes

1. Write a small file, e.g. `runbook_sqs_backlog.md`:
   ```
   # Runbook: SQS Queue Backlog
   Service: sqs

   1. Check ApproximateAgeOfOldestMessage and NumberOfMessagesVisible.
   2. Check consumer errors and the dead-letter queue.
   3. Scale consumers (raise Lambda concurrency or ECS task count).
   ```
2. Drag it onto **Runbooks** and click **Upload & index**. It appears in the list.
3. Upload it again: the toast says it is already indexed (content hash dedupe).
4. New incident, ask **"SQS backlog growing, oldest message age rising"**: it cites the new runbook.
5. Remove it afterwards with the ✕ on the document.

## 5. The safety net (S7)

Explain, then show `tests/integration/test_graph_paths.py::test_s7_loop_limits_give_safe_answer`:
if an answer fails the grounding check 3 times, the copilot never guesses. It quotes the
matching runbook word for word (status `degraded`), or says to escalate if nothing matched.

```bash
pytest tests/integration -q      # all graph paths S1-S11 with fake models, under 2 s
```

## 6. Audit log, about 1 minute

Open **Audit log**, tick **Only this incident**, click a `chat` row: user, question, rewritten
queries, docs used, route, each answer check and latency. Filter by status `degraded` to show
every request where the copilot fell back to the safe answer.

## Talking points

- **Self-correcting:** relevance grading, query rewriting, grounding and usefulness checks,
  each with hard loop limits (2 rewrites, 3 drafts).
- **Runs locally:** Ollama `qwen2.5:7b` + `nomic-embed-text`; switch to OpenAI with one setting
  (`LLM_PROVIDER=openai`).
- **Auditable:** one audit row per request, even when it fails.
- **Tested:** 34 unit and integration tests (no keys needed) plus 8 end-to-end tests
  against the running container.

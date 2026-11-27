"""Phase 2-3: all prompt templates in one place so they are easy to tune."""

CONTEXTUALIZE_PROMPT = """Given the chat history and a follow-up question, rewrite the
follow-up as a standalone question about the same incident. Do not answer it.

Chat history:
{history}

Follow-up: {question}
Standalone question:"""

GRADE_DOCUMENT_PROMPT = """You check retrieved documents for an incident response copilot.
Answer 'yes' if the document is about the same system, service or symptom as the question,
or contains any cause, troubleshooting step or escalation path that could help answer it,
even partially. Answer 'no' only if the document is about an unrelated system or problem.
Be lenient: a separate check catches unsupported answers later.

Document:
{document}

Question: {question}"""

GENERATE_PROMPT = """You are an SRE incident response copilot. Answer ONLY from the context.
If the context is insufficient, say so. Each context block starts with [title] (doc_type).
Only steps taken from blocks whose doc_type is "web" get the label
"(external, verify before applying)". Flag any destructive command with "CONFIRM FIRST".

Format:
**Probable cause**
**Troubleshooting steps** (numbered)
**Escalation**
**Sources** (list the [title] of each context block you used, nothing else)

Context:
{context}

Question: {question}"""

RETRY_GENERATION_NOTE = """

IMPORTANT: your previous draft was rejected because it contained steps or facts that are
not in the context. Write a shorter answer using ONLY what the context says. If the context
only covers part of the question (for example only the escalation path), give that part and
say plainly that the runbook does not cover the rest."""

HALLUCINATION_PROMPT = """You check whether an incident answer is grounded in the facts.

Answer 'yes' when every specific troubleshooting step, command, metric, threshold and
escalation rule in the answer appears in (or is a close paraphrase of) the facts.
These are ALLOWED and do not make an answer ungrounded:
- section headings, summaries and rewording of the facts
- a probable cause inferred directly from the facts
- saying that the facts do not cover something
- safety notes such as "CONFIRM FIRST" or "verify before applying"

Answer 'no' only if the answer adds a specific step, command, tool, number or claim
that is NOT in the facts.

Facts:
{documents}

Answer:
{generation}"""

ANSWER_USEFULNESS_PROMPT = """You check whether an incident answer is useful to the on-call engineer.

Answer 'yes' if it gives at least one concrete check, troubleshooting step, mitigation or
escalation path that applies to the question. A short answer is fine, and it does not need
to name a root cause.
Answer 'no' only if it just restates the symptoms, refuses, or is about a different problem.

Question: {question}
Answer: {generation}"""

REWRITE_PROMPT = """Rewrite this incident question to be a better search query for an
internal runbook / SOP / postmortem knowledge base. Use precise technical terms.
Return only the rewritten query.

Question: {question}"""

INSUFFICIENT_EVIDENCE = (
    "I could not find enough grounded evidence to answer this safely. "
    "Please escalate to the on-call lead and attach the incident details."
)

PARTIAL_EVIDENCE = (
    "I couldn't write a fully verified answer, so here is exactly what the matching "
    "runbook says. Nothing below was added by the model."
)

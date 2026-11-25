"""Phase 2-3: all prompt templates in one place so they are easy to tune."""

CONTEXTUALIZE_PROMPT = """Given the chat history and a follow-up question, rewrite the
follow-up as a standalone question about the same incident. Do not answer it.

Chat history:
{history}

Follow-up: {question}
Standalone question:"""

GRADE_DOCUMENT_PROMPT = """You grade whether a retrieved document is relevant to an
incident question. If it contains keywords or meaning related to the question, answer 'yes'.
Otherwise answer 'no'.

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

HALLUCINATION_PROMPT = """Is the answer below fully grounded in / supported by the facts?
Answer 'yes' or 'no'.

Facts:
{documents}

Answer:
{generation}"""

ANSWER_USEFULNESS_PROMPT = """Does the answer below actually resolve the question
(gives a cause and actionable steps, not just restating symptoms)? Answer 'yes' or 'no'.

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

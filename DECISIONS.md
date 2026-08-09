# DECISIONS

1. **Deterministic-first routing with optional LLM later.** I shipped deterministic extraction for known business rules so retries and tests are stable. With two more weeks I would add Gemini as a secondary classifier only for low-confidence triage candidates.
2. **Gemini rate limits and retries.** Ingest still does not require Gemini in the critical path, so routing cannot fail from free-tier quota. `/api/chat` optionally calls Gemini only to phrase an already-computed SQL-backed answer; if the call fails, the backend falls back to the deterministic draft answer.
3. **Idempotency.** The database has unique keys on `(candidate_id, source_email_id)` and `(candidate_id, thread_id)`. `/ingest` records every decision once and updates existing thread tasks instead of creating duplicates.
4. **Chat data model.** Every processed email gets a row in `decisions`; task updates get `update_events`; current task state is in `tasks`. Chat answers query these tables directly, so the UI gets instant counts without re-classifying old emails.
5. **Hallucination guardrail.** `/api/chat` pattern-matches supported analytical intents, computes exact SQL-backed `supporting_data`, and only then optionally asks Gemini to rephrase the draft without changing numbers. It refuses action requests such as sending email.
6. **Known shipped weakness.** The regex date/company extraction misses some messy signatures and relative dates. I prefer returning `null` or triage over inventing fields, but this will lower recall on some obscure formats.

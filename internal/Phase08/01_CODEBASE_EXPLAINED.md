# Phase 8 explained: memory

> **What this document is.** A plain-language explanation of the code written in Phase 8 of CloudDesk, for explaining it to recruiters, hiring managers and interview boards. It describes only what exists in the repository today.
>
> **Status of this phase:** implemented and checked locally. All three tasks (P8-1 to P8-3) are done, plus a small container fix. In a run made for this document (2026-11-27) the whole suite passed (1103 tests, 31 of them new or extended in Phase 8) and `ruff check .` was clean. Nothing was committed or deployed when this document was written (the work has since merged as pull request #54, and nothing is deployed). Phase 8 has **no language model, no graph node and no API route**: the memory service is a library that Phase 10's nodes will call (planned). Today only tests call it.
>
> **Related documents:** [system design evolution](./02_DESIGN_EVOLUTION.md), [infrastructure evolution](./03_INFRA_EVOLUTION.md), the local-only `04_INTERVIEW_QNA.md`, and [Phase 7 explained](../Phase07/01_CODEBASE_EXPLAINED.md).

---

## A. Executive summary

**Say it aloud.** "A good support agent remembers the customer. I built the memory layer: a short-lived scratchpad in Redis for the ticket being worked on, and a permanent notebook in the database for each customer. Before anything is written to the notebook it is scrubbed of card numbers, keys and passwords, repeats are skipped, and low-confidence guesses are thrown away. A customer can ask to be forgotten, and then both their notes and their search vectors are deleted."

- **What the phase accomplished.** `memory/short_term.py` (Redis), `memory/long_term.py` (the `customer_memory` table through its repository), `memory/memory_service.py` (`recall_customer`, `record_resolution`), and an adapter `backend/app/services/customer_memory_service.py` that wires them to the app.
- **Problem solved.** A resolved ticket teaches something (the past issue, the first steps that helped, how it ended). Without a safe memory, the next ticket starts cold, or worse, the notes hold secrets or another customer's data (N7).
- **Before and after.** Before: a `customer_memory` table and a repository existed (Phase 2) but nothing decided what may be written. After: a tested write path with a confidence floor, scrub, de-duplication and erasure.

## B. Business problem and solution

1. **Real-world problem.** Support teams repeat themselves when nothing remembers a customer, and an AI that remembers carelessly can store a pasted credit card.
2. **Limitation of the basic approach.** Appending every ticket body to a notes field stores secrets and noise and cannot be erased cleanly.
3. **Solution.** Store a few short, scrubbed, confident facts per customer; never the ticket text.
4. **Benefit.** Faster, more consistent resolutions and a clean answer to a deletion request.
5. **Why appropriate.** It follows `CLAUDE.md` section 7.5 and the rule that memory never holds secrets.

Analogy: a short-term scratchpad that is thrown away after a day, and a customer file kept in a cabinet where every page is checked before it is filed.

## C. Application architecture in simple language

| Component | Purpose | Input and output | Needs it? |
|---|---|---|---|
| Short-term memory, `memory/short_term.py` | Keep a ticket's conversation and workflow state for 24 hours; hold the search cache for 300 seconds | A Redis client in; messages, state, cached text out | Without it, state would live only in a process |
| Long-term memory, `memory/long_term.py` | Remember confident facts permanently, skip repeats, recall up to 10, erase | A repository (and optional vector store) in; notes out | Without it, nothing enforces the 0.7 floor or erasure |
| Memory service, `memory/memory_service.py` | The two calls the workflow needs: recall and record | Customer id, ticket id, category, summary, steps, resolution in; a report of what was written out | Without it, every caller would rebuild the note rules |
| Adapter, `backend/app/services/customer_memory_service.py` | Plug in the app's scrub, repository and vector store | A database session in; a ready service out | Without it, `memory/` would have to import the app |

Layer rule: `memory/` imports nothing from `backend/app`. Everything app-specific (the Redis client, the repository, the scrub function, the vector store) arrives as an argument. The tenant filter stays inside the repository, so no file in `memory/` names a tenant.

## D. Codebase structure and file-by-file explanation

| File | What it does | Main parts | Interview line |
|---|---|---|---|
| `memory/__init__.py` | Creates the package and states its rule: no app imports | docstring | "A library with no knowledge of the web app." |
| `memory/short_term.py` | Redis facade | `ShortTermMemory` (`append_message`, `conversation`, `save_workflow_state`, `workflow_state`, `clear_ticket`), `RetrievalCache` (`get`, `set` with a TTL), `cache_key`, `SHORT_TERM_TTL_SECONDS` (86400), `CACHE_TTL_SECONDS` (300) | "A scratchpad that expires on its own." |
| `memory/long_term.py` | Durable notes | `LongTermMemory.remember` (type check, floor 0.7, scrub hook, duplicate check, optional vector), `recall` (at most 10, newest first), `erase` (vectors first, then rows), `Note`, `ErasureReport`, `MemoryRepository` protocol | "Only confident, clean, new facts get in." |
| `memory/memory_service.py` | Orchestrates one resolution | `MemoryService.recall_customer`, `record_resolution` (past issue, steps 1 to 3, resolution note), `RecordReport` | "Three kinds of note, one call." |
| `backend/app/services/customer_memory_service.py` | Wiring | `build_memory_service(session)`, `erase_customer_memory(session, customer_id)` | "The only place memory meets the app." |
| `backend/app/repositories/memory.py` | Changed: added `ids_for_customer` (every row id, no limit) | one method | "Erasure must not stop at the recall limit of 10." |
| `backend/app/core/scrub.py` | Relied on (Phase 7): removes secrets | `scrub` | "The black marker." |
| `tests/unit/test_short_term.py`, `test_long_term.py`, `test_memory_service.py` | The proof | 8, 11 and 8 tests | "Each rule has a test that can fail." |

## E. End-to-end execution flow

The designed flow (the graph nodes that call it are planned, Phase 10):

1. A ticket reaches the customer-context step. The node calls `recall_customer(customer_id)` and gets up to ten notes.
2. The workflow finishes. The memory-update step calls `record_resolution(...)` with the category, a one-line summary, the troubleshooting steps and the resolution text.
3. For each of five candidate notes (past issue, up to three steps, resolution) the service scrubs the text, drops it if it contains the raw ticket body, and asks long-term memory to remember it.
4. Long-term memory discards a fact below 0.7 confidence, skips an exact duplicate (same customer, type and text) and otherwise inserts a row carrying the ticket id as its source.
5. The caller commits the session. Calling the same resolution again changes nothing, because the note text is deterministic and duplicates are skipped.
6. On an erasure request, `erase_customer_memory` lists every row id, deletes those vectors, then deletes the rows.

Today steps 1 to 6 run only inside tests.

## F. Technical concepts explained simply

- **TTL.** Time to live: Redis deletes a key by itself after that many seconds. 24 hours for conversation and state, 300 seconds for cached search results.
- **Facade.** A small class that hides a client behind the few calls the app needs.
- **Protocol.** A Python description of the methods an object must have. `MemoryRepository` lets `memory/` use the real repository without importing it.
- **Confidence floor.** Facts below 0.7 are guesses; storing a guess is worse than storing nothing.
- **Idempotent.** Doing it twice has the effect of doing it once; here, through deterministic text plus exact-duplicate skipping.
- **Erasure.** Deleting rows and vectors together so no search can still find the customer.

## G. Design decisions and trade-offs

- **Scrub is injected, not imported.** `memory/` must not import the app, so the service takes a `scrub` function and the adapter passes `app.core.scrub.scrub`. Trade-off: a caller that builds the service without a scrub function would store unscrubbed text; only the adapter builds it in app code.
- **One note per step, text built from fixed templates.** `Step 1: ...`, `Resolution: ...`. This is what makes the repeat-call test possible. Trade-off: two different resolution texts for the same ticket give two notes.
- **Raw ticket body is dropped, not trimmed.** The service accepts the body only to exclude it.
- **Rows only, no memory vectors from the app wiring.** Writing memory vectors into the same collection as the knowledge base would mix customer notes into knowledge search. The vector hook exists and erasure deletes any such vectors, but the app does not write them.
- **The short-term cache duplicates the retriever's key shape.** `memory/short_term.py` cannot import `rag`-side helpers without coupling, so a test asserts its `cache_key` equals the retriever's.

## H. Error handling and failure scenarios

- Unknown memory type: `ValueError`, nothing stored.
- Confidence below 0.7, empty text, or a duplicate: `remember` returns `None`, counted as skipped.
- Redis key expired: `conversation` returns an empty list and `workflow_state` returns `None`.
- Erasure for a customer with no notes: reports zero rows.
- Not handled: a failure between deleting vectors and deleting rows (the rows would remain until a retry; the retry is safe), and no scrub for non-secret personal data such as a name in a summary.

## I. Testing and verification

| File | Tests | What it proves |
|---|---|---|
| `tests/unit/test_short_term.py` | 8 | TTLs of 24 hours and 300 seconds, expiry by moving the clock, key shape equal to the retriever's, ordered conversation |
| `tests/unit/test_long_term.py` | 11 | Four types, floor of 0.7, duplicates skipped, at most 10 newest first, scrub hook, erasure leaves no row and no vector and spares another customer |
| `tests/unit/test_memory_service.py` | 8 | Past issue, three steps and resolution note; twice gives one resolution note; no card, key or password in the table; raw body dropped; nothing for another customer; adapter scrubs and erases |
| `tests/unit/repositories/test_repositories_memory.py`, `test_repositories_tenant_isolation.py` | 2 added | `ids_for_customer` is unbounded and tenant scoped |
| `tests/deployment/test_dockerfiles.py`, `test_compose.py` | 2 added or changed | Image copies `agents/` and `memory/`; configurable host ports |

Run: `uv run python -m pytest -q`. Result on 2026-11-27: 1103 passed, `ruff check .` clean. Deliberate breaks, each red then restored: TTL changed, floor lowered, vector delete removed, scrub removed, a unique suffix on the resolution note, `memory/` COPY line removed. Untested: real Redis TTLs, Postgres, a graph that calls the service.

## J. Interview-ready explanation

**30 seconds.** "Phase 8 is the memory layer. Redis holds a ticket's conversation and state for a day. The database holds a few permanent notes per customer. Every note is scrubbed, repeats are skipped, guesses below 70 percent confidence are dropped, and erasure removes notes and vectors together."

**2 minutes.** "`memory/` has three modules. Short-term wraps a Redis client with 24-hour keys and a 300-second search cache whose key matches the retriever's. Long-term sits on the existing repository: four note types, a 0.7 confidence floor, exact-duplicate skipping, recall of at most ten, and erasure that deletes vectors first. The service writes a past issue, the first three steps and a resolution note, each through the scrub function, and drops anything containing the raw ticket body. Because note text is deterministic, recording twice leaves one resolution note. `memory/` never imports the app; an adapter in the services layer wires in the scrub and the repository."

**5 minutes.** Add the layering, why vectors are not written by the app wiring, the unbounded id listing for erasure, the tenant filter living only in repositories, and the limits in section H.

**Non-technical.** "It is the assistant's notebook about each customer. Only useful, checked facts go in, never card numbers or passwords, and the whole file can be shredded on request."

**Architect.** "A library with injected ports (Redis client, repository protocol, vector store protocol, scrub function) so it is testable offline and free of app imports; policy (floor, dedup, cap) in one class; transaction ownership left to the caller; erasure ordered vectors before rows so a retry is safe."

## K. Key takeaways and next-phase dependencies

- Implemented: short-term Redis memory, long-term notes, the memory service, the wiring adapter, and a container fix. Not implemented: any caller on the live path, memory vectors written by the app, a route to request erasure.
- Understand before explaining: the floor, the scrub, the dedup, the erasure order, and why `memory/` takes everything as an argument.
- Reused later: Phase 10 nodes call `recall_customer` and `record_resolution` (planned); Phase 9 specialists receive the recalled notes in customer context (done: `CustomerAgent` in `agents/specialists/customer.py` calls `recall_customer`, though no graph runs it yet); the erasure function awaits an API route (not planned yet).

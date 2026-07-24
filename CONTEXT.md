# Mini Agent Harness — Project Context & Handoff

> **Using this in a new session:** point Claude at this file ("read
> CONTEXT.md") to resume with full context. See `ROADMAP.md` in the same
> folder for the detailed architecture + milestone table.

---

## What this project is

A **mini agent harness** built from scratch — the runtime "operating system"
that wraps an LLM with a reasoning loop, tools, and memory so it behaves like a
persistent autonomous agent instead of a one-turn chatbot. Inspired by
open-source harnesses like **OpenClaw** and **Nous Research's Hermes Agent**.

It is a *learning + portfolio* project, not a product meant to compete with
those. The point is to demonstrate deep understanding of how agents work
internally — the strongest possible signal for the target role.

## Who I am (the user)

- **Name:** Nelson. First time building an agent system; beginner-to-intermediate.
- **Goal:** land a **Software Engineer / AI Engineer** role. This project is the
  portfolio centerpiece.
- **How I learn best — please follow this:**
  - I **hand-code everything myself**. Do NOT write large chunks of code for me
    or build files for me. Walk me through **step by step**: explain a piece, I
    type it, I run it, I report back.
  - Explain like I'm still learning — plain language, concrete examples, and
    *why* not just *what*. I ask a lot of "why" and syntax questions; that's good.
  - Build small and runnable. One milestone at a time. Don't jump ahead.
  - I prefer building from scratch over cloning/frameworks so I understand every
    line (this is a deliberate choice, and it's working).

## Key decisions already made

- **Build the core RAW — no LangGraph/LlamaIndex/smolagents.** The harness *is*
  the framework; using one would hide the exact thing I'm trying to learn. (Study
  frameworks later as "oh, I built a mini version of this.")
- **Signature feature = RAG-backed long-term memory.** I already built a full RAG
  system from scratch, so the agent's long-term memory will reuse that
  (embeddings + vector search over past conversations/facts). This is the
  differentiator.
- Chose the harness over a code-reviewer or text-to-SQL agent because building
  the runtime is the deepest "I understand agents" signal for an AI Eng role.

## What I've already built (prior work to reuse)

- **RAG from scratch** — `~/Desktop/Projects/rag-project/`, pushed to GitHub at
  `github.com/nelson35c/rag-from-scratch`. FastAPI + Supabase (pgvector) + Gemini,
  plus a Next.js/TypeScript frontend. I understand chunking, embeddings, cosine
  similarity, vector search (`match_chunks` SQL fn), and grounded generation with
  citations. **This becomes the agent's memory layer (M4).**
- **Raw tool-calling warm-up** — *(⚠ this folder no longer exists on disk — it was
  at `~/Desktop/Projects/agent-warmup/search_tool.py`.)* It was a working Tavily
  web-search tool + a single-round function-calling example; I've seen the model
  request a tool and hand it back. M1 rebuilds that from scratch rather than
  reusing it — which is fine, re-deriving the tool-schema pattern is the point.

## Architecture (condensed — full version in ROADMAP.md)

```
User → Interface (CLI first) → AGENT LOOP (think→tool→observe→repeat)
         ├─ LLM client (Gemini)
         ├─ Tool registry (web search, file I/O, …)
         └─ Memory: short-term (messages list) + long-term (RAG/pgvector)
                                                → Supabase (vectors + state)
       every step → Observability (structured logs)
```

## Stack

- **Language:** Python, raw (no agent framework for the core).
- **LLM:** provider-swappable via the single `agent/llm.py` seam (base_url + key +
  model name; nothing else in the codebase changes). **Currently Groq**
  (`base_url="https://api.groq.com/openai/v1"`, `GROQ_API_KEY` /
  `GROQ_CHAT_MODEL=openai/gpt-oss-20b`) — free tier, and reliable at tool calls.
  History: started on Gemini `gemini-2.5-flash-lite`; credits ran out → tried
  DeepSeek (`deepseek-chat`, but it has **no free tier** → 402) → Groq.
  **Model tool-call reliability varies a lot:** flash-lite emitted `<ctrl42>`
  text, Groq's `llama-3.3-70b-versatile` consistently mangled the tool-call
  format (`tool_use_failed`); `openai/gpt-oss-20b` is the one that works. All the
  `openai` Python SDK, using OpenAI-compatible endpoints throughout.
- **Memory + state:** Supabase (pgvector). Embeddings must be **1536 dims**
  (`gemini-embedding-001` with `dimensions=1536`) to match the `vector(1536)`
  column — same rule as the RAG project.
- **Tools:** plain Python functions; **Tavily** for web search
  (`tavily-python`), file I/O later.
- **Interface:** CLI first; maybe a thin Next.js UI later (reuse frontend skills).
- **Observability:** structured logging first; optional **LangFuse** later.

## Roadmap status

Milestones (see ROADMAP.md for the table). Spine = M1–M4.

- **M1 — The agent loop** ✅ **DONE.** `agent.py` runs a `for`-loop capped by
  `MAX_STEPS`, calling model→tool→model until the model returns plain text (no
  `tool_calls`). Built flat (one file), with a **`calculator`** tool rather than
  web search — a zero-quota tool so loop mechanics could be debugged without
  burning the Gemini free tier. Verified: "847 × 23, then subtract 1000" produced
  two *sequential* tool calls, the second on the agent's own initiative.
  Key shapes established: `messages` list is the whole agent state; the assistant
  message is appended *before* the `tool_calls` branch (the API requires it to
  precede `role: "tool"` results); tool errors return as observation strings
  rather than raising; `TOOLS` dict does name→callable dispatch.
- **M2 — Tool registry** ✅ **DONE.** Flat file split into the `agent/` package:
  `main.py`, `agent/{__init__,llm,loop}.py`, `agent/tools/{__init__,calculator,
  files,web_search}.py`. Registry (`agent/tools/__init__.py`) uses a `@tool(schema)`
  decorator that stores `name → (fn, schema)` in `_REGISTRY`; `schemas()` feeds the
  model, `dispatch(name, args)` runs `fn(**args)` and contains failures as strings.
  Four tools registered: `calculator`, `read_file`, `write_file`, `web_search`.
  Verified the agent *chooses* correctly — math→calculator, current-events→web_search.
  - **Provider seam:** `agent/llm.py` holds the only Gemini-specific code
    (`complete(messages, tools)`); swapping providers is this one file.
  - **Registry gotcha:** `_REGISTRY = {}` at top, tool-module imports at the
    **bottom** of `__init__.py`. The `@tool` decorator only fires on import, so an
    unimported tool file is silently invisible.
  - **Env-at-import gotcha:** `web_search.py` reads `TAVILY_API_KEY` at import
    time, so it calls `load_dotenv()` itself rather than relying on `llm.py`'s call
    (import order isn't guaranteed). Any module reading config at import must load
    it — nudges toward a central `config.py` later.
  - **Tool-use is prompt-driven:** the model won't use a tool just because it's
    registered. `SYSTEM_PROMPT` in `loop.py` now injects `date.today()` and tells
    it to prefer `web_search` over stale memory — that's what made search fire.
  - **Open follow-ups (not blocking):** trace output is raw/noisy — proper
    `--verbose` formatting is M7.
- **File-path sandbox** ✅ done. `agent/tools/files.py` confines every read/write to
  a `workspace/` folder at the project root (git-ignored). `_safe_path()` does
  `(_WORKSPACE / path.lstrip("/\\")).resolve()` then `is_relative_to(WORKSPACE)`;
  returns `None` on escape. Defeats both `..` traversal (→ None) and absolute
  paths (`/etc/passwd` → pulled back inside workspace). Applies to `read_file` and
  `write_file` both. `WORKSPACE.mkdir` at import creates the folder.
- **Apple ecosystem tools (bonus, post-M2)** ✅ working. `agent/tools/apple.py`
  drives native macOS apps via **AppleScript through `osascript`** (a
  `subprocess` call), NOT `run_python`/EventKit/CalDAV — a dedicated tool per
  capability. Single chokepoint `_osa(script, timeout=30)` handles the three
  failure modes (non-macOS, timeout, AppleScript error) and returns strings.
  Tools: `create_note`, `create_reminder`, `read_reminders`,
  `create_calendar_event`, `read_calendar`. All register automatically — they're
  in the already-imported `apple` module, so no new import line per tool.
  - **AppleScript gotchas learned:** string literals need **double quotes** (wrap
    the Python f-string in single quotes so they pass through); a newline *inside*
    a quoted AS string is a syntax error — use `& return &` (newlines *between*
    statements are fine); dates are locale-brittle, so `create_calendar_event`
    parses ISO in Python and injects numeric components (`set year/month/day/...`)
    rather than passing a date string; `read_calendar` uses `timeout=45` (Calendar
    AS is slow). `DEFAULT_CALENDAR` constant at the top of the calendar section
    holds the user's real calendar name.
  - **Still open:** quote-escaping — a `"` in any title/body still breaks the
    script; needs an escape helper before real-world use.
  - **Model note:** `gemini-2.5-flash-lite` intermittently emits tool calls as
    plain-text `<ctrl42>call ...` instead of structured `tool_calls` (weakest model
    at tool use). Retrying usually fixes it; if it becomes chronic, bump to
    `gemini-2.5-flash` or switch provider (Groq) via the `llm.py` seam.
- **M3 — Short-term memory** ✅ **DONE.** `messages` was hoisted out of the loop:
  `run_agent(task)` → `run_turn(messages)` (advances a list passed in, mutating it
  by reference — that's the memory mechanism). New `chat()` REPL in `loop.py` holds
  one `messages` list across turns; `main.py` one-shots when given argv, else drops
  into `chat()`. Verified: "15×12" → "add 100 to that" (280, no numbers restated)
  → "save that number to math-result" wrote 280 to `workspace/`. Memory carries
  across turns and chains into a tool.
- **M4 — Long-term memory (vector recall)** ✅ **DONE.** The signature feature.
  Supabase table `agent_memories (id, session_id, content, embedding vector(1536),
  created_at)` + HNSW index + `match_memories()` SQL fn (cosine, optional
  `filter_session`) — mirrors the RAG project's `match_chunks`. Stores **raw
  exchanges** ("User: …\nAssistant: …"), one row per turn, embedded and recalled by
  semantic similarity (the thing FTS5 can't do — verified 0.724 similarity on a
  zero-keyword-overlap query). New package `agent/memory/`:
  - `embeddings.py` — `embed(text)` via **Gemini** `gemini-embedding-001`,
    `dimensions=1536` (embeddings stayed on Gemini even though chat moved to Groq;
    separate `OpenAI` client, separate provider — proof the seams are independent).
  - `store.py` — `save_memory(session_id, content)` (insert) and
    `recall_memories(query, ...)` (`.rpc("match_memories")`).
  - Wired into `chat()` on the Hermes lifecycle: **recall before** the turn (inject
    top matches as a `system` block, cross-session), **save after** the turn.
    `session_id = uuid4()` per run. Verified cross-restart: fact saved in session A
    recalled in a brand-new session B (empty short-term memory).
  - **Supabase gotcha:** inserts need the **service_role** key (anon key hit RLS
    `42501`). Key lives only in `.env` (git-ignored).
  - **Open refinements (not blocking):** recall block is injected every turn →
    `messages` grows with system blocks over long sessions (dedupe/threshold later);
    embeds every turn (2 embed calls/turn); a leftover `test-session` row exists in
    the DB.
- **M5 — Persistence** ✅ **DONE.** Saves/reloads the actual `messages` thread
  (distinct from M4: M4 = fuzzy fact recall by similarity; M5 = exact conversation
  resume). New `agent/memory/session_store.py`: `save_session` writes the list to
  `sessions/<uuid>.json` (git-ignored), converting SDK assistant objects via
  `.model_dump()`. `load_session` **cleans on load** — whitelists API-valid fields
  `{role, content, tool_calls, tool_call_id, name}`, drops `reasoning`/nulls, and
  strips all `system` messages (fresh prompt re-added, recall regenerated live).
  `list_sessions` = newest-first. `chat(resume=True)` seeds
  `messages = [system] + load_session(latest)` and reuses the same `session_id`
  (so save_session/save_memory keep appending to the same thread). `main.py`:
  `--resume` flag. Verified: new session mentioned "Kyoto"; after exit,
  `--resume` recalled "your Kyoto trip" (Kyoto was only in the restored thread).
- M6 — Skills / learning loop (write learned procedures to a store)
- **M7 — Observability** ✅ **DONE.** Single trace seam `agent/trace.py`: module
  `_verbose` flag + `set_verbose()`, one `_emit()` chokepoint (the spot LangFuse
  attaches in Phase 2), and event helpers `tool_call` / `tool_result` /
  `memory_recall` / `retry`. `loop.py` routes the old `print()`s through it; `chat()`
  traces recall hits + similarities. `main.py` parses `--verbose` (composes with
  `--resume` and one-shot). Clean by default, detailed on demand.
  **Retry hardening:** `complete()` in `llm.py` catches `BadRequestError` containing
  `tool_use_failed` and retries once (bounded `retries+1` loop; re-raises anything
  else) — so a flaky tool-call generation no longer kills the session. Retries are
  observable via `trace.retry`.
  Also: `sessions/` logs untracked from git (were committed before the ignore rule).
- M8 — Polish + demo (clean CLI, README, small eval suite)

Out of scope (avoid scope creep): multi-agent orchestration, WebSocket gateways,
MCP protocol, multi-user auth, fine-tuning.

## Environment gotchas (these bit me repeatedly — check first)

- **Three Pythons fight on this Mac:** system, Homebrew (`/opt/homebrew/bin/python3`),
  and conda `(base)`. Only the project **venv** has the right packages.
  - Always confirm `which python` shows the project's `venv/` before running.
  - A **full path** to an interpreter (e.g. `/opt/homebrew/bin/python3 x.py`)
    **bypasses** an activated venv. Use bare `python` with `(venv)` showing, or fix
    VS Code's selected interpreter.
  - `pip install X` and `python x.py` must run in the **same** environment.
- **`os.getenv` fails silently** (returns `None`) on a typo — suspect env-name
  typos, wrong folder, or missing `load_dotenv()`.
- **Don't name a file after a library** (e.g. `tavily.py` shadows the `tavily`
  package). Filename ≠ import name.
- **Secrets** live only in `.env` (never in code, never in chat). `.env` here has
  `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `TAVILY_API_KEY`.

## Quota reality (Gemini free tier)

- `gemini-2.5-flash` free tier has a **~20 requests/DAY** cap (hit it already).
  Agent loops make many calls per task, so use **`gemini-2.5-flash-lite`** (much
  higher daily allowance). A daily 429 can't be waited out; a per-minute 429 can.

## Where things live

- This project: `~/Desktop/Projects/oajan-agent/` (renamed from `agent-harness`)
  — `ROADMAP.md`, `CONTEXT.md`, `.gitignore`, `venv/`, and `agent.py` once built.
- RAG project (memory layer to reuse): `~/Desktop/Projects/rag-project/`.
- Hermes Agent clone (prior art, read at M6): `~/Desktop/Projects/hermes-agent-os-63815/`.

## How to continue in a new session

1. Read this file + `ROADMAP.md`.
2. Check whether `agent.py` (M1 loop) is built and runs — if not, finish M1:
   walk me through it step by step (setup venv, scaffolding from the warm-up, then
   the loop), let me type and run it.
3. Then proceed to M2 (tool registry). One milestone at a time, hands-on.

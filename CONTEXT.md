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
- **LLM:** Google **Gemini** via the **OpenAI-compatible endpoint**
  (`base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`), using
  the `openai` Python SDK. Model: **`gemini-2.5-flash-lite`** (chosen for a higher
  free-tier daily quota — see quota note below).
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
- **M2 — Tool registry** ← **CURRENTLY BUILDING. Paused mid-refactor.**
  - ✅ Package created: `main.py`, `agent/{__init__,llm,loop}.py`,
    `agent/tools/{__init__,calculator}.py`.
  - ✅ Registry verified working (no API calls needed):
    `python -c "from agent import tools; print(tools.schemas())"` lists
    `calculator`, and `tools.dispatch(...)` returns 19481. Both error paths
    (unknown tool name, bad arguments) return strings instead of raising.
  - ⏭ **Next, in order:** (1) run `python main.py "What is 847 times 23, then
    subtract 1000?"` to confirm end-to-end parity with M1; (2) delete the old
    root `agents.py` once parity holds; (3) `git add -A && git commit`;
    (4) then add `web_search` (Tavily) and file read/write so the agent has to
    *choose* a tool — that choice is the real M2 deliverable.
  - ⚠ Registry gotcha, already hit once: `agent/tools/__init__.py` must define
    `_REGISTRY = {}` at the top and keep `from agent.tools import calculator` at
    the **bottom**. The decorator only fires on import, so an unimported tool file
    is silently invisible to the agent.
- M3 — Short-term memory (conversation across turns)
- M4 — Long-term memory (RAG-backed vector recall) ← reuses the RAG project
- M5 — Persistence (state survives restart)
- M6 — Skills / learning loop (write learned procedures to a store)
- M7 — Observability (`--verbose` trace)
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

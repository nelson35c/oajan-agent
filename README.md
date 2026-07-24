# Oajan Agent

A personal AI agent harness built from scratch in raw Python — the runtime that
wraps an LLM with a reasoning loop, a tool registry, three tiers of memory, a
self-authored skill system, and observability. No agent framework: the harness
*is* the framework.

The point of the project is to demonstrate, line by line, how an autonomous agent
actually works internally — rather than importing that understanding from
LangChain or LlamaIndex.

```
 ██████╗  █████╗      ██╗ █████╗ ███╗   ██╗
██╔═══██╗██╔══██╗     ██║██╔══██╗████╗  ██║
██║   ██║███████║     ██║███████║██╔██╗ ██║
██║   ██║██╔══██║██   ██║██╔══██║██║╚██╗██║
╚██████╔╝██║  ██║╚█████╔╝██║  ██║██║ ╚████║
 ╚═════╝ ╚═╝  ╚═╝ ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝
```

## What it does

- **Reasoning loop** — a ReAct-style `think → act → observe` loop that calls tools
  and feeds the results back to the model until it produces a final answer.
- **11 tools** across a self-registering registry: arithmetic, web search,
  sandboxed file I/O, and native macOS integration (Notes, Reminders, Calendar).
- **Three kinds of memory** — short-term (in-conversation), long-term (semantic
  vector recall over past exchanges), and persistence (resume a conversation after
  restart).
- **A self-hosting skill system** — the agent writes reusable procedures for its
  future self by following a procedure it can read.
- **Observability** — a single trace seam with a `--verbose` mode and automatic
  retry on flaky tool-call generations.
- **Provider-swappable LLM** — the model backend is one file; the agent has run on
  Gemini, DeepSeek, and Groq with no changes to the loop.

## Architecture

```
        User
          │
          ▼
   ┌──────────────┐      CLI: chat REPL, --resume, --verbose, one-shot
   │  Interface   │
   └──────┬───────┘
          ▼
┌───────────────────────────────────────────────┐
│            AGENT LOOP  (run_turn)              │
│    think → call tool → observe → repeat        │
│    until the model returns a final answer      │
└───┬──────────────┬──────────────┬──────────────┘
    │              │              │
┌───▼─────┐  ┌─────▼──────┐  ┌────▼──────────────┐
│  LLM     │  │   Tool     │  │      Memory        │
│  client  │  │  registry  │  │  short · long · )  │
│(swappable)│  │ (@tool)    │  │  persistence       │
└──────────┘  └─────┬──────┘  └────┬──────────────┘
                    │              │
              ┌─────▼─────┐   ┌────▼──────────────┐
              │  calculator │   │  Supabase pgvector │
              │  web_search │   │  (vector recall)   │
              │  files      │   │  sessions/*.json   │
              │  apple      │   │  (persistence)     │
              │  skills     │   └───────────────────┘
              └───────────┘
     every step ──▶ trace seam (observability)
```

## The three tiers of memory

| Tier | What it stores | Survives restart? | Mechanism |
|---|---|---|---|
| **Short-term** | the live conversation | ✗ | a `messages` list held in RAM across turns |
| **Long-term** | facts / past exchanges | ✓ | embeddings in Supabase pgvector, recalled by cosine similarity |
| **Persistence** | the exact conversation thread | ✓ | the `messages` list serialized to `sessions/*.json` |

Long-term memory reuses a from-scratch RAG stack (embeddings + `match_memories`
SQL function over a `vector(1536)` column) as the agent's associative memory —
it recalls a relevant fact even when the query shares no keywords with it.
Persistence is different: it reloads a *specific* thread so a conversation can
resume where it left off.

## The skill system

A skill is a folder `skills/<name>/SKILL.md` — YAML frontmatter (name,
description) plus a body of numbered steps. Skills are **self-hosting**: a
hand-written bootstrap skill, `create-skill`, holds the authoring standards, so
when asked to learn a new procedure the agent reads `create-skill`, then calls
the `save_skill` tool to author the new one. Every skill's description is injected
into the system prompt as an index, so the agent knows what it can do.

## Tools

| Tool | Purpose |
|---|---|
| `calculator` | arithmetic (the model never does mental math) |
| `web_search` | current information via Tavily |
| `read_file` / `write_file` | sandboxed file I/O (confined to `workspace/`) |
| `create_note` | macOS Notes |
| `create_reminder` / `read_reminders` | macOS Reminders |
| `create_calendar_event` / `read_calendar` | macOS Calendar |
| `read_skill` / `save_skill` | recall and author skills |

macOS tools drive native apps through AppleScript (`osascript`) — no
`run_python`, no third-party services. File tools are sandboxed: every path is
resolved and rejected if it escapes `workspace/`, defeating `..` traversal and
absolute-path escapes.

## Tech stack

- **Language:** Python, raw (no agent framework for the core)
- **LLM:** provider-swappable via the `openai` SDK against OpenAI-compatible
  endpoints; currently Groq (`openai/gpt-oss-20b`)
- **Embeddings:** Gemini `gemini-embedding-001` (1536 dims)
- **Vector store:** Supabase (pgvector)
- **Tools:** plain Python functions; Tavily for search; `osascript` for macOS
- **CLI:** `rich` for the terminal UI
- **Observability:** structured trace seam (LangFuse-ready)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` (see `.env.example`):

```
GROQ_API_KEY=...
GROQ_CHAT_MODEL=openai/gpt-oss-20b
GEMINI_API_KEY=...              # embeddings only
TAVILY_API_KEY=...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=...                # service_role key
```

Long-term memory needs a Supabase table + recall function:

```sql
create extension if not exists vector;

create table agent_memories (
    id          bigint generated always as identity primary key,
    session_id  text        not null,
    content     text        not null,
    embedding   vector(1536),
    created_at  timestamptz not null default now()
);

create index on agent_memories using hnsw (embedding vector_cosine_ops);

create or replace function match_memories(
    query_embedding vector(1536),
    match_count int default 5,
    similarity_threshold float default 0.5,
    filter_session text default null
)
returns table (id bigint, session_id text, content text, similarity float, created_at timestamptz)
language sql stable as $$
    select m.id, m.session_id, m.content,
           1 - (m.embedding <=> query_embedding) as similarity, m.created_at
    from agent_memories m
    where (filter_session is null or m.session_id = filter_session)
      and 1 - (m.embedding <=> query_embedding) > similarity_threshold
    order by m.embedding <=> query_embedding
    limit match_count;
$$;
```

## Usage

```bash
python main.py                     # interactive chat
python main.py --resume            # resume the most recent conversation
python main.py --verbose           # show the full reasoning trace
python main.py "what is 47 * 89"   # one-shot
python evals/run_evals.py          # run the eval suite
```

## Project structure

```
main.py                      CLI entry point
agent/
  loop.py                    the agent loop + chat REPL
  llm.py                     LLM client (the provider seam)
  trace.py                   observability seam
  skills.py                  skill discovery / authoring
  tools/                     self-registering tool modules
    __init__.py              the @tool registry
    calculator.py · files.py · web_search.py · apple.py · skill_tools.py
  memory/
    embeddings.py            Gemini embeddings
    store.py                 vector memory (save / recall)
    session_store.py         conversation persistence
skills/
  create-skill/SKILL.md      the bootstrap meta-skill
evals/
  run_evals.py               the eval suite
workspace/                   sandbox for agent file output (git-ignored)
sessions/                    saved conversation threads (git-ignored)
```

## Design decisions

- **Built raw, no LangGraph/LlamaIndex.** Using a framework would hide the exact
  mechanics this project exists to demonstrate.
- **Postgres/pgvector over a dedicated vector DB.** The agent's memory and its
  relational state live in one transactional system, queryable with SQL beside the
  vector search. A dedicated vector DB is the right call at much larger scale.
- **One provider seam.** All model-specific code lives in `llm.py`; swapping
  providers is a base-URL, key, and model-name change and nothing else.
- **Frameworks belong around the loop, never inside it.** Observability (LangFuse)
  and MCP are candidates to layer on later; the reasoning loop stays hand-written.

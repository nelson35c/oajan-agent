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
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
```

## What it does

- **Reasoning loop** — a ReAct-style `think → act → observe` loop that calls tools
  and feeds the results back to the model until it produces a final answer.
  A running workflow can be interrupted mid-loop with `Ctrl+C`, which stops cleanly
  and leaves a valid conversation to continue from.
- **11 local tools** across a self-registering registry: arithmetic, web search,
  sandboxed file I/O, and native macOS integration (Notes, Reminders, Calendar) —
  **plus a Composio MCP meta-router** that reaches 1000+ external apps (Gmail,
  Slack, GitHub, Notion, …), with tools discovered and executed at runtime.
- **Three kinds of memory** — short-term (in-conversation), long-term (semantic
  vector recall over past exchanges), and persistence (resume a conversation after
  restart).
- **A self-hosting skill system** — the agent writes reusable procedures for its
  future self by following a procedure it can read.
- **A messaging gateway** — chat with the agent from the Telegram app on your
  phone, gated by an authorization allowlist since it can trigger real actions.
- **Observability** — a single trace seam that drives both a `--verbose` mode and
  **LangFuse**: every turn is one trace, with the LLM generation and each tool call
  as nested spans (tokens, cost, latency), grouped by conversation session.
- **Provider-swappable LLM** — the model backend is one file; the agent has run on
  Anthropic (Claude Sonnet 5), Gemini, DeepSeek, Groq, and Perplexity with no
  changes to the loop.

## Architecture

```
        User
          │
          ▼
   ┌──────────────┐      CLI (chat REPL · --resume · --verbose · one-shot · Ctrl+C)
   │  Interface   │      Telegram gateway (--telegram)
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
│  client  │  │  registry  │  │  short · long ·    │
│(swappable)│  │ (@tool)    │  │  persistence       │
└──────────┘  └─────┬──────┘  └────┬──────────────┘
                    │              │
          ┌─────────┴────────┐  ┌──▼────────────────┐
     ┌────▼──────┐   ┌───────▼─┐ │  Supabase pgvector │
     │  local     │   │ Composio │ │  (vector recall)   │
     │  calculator│   │   MCP    │ │  sessions/*.json   │
     │  web_search│   │  router  │ │  (persistence)     │
     │  files     │   │ 1000+    │ └───────────────────┘
     │  apple     │   │  apps    │
     │  skills    │   └──────────┘
     └───────────┘
     every step ──▶ trace seam ──▶ --verbose  ·  LangFuse
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

## External apps via MCP (Composio)

Beyond the local tools, the agent connects to [Composio](https://composio.dev) as
an **MCP client**, which exposes a meta-router over 1000+ external apps. Instead of
hardcoding each integration, four meta-tools are registered
(`COMPOSIO_SEARCH_TOOLS`, `COMPOSIO_GET_TOOL_SCHEMAS`, `COMPOSIO_MULTI_EXECUTE_TOOL`,
`COMPOSIO_MANAGE_CONNECTIONS`) and the model discovers what it needs at runtime:
search for a tool by intent → fetch its schema → execute it → start an OAuth flow
if the app isn't connected yet.

That router requires the model to assemble two-level-nested execution arguments,
which weaker models leave empty. Claude Sonnet 5 constructs them reliably, so it is
the default chat model — a concrete case of the provider seam mattering. `Ctrl+C`
still stops these workflows cleanly mid-run.

## Observability

The `trace.py` seam is the single point every step flows through, so a backend can
attach without touching the loop. Two are wired: the `--verbose` printer, and
**LangFuse**. When LangFuse keys are present, each turn opens one trace with the
LLM generation and every tool call as nested spans — model, token counts, cost, and
latency included — and all turns of a conversation are grouped by `session_id`.
With no keys set it is a zero-cost no-op, so the agent runs the same either way.

## Messaging gateway (Telegram)

The same `run_turn` core is reachable from Telegram, so you can operate the agent
from your phone. The gateway is built raw on the Telegram Bot API with long-polling
(`requests`, no bot framework): for each message it looks up that chat's
conversation, runs a turn, and sends the reply back. Each chat maps to a stable
session (`telegram-<chat_id>`), so conversations persist across restarts and reuse
the same long-term memory and LangFuse tracing as the CLI. Long replies are split
under Telegram's length cap, a typing indicator shows while a turn runs, and
`/reset` clears a conversation.

Because a messaged agent can trigger side-effecting tools (send email, create
events), authorization is enforced up front: only user IDs in
`TELEGRAM_ALLOWED_IDS` get a real reply. An unknown sender is told its own ID so it
can be allowlisted — nothing runs until you opt yourself in.

```bash
python main.py --telegram
```

## Tech stack

- **Language:** Python, raw (no agent framework for the core)
- **LLM:** provider-swappable via the `openai` SDK against OpenAI-compatible
  endpoints; currently Anthropic (`claude-sonnet-5`)
- **Embeddings:** Gemini `gemini-embedding-001` (1536 dims)
- **Vector store:** Supabase (pgvector)
- **Tools:** plain Python functions; Tavily for search; `osascript` for macOS;
  Composio over MCP for 1000+ external apps
- **CLI:** `rich` for the terminal UI
- **Messaging:** Telegram Bot API (raw long-polling via `requests`)
- **Observability:** structured trace seam → LangFuse

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` (see `.env.example`):

```
ANTHROPIC_API_KEY=...
ANTHROPIC_CHAT_MODEL=claude-sonnet-5
GEMINI_API_KEY=...              # embeddings only
TAVILY_API_KEY=...
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=...                # service_role key
COMPOSIO_API_KEY=...            # optional — external apps over MCP
LANGFUSE_PUBLIC_KEY=...         # optional — tracing
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
TELEGRAM_BOT_TOKEN=...          # optional — Telegram gateway (from @BotFather)
TELEGRAM_ALLOWED_IDS=...        # comma-separated Telegram user IDs allowed to use it
```

The chat model is the one seam that changes providers: swap these two lines and the
`base_url` in `agent/llm.py`. Composio, LangFuse, and Telegram are all optional —
leave their keys blank and those features simply switch off. For Telegram, get a
token from [@BotFather](https://t.me/BotFather), run `python main.py --telegram`,
message the bot once to learn your user ID, and add it to `TELEGRAM_ALLOWED_IDS`.

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
python main.py                     # interactive chat (Ctrl+C stops a running turn)
python main.py --resume            # resume the most recent conversation
python main.py --verbose           # show the full reasoning trace
python main.py --telegram          # run the Telegram gateway (chat from your phone)
python main.py "what is 47 * 89"   # one-shot
python evals/run_evals.py          # run the eval suite
```

## Project structure

```
main.py                      CLI entry point
agent/
  loop.py                    the agent loop + chat REPL
  llm.py                     LLM client (the provider seam)
  mcp_client.py              Composio MCP meta-router (1000+ apps)
  trace.py                   observability seam (--verbose · LangFuse)
  skills.py                  skill discovery / authoring
  tools/                     self-registering tool modules
    __init__.py              the @tool registry
    calculator.py · files.py · web_search.py · apple.py · skill_tools.py
  memory/
    embeddings.py            Gemini embeddings
    store.py                 vector memory (save / recall)
    session_store.py         conversation persistence
  gateway/
    telegram.py              Telegram messaging gateway
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
- **Frameworks belong around the loop, never inside it.** LangFuse (observability)
  and MCP (external apps via Composio) both attach at the edges — through the trace
  seam and the tool registry — while the reasoning loop stays hand-written. They are
  layered on *around* the loop, exactly where a framework should live.

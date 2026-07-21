# Mini Agent Harness — Roadmap

The "operating system" that wraps an LLM with a reasoning loop, tools, and
memory so it acts like a persistent agent instead of a one-turn chatbot. Built
raw (no framework — the harness *is* the framework), with a RAG-backed vector
store as its long-term memory.

## Architecture

```
   User
    │
    ▼
┌──────────────┐
│  Interface   │  CLI first, thin web UI later
└──────┬───────┘
       ▼
┌─────────────────────────────────────────────┐
│           AGENT LOOP  (orchestrator)         │
│   think → call tool → observe → repeat        │
│   until the model returns a final answer      │
└───┬──────────────┬───────────────┬───────────┘
    │              │               │
┌───▼─────┐  ┌─────▼──────┐  ┌─────▼─────────┐
│  LLM     │  │   Tool     │  │   Memory      │
│  client  │  │  registry  │  │  short + long │
│ (Gemini) │  │            │  │               │
└──────────┘  └─────┬──────┘  └─────┬─────────┘
                    │               │
              ┌─────▼─────┐   ┌─────▼──────────┐
              │  Tools:    │   │  Supabase       │
              │  search,   │   │  pgvector =     │
              │  file r/w  │   │  long-term      │
              └───────────┘   │  memory + state │
                              └─────────────────┘
       every step ──▶ Observability (structured logs)
```

## Components

| Component | Job | Maps to |
|---|---|---|
| Agent loop | The reason→act→observe cycle; the heart | The Tavily warm-up, made multi-turn |
| LLM client | Model interface, swappable | Gemini via OpenAI-compatible endpoint |
| Tool registry | Register / dispatch tools by name | The tool schema pattern |
| Memory | Short-term (conversation) + long-term (vector recall) | RAG, repurposed |
| Persistence | Save / load state across sessions | Supabase tables |
| Observability | Trace every thought + tool call | New — makes the loop visible |

## Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python, raw | The harness is the framework; no LangGraph |
| LLM | Gemini (`gemini-2.5-flash-lite`) via OpenAI-compatible endpoint | Known; higher daily quota |
| Memory + state | Supabase (pgvector) | Reuse existing setup |
| Tools | Python functions; Tavily (search), file I/O | Tavily already wired |
| Interface | CLI → optional Next.js UI | Reuse frontend skills later |
| Observability | Structured logging → optional LangFuse | Makes demos legible |

## Milestones (each one is small and runnable)

| # | Milestone | Done when… |
|---|---|---|
| M1 | The agent loop | Give it a task; it calls a tool, observes, loops until a final answer |
| M2 | Tool registry | Agent chooses among several registered tools (search / file-read / file-write) |
| M3 | Short-term memory | Full conversation carried across turns; multi-step tasks work |
| M4 | Long-term memory (RAG) | Stores facts as embeddings, retrieves relevant memory each turn |
| M5 | Persistence | Restart the program and it still remembers you |
| M6 | Skills / learning | Agent writes learned procedures to a store and recalls them — **⚠ scope is deliberately undecided; discuss and pin down BEFORE starting M6** (see note below) |
| M7 | Observability | A `--verbose` trace showing every thought → tool → result |
| M8 | Polish + demo | Clean CLI, README with architecture, small eval suite + demo |

Spine = M1–M4. After memory (M4) it's a genuine harness; M5–M8 make it
persistent, legible, and portfolio-ready.

> **⚠ M6 checkpoint — do not skip.** "Skills / learning" is the vaguest
> milestone here and could mean several very different systems. **Stop and
> design it before writing any M6 code.** Useful prior art to read at that
> point: Hermes Agent's `agent/curator.py`, `agent/learning_graph.py` and
> `agent/skill_*.py` (local clone at `~/Desktop/Projects/hermes-agent-os-63815/`),
> plus the `agentskills.io` open standard it implements.

## File layout, by milestone

A sketch, not a contract — adjust as the build teaches us better. The rule: a
file appears only in the milestone that needs it, so the folder never holds a
file I can't explain.

```
oajan-agent/
├── main.py                  # CLI entry point                    M1
├── config.py                # loads .env, model names, max_steps M1
├── agent/
│   ├── loop.py              # think → tool → observe → repeat    M1  ★
│   ├── llm.py               # Gemini client (swappable shape)    M1
│   ├── tools/
│   │   ├── __init__.py      # THE REGISTRY — name → fn + schema  M2
│   │   ├── calculator.py    # zero-quota tool for debugging      M2
│   │   ├── web_search.py    # Tavily                             M1
│   │   └── files.py         # read / write                       M2
│   ├── memory/
│   │   ├── short_term.py    # message buffer                     M3
│   │   ├── long_term.py     # Supabase pgvector recall           M4
│   │   └── embeddings.py    # gemini-embedding-001, 1536 dims    M4
│   ├── prompts/
│   │   └── system.txt       # prompt pulled out of the code      M2
│   ├── skills.py            # learned procedures                 M6
│   └── trace.py             # structured logging, --verbose      M7
├── evals/                   # small eval suite                   M8
├── .env · requirements.txt · README.md
└── ROADMAP.md · CONTEXT.md
```

**M1 stays flat.** One `agent.py` in the root, one tool. The split into the tree
above happens at M2, when a second tool makes the single file genuinely
uncomfortable — so the structure is *felt* before it's adopted.

Deliberately not included (from the common "agent folder structure" templates):
`planner.py` / `executor.py` / `workflows/` belong to a plan-and-execute
architecture and duplicate the ReAct loop's job; multiple `llm/providers/*`
files when only Gemini is used; an `api/` layer (CLI first); and a `config.yaml`
alongside `settings.py` — `.env` plus one `config.py` is enough.

## Out of scope (prevents ballooning)

Multi-agent orchestration · gateway / WebSocket channels · multi-user auth ·
fine-tuning. All "someday", none needed to prove the concept.

## Phase 2 — frameworks, after the harness works

Not part of M1–M8. Parked here so it stops taking up working memory.

**The rule:** frameworks go at the layers *around* the loop, never inside it.
Observability, evals and serving are things nobody hand-rolls in production, so
using real tools there reads as judgement. The loop itself stays raw — handing
orchestration to a framework would delete the whole point of the project.

| # | Add | Where it attaches | Why it's worth doing |
|---|---|---|---|
| P1 | **LangFuse** | On top of the M7 tracing seam | Shows agents need production observability, not `print()` |
| P2 | **Eval harness** (plain pytest + a fixed task set is enough) | Extends M8 | Most portfolio agents have zero evals; "I measure my agent" is the strongest claim here |
| P3 | **MCP** — expose the M2 tool registry over the protocol | Wraps `agent/tools/` | Small, contained, and current; the registry already has the right shape |
| P4 | FastAPI layer over the CLI | Optional | Cheap — already known from the RAG project |

**Implication for M7 (decide early):** keep every trace call in a single
`trace.py` seam instead of scattering `print()` through the loop. Then adding
LangFuse is swapping one module's internals rather than surgery on the agent —
same reasoning as keeping `llm.py` a single swappable file.

**Not doing:** replacing the core loop with LangGraph/LangChain, or swapping the
pgvector memory for a managed vector framework. Both delete the parts that prove
the most.

## Guiding principle

Every milestone runs on its own, and long-term memory is a RAG vector store.
Build small, run it, understand it.

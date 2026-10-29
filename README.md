<div align="center">

```
 ██████╗ ███████╗███████╗██████╗
 ██╔══██╗██╔════╝██╔════╝██╔══██╗
 ██║  ██║█████╗  █████╗  ██████╔╝
 ██║  ██║██╔══╝  ██╔══╝  ██╔═══╝
 ██████╔╝███████╗███████╗██║
 ╚═════╝ ╚══════╝╚══════╝╚═╝
 ██████╗ ███████╗███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
 ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
 ██████╔╝█████╗  ███████╗█████╗  ███████║██████╔╝██║     ███████║
 ██╔══██╗██╔══╝  ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
 ██║  ██║███████╗███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
 ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
```

**Production-grade multi-agent research system with dual orchestration**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-40%20passed-brightgreen.svg)]()
[![OpenAI SDK](https://img.shields.io/badge/OpenAI-SDK-412991.svg)](https://platform.openai.com/)

[Getting Started](#getting-started) | [Architecture](#architecture) | [How It Works](#how-it-works) | [API Reference](#api-reference) | [Evaluation](#evaluation) | [Contributing](#contributing)

</div>

---

## What is Deep Research?

Deep Research is an **autonomous AI research agent** that takes a question, searches the web, scrapes and analyzes sources, and produces a comprehensive cited report — all without human intervention.

What makes it unique: it ships with **two orchestration modes** so you can study (and compare) the two dominant patterns in agentic AI:

| Mode | Who decides the next step? | Pattern |
|------|---------------------------|---------|
| **Code Orchestration** | Your Python code | Deterministic pipeline — same steps every time |
| **LLM Orchestration** | The LLM itself | Autonomous agent — the model picks tools and adapts |

Both modes use the same agents, tools, and guardrails. The only difference is *who's driving*.

---

## Key Features

- **6 Specialized Agents** — Clarifier, Planner, Analyst, Writer, Critic (with revision loop)
- **Smart Follow-up Questions** — LLM auto-decides if your query needs clarification before research begins
- **Free Web Search** — DuckDuckGo search (no API key needed beyond OpenAI)
- **Deep Content Extraction** — trafilatura for scraping + crawl4ai fallback for JS-heavy pages
- **Guardrails** — Prompt injection detection, topic safety checks, output quality validation, token budget management
- **Evaluation Framework** — 6 metrics + LLM-as-judge scoring for search relevance and topic coverage
- **Real-time UI** — FastAPI backend with SSE streaming + vanilla HTML/CSS/JS frontend
- **Multi-format Export** — Markdown, PDF, and email delivery
- **40 Unit Tests** — Models, agents, guardrails, tools, and API endpoints fully tested

---

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (HTML/CSS/JS)                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Query    │  │  Follow-up   │  │ Progress │  │   Report    │  │
│  │  Input    │  │  Questions   │  │ Tracker  │  │  + Export   │  │
│  └────┬─────┘  └──────▲───────┘  └────▲─────┘  └──────▲──────┘  │
│       │               │               │               │          │
│       │        Server-Sent Events (SSE) Stream         │          │
└───────┼───────────────┼───────────────┼───────────────┼──────────┘
        │               │               │               │
┌───────▼───────────────┴───────────────┴───────────────┴──────────┐
│                     FastAPI BACKEND (/api)                         │
│                                                                    │
│  POST /research ──► GET /stream ──► POST /clarify                 │
│  GET /report/pdf    GET /report/md   POST /email                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │    ORCHESTRATION LAYER     │
              │                           │
              │  ┌─────────┐ ┌─────────┐  │
              │  │  CODE   │ │   LLM   │  │
              │  │  MODE   │ │  MODE   │  │
              │  └────┬────┘ └────┬────┘  │
              └───────┼───────────┼───────┘
                      │           │
        ┌─────────────▼───────────▼─────────────┐
        │            AGENT LAYER                 │
        │                                        │
        │  ┌───────────┐  ┌──────────────────┐   │
        │  │ Clarifier │  │     Planner      │   │
        │  └───────────┘  └──────────────────┘   │
        │  ┌───────────┐  ┌──────────────────┐   │
        │  │  Analyst  │  │     Writer       │   │
        │  └───────────┘  └──────────────────┘   │
        │  ┌───────────┐                         │
        │  │  Critic   │  ◄── revision loop      │
        │  └───────────┘                         │
        └───────────────────┬────────────────────┘
                            │
        ┌───────────────────▼────────────────────┐
        │            TOOL LAYER                   │
        │                                         │
        │  ┌─────────────┐  ┌─────────────────┐  │
        │  │  DuckDuckGo │  │  trafilatura /   │  │
        │  │   Search    │  │  crawl4ai        │  │
        │  └─────────────┘  └─────────────────┘  │
        └───────────────────┬─────────────────────┘
                            │
        ┌───────────────────▼────────────────────┐
        │          GUARDRAILS LAYER               │
        │                                         │
        │  ┌──────────┐ ┌────────┐ ┌──────────┐  │
        │  │  Input   │ │ Token  │ │  Output  │  │
        │  │  Guard   │ │ Budget │ │  Guard   │  │
        │  └──────────┘ └────────┘ └──────────┘  │
        └─────────────────────────────────────────┘
```

### Code Orchestration — Data Flow

```
User Query
    │
    ▼
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│  Input   │────►│ Clarifier │────►│ Planner  │────►│ Search   │
│  Guard   │     │  Agent    │     │  Agent   │     │ (DDG×N)  │
└──────────┘     └───────────┘     └──────────┘     └────┬─────┘
                       │                                  │
                  (optional)                              ▼
                  follow-up                         ┌──────────┐
                  questions                         │ Scrape   │
                       │                            │ (×M URLs)│
                       ▼                            └────┬─────┘
                  User answers                           │
                                                         ▼
┌──────────┐     ┌───────────┐     ┌──────────┐    ┌──────────┐
│  Output  │◄────│  Critic   │◄─┬──│  Writer  │◄───│ Analyst  │
│  Guard   │     │  Agent    │  │  │  Agent   │    │  Agent   │
└────┬─────┘     └───────────┘  │  └──────────┘    └──────────┘
     │                │         │
     ▼           score < 7?     │
┌──────────┐     YES ───────────┘  (max 2 revision loops)
│  Export  │
│ PDF/Email│
└──────────┘
```

**Every step is deterministic.** Your code controls what happens, in what order, every time.

### LLM Orchestration — Data Flow

```
User Query
    │
    ▼
┌──────────┐
│  Input   │
│  Guard   │
└────┬─────┘
     │
     ▼
┌─────────────────────────────────────────┐
│        ORCHESTRATOR LLM                  │
│                                          │
│   System prompt + 9 tool definitions     │
│                                          │
│   ┌─────────────────────────────────┐    │
│   │     TOOL-CALLING LOOP           │    │
│   │     (max 25 iterations)         │    │
│   │                                 │    │
│   │  LLM decides ──► call tool      │    │
│   │       ▲              │          │    │
│   │       │              ▼          │    │
│   │       └──── tool result         │    │
│   │                                 │    │
│   │  Available tools:               │    │
│   │  • clarify_query                │    │
│   │  • plan_searches                │    │
│   │  • search_web                   │    │
│   │  • scrape_url                   │    │
│   │  • analyze_content              │    │
│   │  • write_report                 │    │
│   │  • critique_report              │    │
│   │  • revise_report                │    │
│   │  • report_status                │    │
│   └─────────────────────────────────┘    │
│                                          │
│   Safety limits:                         │
│   • 25 max iterations                    │
│   • 3 max consecutive failures           │
│   • 10 max search calls                  │
│   • 15 max scrape calls                  │
│   • Token budget enforcement             │
└──────────────────────────────────────────┘
     │
     ▼
  Final report (LLM returns without tool call)
```

**The LLM has full autonomy.** It can skip steps, reorder them, do extra searches after finding gaps, or take novel paths. Guardrails ensure it can't loop forever or burn your budget.

---

## Project Structure

```
deep_research/
│
├── config.py                          # Central config (Pydantic Settings, env vars)
├── logging_config.py                  # Structured logging with structlog
│
├── models/                            # Data contracts (Pydantic v2)
│   ├── common.py                      #   TokenUsage, ValidationResult
│   ├── query.py                       #   ResearchQuery, ClarificationResult
│   ├── search.py                      #   SearchPlan, SearchResult, ScrapedContent
│   ├── analysis.py                    #   AnalysisFindings (themes, gaps, contradictions)
│   ├── report.py                      #   ReportDraft, CritiqueResult, FinalReport
│   └── session.py                     #   ResearchSession, SessionStatus, events
│
├── agents/                            # Agent implementations
│   ├── base.py                        #   BaseAgent (template method pattern)
│   ├── clarifier.py                   #   Decides if follow-ups needed
│   ├── planner.py                     #   Creates search strategy
│   ├── analyst.py                     #   Synthesizes findings
│   ├── writer.py                      #   Writes + revises report
│   └── critic.py                      #   Scores quality (5 dimensions, 0-10)
│
├── tools/                             # External tool integrations
│   ├── search_tool.py                 #   DuckDuckGo search with rate limiting
│   ├── scrape_tool.py                 #   trafilatura + crawl4ai fallback
│   └── tool_registry.py              #   Converts tools → OpenAI function schemas
│
├── orchestration/                     # The two orchestration engines
│   ├── base.py                        #   Abstract base with SSE emission
│   ├── code_orchestrator.py           #   Deterministic 10-step pipeline
│   └── llm_orchestrator.py            #   LLM-controlled tool-calling loop
│
├── guardrails/                        # Safety & quality
│   ├── input_guard.py                 #   Injection detection, topic safety, length
│   ├── output_guard.py                #   Citation verification, quality thresholds
│   └── token_budget.py                #   Per-session token tracking & limits
│
├── services/                          # Infrastructure
│   ├── llm_client.py                  #   OpenAI SDK wrapper (retry, structured outputs)
│   ├── pdf_service.py                 #   Markdown → PDF (weasyprint)
│   └── email_service.py               #   SMTP email delivery
│
├── api/                               # FastAPI backend
│   ├── main.py                        #   App creation, CORS, static mount
│   ├── dependencies.py                #   Dependency injection
│   ├── session_store.py               #   In-memory session + event queues
│   └── routes/
│       ├── health.py                  #   GET /api/health
│       └── research.py                #   All research endpoints + SSE
│
├── frontend/                          # Web UI (vanilla, no build step)
│   ├── index.html                     #   Single-page app shell
│   ├── css/styles.css                 #   Light/dark themes, editorial design
│   └── js/app.js                      #   SSE client, state machine, DOM
│
├── evals/                             # Evaluation framework
│   ├── runner.py                      #   Executes test cases, collects metrics
│   ├── metrics.py                     #   6 metric calculators
│   ├── judges.py                      #   LLM-as-judge scoring
│   └── datasets/
│       └── research_queries.json      #   5 curated eval cases
│
├── tests/                             # Test suite (40 tests)
│   ├── conftest.py                    #   Shared fixtures, mock LLM client
│   ├── test_models.py                 #   Pydantic model validation
│   ├── test_agents.py                 #   Agent execution with mocked LLM
│   ├── test_guardrails.py             #   Guard validation + token budget
│   ├── test_tools.py                  #   Tool wrappers with mocked HTTP
│   └── test_api.py                    #   FastAPI endpoint integration tests
│
├── scripts/
│   └── run_evals.py                   #   CLI evaluation runner
│
├── pyproject.toml                     #   Dependencies & project metadata
├── Makefile                           #   Shortcuts: make run, make test, make eval
├── .env.example                       #   Environment variable template
└── .gitignore
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- An OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/deep-research.git
cd deep-research

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### Quick Start

```bash
# Start the server
make run
# or: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Open http://localhost:8000 in your browser
```

That's it. Enter a research question, pick an orchestration mode, and hit **RESEARCH**.

### Configuration

All settings are in `.env` with the `DR_` prefix. Key options:

```bash
# Required
DR_OPENAI_API_KEY=sk-...

# Models
DR_DEFAULT_MODEL=gpt-4o-mini       # Agents (cheap, fast)
DR_WRITING_MODEL=gpt-4o            # Writer agent (quality)
DR_ORCHESTRATOR_MODEL=gpt-4o       # LLM orchestrator (smart)

# Research parameters
DR_MAX_SEARCHES=5                   # Number of search queries
DR_MAX_SCRAPE_URLS=10               # Max pages to scrape
DR_MAX_FOLLOW_UP_QUESTIONS=3        # Clarification questions
DR_MAX_REVISIONS=2                  # Writer ↔ Critic loops

# Token budget
DR_MAX_TOKENS_PER_SESSION=100000    # Per-research session limit

# Email (optional)
DR_EMAIL_ENABLED=false
DR_EMAIL_ADDRESS=you@example.com
DR_EMAIL_SMTP_SERVER=smtp.gmail.com
DR_EMAIL_APP_PASSWORD=your-app-password
```

---

## How It Works

### 1. Query Validation
Every query passes through the **Input Guard** which checks for:
- Length constraints (5–2000 characters)
- Prompt injection patterns (regex-based detection)
- Topic safety (harmful content filtering)

### 2. Smart Clarification
The **Clarifier Agent** analyzes query ambiguity across 5 dimensions (ambiguity, scope, recency, perspective, depth). It auto-decides whether to ask follow-up questions — most clear queries skip this step entirely.

### 3. Search Planning
The **Planner Agent** generates a prioritized search strategy: broad overview queries first, then specific sub-topics, contrasting viewpoints, and recent developments.

### 4. Web Search & Scraping
- **DuckDuckGo** search via `duckduckgo-search` (free, no API key)
- **trafilatura** extracts clean text from web pages
- **crawl4ai** handles JavaScript-heavy pages as fallback
- Rate-limited and parallelized with configurable concurrency

### 5. Analysis
The **Analyst Agent** synthesizes all scraped content into structured findings: key claims, themes, contradictions between sources, knowledge gaps, and per-source quality assessment.

### 6. Report Writing & Review
The **Writer Agent** produces a comprehensive markdown report (1500+ words, inline citations). The **Critic Agent** scores it on 5 dimensions (accuracy, completeness, structure, clarity, citations). If the score is below 7/10, the report goes back for revision (up to 2 loops).

### 7. Output Validation
The **Output Guard** verifies:
- All cited URLs were actually scraped (catches hallucinated sources)
- Minimum word count and heading structure
- Source diversity

### 8. Export
Reports are available as rendered HTML in the UI, downloadable Markdown, downloadable PDF, or emailed directly.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/research` | Start a research session. Body: `{"query": "...", "mode": "code\|llm"}` |
| `GET` | `/api/research/{id}/stream` | SSE event stream for real-time updates |
| `POST` | `/api/research/{id}/clarify` | Submit answers to follow-up questions |
| `GET` | `/api/research/{id}` | Get full session state |
| `GET` | `/api/research/{id}/report/md` | Download report as Markdown |
| `GET` | `/api/research/{id}/report/pdf` | Download report as PDF |
| `POST` | `/api/research/{id}/email` | Email the report. Body: `{"to": "email@example.com"}` |
| `GET` | `/api/health` | Health check |

### SSE Event Types

```
event: status     → {"message": "Planning 5 searches...", "status": "planning"}
event: clarify    → {"questions": [{"question": "...", "purpose": "..."}]}
event: progress   → {"message": "Searched 3/5", "current": 3, "total": 5}
event: complete   → {"report": { ...FinalReport... }}
event: error      → {"message": "...", "recoverable": true|false}
```

---

## Evaluation

The eval framework measures 6 dimensions of quality:

| Metric | What it measures | How |
|--------|-----------------|-----|
| Search Relevance | Are search results on-topic? | LLM-as-judge (0-10) |
| Scrape Success Rate | % of URLs successfully scraped | `successes / attempts` |
| Report Quality | Overall report score | Critic agent's 5-dimension average |
| Citation Accuracy | Are cited URLs real sources? | Cross-reference vs scraped URLs |
| Topic Coverage | Does the report cover expected topics? | LLM-as-judge per-topic |
| Token Efficiency | How much budget was used? | `1 - (used / max)` |

### Running Evals

```bash
# Run all eval cases in code orchestration mode
python scripts/run_evals.py --mode code

# Run in LLM orchestration mode
python scripts/run_evals.py --mode llm

# Run specific cases file
python scripts/run_evals.py --mode code --cases path/to/cases.json
```

---

## Testing

```bash
# Run all 40 tests
make test
# or: python -m pytest tests/ -v

# Run specific test modules
python -m pytest tests/test_models.py -v
python -m pytest tests/test_guardrails.py -v
python -m pytest tests/test_agents.py -v
python -m pytest tests/test_api.py -v
python -m pytest tests/test_tools.py -v
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| LLM | OpenAI SDK (raw `openai` package) | Direct API control, structured outputs, tool calling |
| Search | duckduckgo-search | Free, no API key, rate-limited |
| Scraping | trafilatura + crawl4ai | Best-in-class extraction accuracy |
| Backend | FastAPI + SSE | Async, real-time streaming, auto-generated docs |
| Frontend | Vanilla HTML/CSS/JS | Zero build step, fully teachable |
| PDF | weasyprint | High-quality markdown-to-PDF |
| Validation | Pydantic v2 | Type-safe data contracts + OpenAI structured outputs |
| Config | pydantic-settings | Type-safe env var management |
| Logging | structlog | Structured JSON logging |
| Tests | pytest + pytest-asyncio | Async-native test runner |

---

## Understanding the Two Orchestration Modes

This project exists to teach the two fundamental patterns in agentic AI. Here's the core difference:

### Code Orchestration (Deterministic)
```python
# YOU decide the pipeline
results = await search(plan)          # Step 1: always search
content = await scrape(results)       # Step 2: always scrape
findings = await analyze(content)     # Step 3: always analyze
report = await write(findings)        # Step 4: always write
critique = await review(report)       # Step 5: always review
```

**Pros:** Predictable, debuggable, reproducible. Same input = same flow.
**Cons:** Can't adapt. If analysis reveals a gap, it won't go back and search more.

### LLM Orchestration (Autonomous)
```python
# THE LLM decides the pipeline
while not done:
    action = await llm.decide(context, tools)  # LLM chooses
    result = await execute(action)              # We execute
    context.append(result)                      # LLM sees result
```

**Pros:** Adaptive. Can search more after finding gaps, skip irrelevant steps, take novel paths.
**Cons:** Less predictable, harder to debug, may waste tokens on unnecessary steps.

**Which is better?** Neither — they serve different needs. Production systems often use code orchestration for reliability with LLM orchestration for specific sub-tasks that benefit from flexibility.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Commit (`git commit -m "Add your feature"`)
6. Push (`git push origin feature/your-feature`)
7. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built to learn. Built to teach. Built to ship.

**If this helped you understand agentic AI, give it a star.**

</div>

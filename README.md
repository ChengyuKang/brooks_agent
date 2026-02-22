# AI Brooks RAG Trading Agent (Practice Project)

**Status:** Research prototype project  
**Goal:** Explore how to combine feature engineering + RAG + LLM reasoning to produce a structured, explainable trading plan inspired by Al Brooks' price-action framework.

> This project is **not** a profitable system and is expected to fail as a fully automated strategy in real markets.  
> The focus is engineering and research process, not guaranteed returns.

## What This Project Is

This repository builds a modular AI trading assistant prototype for intraday workflows (currently focused on 5-minute bars for SPY/ES-style instruments). It:

- Converts raw OHLCV into numeric `MarketSnapshot` features
- Use regime routing to select which book(s)/retrieval strategy to use based on the current market regime (trend vs range vs reversal)
- Uses RAG over Brooks book chunks to retrieve relevant rules/examples
- Injects a stable doctrine layer (`xinfa`) for consistency
- Produces strict JSON decision output with citations

Key idea:

- Python is the **eyes**: hard evidence (features, levels, candidate prices)
- RAG is the **playbook**: grounded domain knowledge retrieval
- LLM (optional) is the **analyst**: structured reasoning and explanation

## Why This Is Portfolio-Relevant

Even if it does not produce robust trading returns, it demonstrates practical engineering capabilities:

- Feature engineering pipeline with explicit schema and reproducible inputs
- Long-document RAG pipeline (PDF cleaning -> chunking -> metadata -> embedding -> retrieval)
- Decision orchestration (routing, query planning, token budgeting, citation grounding)
- Strict structured output design for evaluation and automation-readiness
- Realistic handling of uncertainty, ambiguity, and risk constraints

## High-Level Workflow
<img width="3052" height="5800" alt="image" src="https://github.com/user-attachments/assets/c27bbe8d-925e-4d62-b14b-687fdc15571d" />

```text
Raw OHLCV (CSV/API)
   ↓
Feature Engineering (MarketSnapshot)
   ↓
DecisionRequest (levels + candidates + sizing)
   ↓
RAG Retrieval (book routing + metadata filters + neighbors)
   ↓
Static Xinfa Injection (core + regime reinforcement)
   ↓
(Optional) LLM Decision Engine
   ↓
Decision JSON (action + entry/SL/TP/size + citations)
```

## Module Breakdown

### 1) Feature Engineering (`ai_brooks_features/`)

Produces `MarketSnapshot` as a compact continuous representation of market state:

- Bar anatomy: body/tails/close position
- Local trend: EMA slope, micro-channel, pullback depth
- Swing structure: double top/bottom, wedge-related signals
- Range structure: overlap, tests, breakout-failure behavior
- Reversal signals: climax and H1/H2/L1/L2 style scores
- Regime scores: trend vs range vs reversal setup

Design choice: prefer mostly continuous scores (0-1) over brittle booleans.

Primary entrypoint:

- `ai_brooks_features/builder.py`

### 2) Xinfa Doctrine Layer (`ai_brooks_knowledge/xinfa_core/`)

Large book knowledge is distilled into stable doctrine documents:

- A: Worldview & Risk
- B: Trend
- C: Trading Range
- D: Reversal
- E: Psychology & Routines
- F: Feature Glossary

Usage pattern:

- Always inject A + E + F
- Add B/C/D based on detected regime

This improves consistency and reduces context drift.

### 3) Knowledge Ingestion + Vectorization (`ai_brooks_knowledge/` + `scripts/build_vector_db.py`)

Pipeline:

1. Extract text from PDFs
2. Clean/de-noise (headers, footers, index/TOC artifacts, wrapped lines)
3. Chunk and attach metadata (`book`, `part/chapter`, `pages`, `chunk_id`, `seq`)
4. Embed and store in Chroma

Key files:

- `ai_brooks_knowledge/ingest_pipeline.py`
- `ai_brooks_knowledge/ingest_books.py`
- `scripts/build_vector_db.py`

### 4) RAG Orchestration (`ai_brooks_rag/`)

- `router.py`: regime-aware retrieval planning
- `rewrite.py`: multi-intent query generation (`pattern`, `regime`, `management`)
- `decision_mapper.py`: decision request -> retrieval plan adapter
- `retriever.py`: retrieval + dedup + neighbor expansion + token clipping
- `context_builder.py`: builds final model messages and output schema instructions
- `llm_client.py`: optional model call and strict JSON parse

### 5) Decision Layer (`decision_types.py`)

Builds `DecisionRequest` with execution-relevant fields:

- `snapshot`: features from `MarketSnapshot`
- `account`: risk constraints (per-trade / daily)
- `position`: current position status
- `instrument`: tick size / point value / quantity unit
- `recent_bars`: local bar window for concrete pricing
- `levels`: prior day levels, opening range, EMA/VWAP, swing anchors
- `order_candidates`: Python-generated entry/SL/TP candidates
- `sizing`: risk budget -> suggested quantity

Important design: price levels and order candidates are computed in Python to reduce hallucination risk.

## Retrieval Strategy (RAG-Focused)

This project directly addresses common RAG failure modes:

- Ambiguity (trend/range/reversal overlap):
  - Regime-based routing
  - Multi-book retrieval when uncertainty is high
- Chunk fragmentation:
  - Neighbor expansion via stable per-book `seq`
- Over-retrieval:
  - Token budgeting and final-K caps
- Relevance drift:
  - Mandatory citation-oriented output format

## Typical Output (When LLM Decision Is Enabled)

Strict JSON fields include:

- `action`: `WAIT | ENTER_LONG | ENTER_SHORT | MANAGE | EXIT`
- `entry`: type + price + trigger
- `stop_loss`: price + reason
- `take_profit`: one or more targets with size fractions
- `position_size`: quantity + cash risk + risk-R
- `reasons`, `trigger_conditions`, `invalidation_conditions`, `next_bar_plan`
- `citations`: grounded references

Citation format:

- Book chunks: `[[BOOK:BOOK|pSTART-END|CHUNK_ID|seq=S]]`
- Xinfa docs: `[[XINFA:FILENAME.md]]`

## What Is Out of Scope (Current Stage)

- Not a production trading system
- No profitability claim
- No broker execution integration
- No complete walk-forward framework with full cost/slippage modeling
- No guarantee that pattern logic generalizes across regimes/instruments

## Quick Start Workflow

### 0) Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install langchain-chroma pymupdf tiktoken
```

Create `.env`:

```dotenv
OPENAI_API_KEY=your_api_key
```

### 1) Build / Refresh Chroma Vector DB

```powershell
python scripts\build_vector_db.py --reset
python scripts\test_search.py
```

### 2) Inspect DecisionRequest (Pricing Inputs + Candidates)

```powershell
python scripts\test_decision_request_fields.py --index 4570 --save
```

### 3) Inspect Context Sent to LLM (No LLM Call)

```powershell
python scripts\inspect_decision_context.py --dr data\tmp\dr_4570.json --save-messages
```

### 4) Optional Full Decision Run (LLM Enabled)

```powershell
python scripts\run_decision.py --dr data\tmp\dr_4570.json --model gpt-5
```

## Tech Stack

### Core Language and Data

- Python
- pandas, numpy

### Market Feature Engineering

- Custom indicators and engineered schema (`MarketSnapshot`)

### Document and Knowledge Pipeline

- PyMuPDF (`fitz`) for PDF extraction
- Custom text cleaning, structure parsing, chunking, metadata tracking

### Retrieval and Vector Store

- Chroma (local persistence)
- LangChain wrappers (`langchain-chroma`, `langchain-openai`, `langchain-core`, `langchain-community`)

### Embeddings and Optional LLM

- OpenAI embeddings (`text-embedding-3-small`)
- Optional OpenAI model inference for decision JSON output

### Orchestration

- Custom router/retriever with metadata filters, neighbor expansion, and token budgeting

## Failure Modes and Realism

This project is expected to fail as a money-printing bot for structural reasons:

- Price action interpretation is subjective
- Regime ambiguity is frequent
- Slippage/fees/latency dominate intraday edges
- Pattern detector overfitting risk is high
- LLMs can appear confident when uncertain

Therefore the focus is a reproducible, inspectable research pipeline rather than return promises.

## Roadmap (Portfolio-Friendly)

- Retrieval evaluation harness (chapter/topic hit quality)
- Decision consistency checks (schema compliance + citation coverage)
- Paper-trading simulator with slippage/fees
- Optional reranking for ambiguous regimes
- Better magnet/measured-move target logic
- Lightweight UI for timeline + citations review

## Repository Snapshot

```text
brooks_agent/
  ai_brooks_features/
  ai_brooks_knowledge/
  ai_brooks_rag/
  ai_brooks_decision/
  scripts/
  decision_types.py
  data_loader.py
  data/
```

---

If you are evaluating this project as a portfolio artifact, prioritize the architecture, interfaces, testability, and failure analysis over short-term trading performance.

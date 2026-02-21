# brooks_agent

AI Brooks RAG Trading Agent (Research / Portfolio Project)

Status: Research prototype / portfolio project
Goal: Explore how to combine feature engineering + RAG + LLM reasoning to produce a structured, explainable trading plan inspired by Al Brooks’ price-action framework.
Note: This project is not a proven profitable system and is expected to fail as a fully automated trading strategy in real markets. The point is the engineering + research process, not guaranteed returns.

What this project is

This repo builds a modular “AI trading assistant” prototype for intraday trading (initially 5-minute bars on SPY/ES style instruments). It:

Converts raw OHLCV data into a numeric MarketSnapshot (continuous features).

Uses RAG over Al Brooks’ Trading Price Action books to retrieve relevant rules/examples.

Injects a “global doctrine” (xinfa) as a stable decision framework.

Produces a strict JSON decision output: whether to trade, and if yes, with entry / stop / targets / sizing, plus citations to sources.

Key idea:

Python is the “eyes” (hard evidence: continuous features + price levels).

RAG provides the “playbook” (book knowledge retrieval).

The LLM (optional) is the “analyst” (reasoning + structured plan + explanation).

Why it’s interesting (portfolio angle)

Even if this cannot reliably make money, it demonstrates real-world skills hiring teams care about:

Building a feature engineering pipeline with reproducible schemas and testability.

Designing a RAG system for long-form PDFs (cleaning → chunking → metadata → embeddings → retrieval).

Implementing a decision orchestration layer (routing, retrieval planning, token budgeting, citation tracking).

Creating structured outputs suitable for evaluation and future automation.

Thinking realistically about failure modes, uncertainty, ambiguity, and risk constraints.

High-level architecture
Raw OHLCV (CSV/API)
   ↓
Feature Engineering (MarketSnapshot)
   ↓
DecisionRequest (adds pricing levels + sizing candidates)
   ↓
RAG Retrieval (books + metadata filters + neighbor expansion)
   ↓
Static Xinfa Injection (core + regime reinforcement)
   ↓
(Optionally) LLM Decision Engine
   ↓
Decision JSON (entry/SL/TP/size + citations)
Core modules
1) Feature Engineering (ai_brooks_features/)

Produces MarketSnapshot (a compact numeric summary of the last bar + local context):

bar anatomy (body/tails/close position)

local trend state (EMA slope, micro-channel, pullback depth)

swing structure (double top/bottom, wedge)

range structure (overlap, tests, breakout failure)

reversal signals (climax, final flag, High/Low 1/2 scores)

regime scores (trend vs range vs reversal setup)

Design choice: features are mostly continuous scores (0–1) rather than fragile “pattern = True/False”.

2) Knowledge distillation (“Xinfa”) (ai_brooks_knowledge/xinfa_core/)

The three Brooks books are large and repetitive. Instead of relying only on raw retrieval, the project distills a set of stable “doctrine documents” (xinfa), split into modules:

A: Worldview & Risk (core principles)

B: Trend

C: Trading Range

D: Reversal

E: Psychology & Routines

F: Feature Glossary

Usage:

Always inject A + E + F as stable constraints.

Inject B/C/D depending on the detected regime.

This prevents the agent from “forgetting” core principles and improves consistency.

3) RAG pipeline (ai_brooks_knowledge/ + vector DB)

Steps:

Extract text from PDFs

Clean and de-noise (headers/footers, TOC/index pages, broken lines)

Chunk with metadata (book, chapter/part, pages, sequence id)

Embed and store in Chroma

Retrieve using:

regime routing (TREND / RANGE / REVERSAL)

multiple query intents (pattern / regime / management)

neighbor expansion (seq ± N) to restore lost context

token budgeting to keep context usable

4) Decision layer (decision_types.py + ai_brooks_rag/)

The system builds a DecisionRequest that includes:

MarketSnapshot

account constraints (max risk per trade/day)

position state (if already in a trade)

instrument spec (tick size, point value)

recent bars window (for exact price references)

key price levels (yesterday high/low, opening range, EMA/VWAP, swing points)

order candidates (Python-generated candidate entry/SL/TP levels)

sizing advice (risk budget → suggested quantity)

Important: price levels and order candidates are computed in Python to reduce hallucinations.
The LLM (when used) is expected to choose among candidates and justify with citations.

Retrieval strategy (RAG focus)

This project explicitly targets common RAG failure modes:

Ambiguity: trend vs range vs reversal setups overlap frequently.

Solution: regime-based routing + multi-book retrieval when uncertain.

Chunk fragmentation: important explanations often span adjacent chunks.

Solution: neighbor expansion using a stable seq per book.

Over-retrieval: too many chunks reduces model focus.

Solution: token budgets + final-k caps + optional compression layer.

Relevance drift: a “pretty” answer is useless if not grounded.

Solution: mandatory citations for rules used in decisions.

What it outputs (when decision engine is enabled)

A strict JSON object such as:

action: WAIT / ENTER_LONG / ENTER_SHORT / MANAGE / EXIT

entry: order type + price + trigger condition

stop_loss: price + reason

take_profit: one or more targets + size fractions + reasons

position_size: quantity + cash risk + R risk

reasons: concise bullets

invalidation_conditions: when the setup fails

citations: list of [[BOOK:...]] and [[XINFA:...]]

What’s intentionally out of scope (for now)

This is not a production trading system.

No claim of profitability.

No robust walk-forward optimization, full evaluation harness, or transaction cost modeling yet.

No broker execution integration.

No guarantees about pattern correctness or market generalization.

How to run (typical workflow)
1) Build vector DB (books → chunks → embeddings → Chroma)
python scripts/build_vector_db.py --reset
python scripts/test_search.py
2) Inspect DecisionRequest (pricing inputs / candidates)
python -m scripts.test_decision_request_fields --index 4570 --save
3) Inspect what would be sent to the LLM (no LLM calls)
python -m scripts.inspect_decision_context --dr data/tmp/dr_XXXX.json --save-messages
4) (Optional) Run the full decision pipeline (LLM enabled)

This step is optional and may not be enabled by default in the repo.

Failure modes & realism

This project is expected to fail as a money-printing bot for multiple reasons:

Price action is subjective; translating it into features loses information.

Regime ambiguity is common; “right answer” is often probabilistic.

Slippage/fees/latency matter, especially for intraday.

Overfitting risk is high when designing pattern detectors.

LLMs can sound confident even when uncertain.

Therefore: the focus is on the engineering + research process and building a reproducible, inspectable pipeline.

Tech stack (high level)

Python (pandas, numpy)

Feature pipeline (custom indicators + engineered schema)

PDF processing + cleaning + chunking

Vector DB: Chroma (local persistence)

Embeddings: OpenAI embeddings (configurable)

RAG orchestration: custom router/retriever + metadata filters

Optional LLM decision engine: OpenAI API (configurable)

Roadmap (portfolio-friendly)

Add evaluation harness:

retrieval quality metrics (hit rate by chapter/topic)

decision consistency checks (schema validation, citation coverage)

paper-trading simulator with slippage/fees

Add optional reranking layer for ambiguous regimes

Add better “magnet” detection and measured-move targets

Add UI for reviewing decisions (timeline + citations)

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple

from ai_brooks_decision.xinfa_loader import load_xinfa_docs, pick_xinfa_set, XinfaDoc, approx_tokens

def _book_citation(meta: Dict[str, Any]) -> str:
    book = meta.get("book", "UNK")
    ps = meta.get("page_start", "?")
    pe = meta.get("page_end", "?")
    cid = meta.get("chunk_id", "UNK")
    seq = meta.get("seq", "?")
    return f"BOOK:{book}|p{ps}-{pe}|{cid}|seq={seq}"

def format_xinfa_block(d: XinfaDoc) -> str:
    return f"### [[{d.doc_id}]]\n{d.text}\n"

def format_book_doc_block(doc) -> str:
    meta = doc.metadata or {}
    cite = _book_citation(meta)
    header = f"### [[{cite}]]\n"
    # 建议把 part/chapter 放在 header 里（可追溯性强，且不污染 embedding）
    part = meta.get("part") or ""
    chapter = meta.get("chapter") or ""
    extra = []
    if part: extra.append(f"part={part}")
    if chapter: extra.append(f"chapter={chapter}")
    if extra:
        header += f"_meta: {', '.join(extra)}_\n"
    return header + doc.page_content.strip() + "\n"

def build_decision_messages(
    decision_request: Dict[str, Any],
    plan: Any,
    retrieved_docs: List[Any],
    xinfa_root: str = "ai_brooks_knowledge/xinfa_core",
    system_xinfa_budget: int = 2500,
    static_xinfa_budget: int = 3000,
    dynamic_budget: Optional[int] = None,
) -> List[Dict[str, str]]:
    """
    返回 messages: [{"role":"system","content":...}, {"role":"user","content":...}, ...]
    """
    all_xinfa = load_xinfa_docs(xinfa_root)
    sys_docs, static_docs = pick_xinfa_set(
        all_xinfa,
        plan_books=getattr(plan, "books", []) or [],
        system_budget=system_xinfa_budget,
        static_budget=static_xinfa_budget,
    )

    # dynamic budget 默认用 plan.token_budget
    dyn_budget = int(dynamic_budget or getattr(plan, "token_budget", 6000))

    # 组装 dynamic chunks（按顺序取，直到预算）
    dyn_blocks = []
    used = 0
    for d in retrieved_docs:
        block = format_book_doc_block(d)
        t = approx_tokens(block)
        if used + t > dyn_budget:
            continue
        dyn_blocks.append(block)
        used += t

    # System：固定原则（A+E+F） + 输出格式要求
    sys_rules = """You are an Al Brooks style price-action trading decision engine.
You must:
- Never invent citations or facts not present in provided context.
- Use the provided sources as authoritative. If information is missing, say so and choose WAIT or a conservative plan.
- Output STRICT JSON only (no markdown). Follow the required schema exactly.
- Provide numeric entry/stop/targets only if decision_request contains sufficient price levels/tick_size; otherwise ask for missing fields and return WAIT.

Citation format:
- For book chunks, cite as: [[BOOK:BOOK|pSTART-END|CHUNK_ID|seq=S]]
- For xinfa docs, cite as: [[XINFA:FILENAME.md]]

When you justify a rule, include at least 1 relevant citation in the `citations` field.
"""

    sys_xinfa_text = "\n\n".join(format_xinfa_block(d) for d in sys_docs)

    system_message = sys_rules + "\n\n" + sys_xinfa_text

    # Static context：regime 强化 + 通用补强（不放 system，避免 system 过长）
    static_xinfa_text = "\n\n".join(format_xinfa_block(d) for d in static_docs)

    # Context message：static xinfa + dynamic retrieved chunks
    context_message = (
        "=== STATIC XINFA (regime reinforcement + common playbooks) ===\n"
        + static_xinfa_text
        + "\n\n=== DYNAMIC BOOK CHUNKS (retrieved) ===\n"
        + "\n\n".join(dyn_blocks)
    )

    # User message：DecisionRequest + 强制输出 schema
    decision_schema = {
        "action": "WAIT | ENTER_LONG | ENTER_SHORT | MANAGE | EXIT",
        "entry": {
            "type": "stop | limit | market | none",
            "price": "number|null",
            "trigger": "string",
        },
        "stop_loss": {
            "price": "number|null",
            "reason": "string",
        },
        "take_profit": [
            {"price": "number|null", "size_frac": "0-1", "reason": "string"}
        ],
        "position_size": {
            "units": "contracts|shares",
            "quantity": "number|null",
            "risk_r": "number|null",
            "risk_cash": "number|null"
        },
        "probability": {
            "win_prob": "0-1|null",
            "expected_rr": "number|null",
            "notes": "string"
        },
        "reasons": ["string"],
        "trigger_conditions": ["string"],
        "invalidation_conditions": ["string"],
        "next_bar_plan": ["string"],
        "citations": ["[[...]]"]
    }

    user_payload = {
        "decision_request": decision_request,
        "required_output_schema": decision_schema
    }

    user_message = json.dumps(user_payload, ensure_ascii=False)

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": context_message},
        {"role": "user", "content": user_message},
    ]

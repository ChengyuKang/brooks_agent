from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable, Optional, List, Dict, Tuple
import fitz

try:
    import tiktoken
except Exception:
    tiktoken = None

# ============ 数据结构 ============

@dataclass(frozen=True)
class PageItem:
    book: str
    pdf_path: str
    page_index: int
    text_raw: str
    text_clean: str
    noise_score: float
    is_noise: bool
    heading_lines: Optional[List[str]] = None

@dataclass(frozen=True)
class ChunkItem:
    chunk_id: str
    book: str
    pdf_path: str
    part: Optional[str]
    chapter: Optional[str]
    page_start: int
    page_end: int
    text: str
    n_tokens: int

# ============ 基础工具 ============

def token_count(text: str, model: str = "text-embedding-3-small") -> int:
    if not tiktoken:
        return max(1, len(text) // 4)
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def read_pdf_pages(pdf_path: Path) -> List[str]:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(doc.page_count):
        txt = doc.load_page(i).get_text("text") or ""
        txt = txt.replace("\r\n", "\n").replace("\r", "\n")
        pages.append(txt)
    doc.close()
    return pages

# ============ 去页眉/页脚（基于重复行统计） ============

def compute_repeated_lines(pages: List[str], top_k: int = 2, bottom_k: int = 2) -> Tuple[Dict[str, int], Dict[str, int]]:
    top_counter: Dict[str, int] = {}
    bottom_counter: Dict[str, int] = {}

    for p in pages:
        lines = [ln.strip() for ln in p.split("\n") if ln.strip()]
        top_lines = lines[:top_k]
        bottom_lines = lines[-bottom_k:] if len(lines) >= bottom_k else lines

        for ln in top_lines:
            top_counter[ln] = top_counter.get(ln, 0) + 1
        for ln in bottom_lines:
            bottom_counter[ln] = bottom_counter.get(ln, 0) + 1

    return top_counter, bottom_counter

def strip_headers_footers(text: str, top_counter: Dict[str, int], bottom_counter: Dict[str, int], total_pages: int, threshold: float = 0.30) -> str:
    # 如果某行在 >=30% 页出现，视为页眉/页脚候选
    def is_repeated(line: str, counter: Dict[str, int]) -> bool:
        return counter.get(line, 0) >= int(total_pages * threshold)

    lines = [ln.rstrip() for ln in text.split("\n")]
    # 去掉开头连续的重复行
    while lines and is_repeated(lines[0].strip(), top_counter):
        lines.pop(0)
    # 去掉末尾连续的重复行
    while lines and is_repeated(lines[-1].strip(), bottom_counter):
        lines.pop()
    return "\n".join(lines)

# ============ 清洗规则（轻量、可测） ============

_ROMAN_RE = re.compile(r"^(?=[ivxlcdm]+$)[ivxlcdm]+$", re.IGNORECASE)
_PAGE_NUM_RE = re.compile(r"^\d{1,4}$")
_SPACED_CAPS_RE = re.compile(r"\b(?:[A-Z]\s){2,}[A-Z]\b")
_CHAPTER_DIGITS_SPACED = re.compile(r"^(CHAPTER|Chapter)\s+((?:\d\s*){1,3})\b(.*)$")
_PART_ROMAN_SPACED = re.compile(r"^(PART|Part)\s+((?:[IVXLC]\s*){1,8})\b(.*)$", re.IGNORECASE)

def normalize_heading_line(line: str) -> str:
    """
    解决 PDF 把标题数字拆开的情况：
      - 'CHAPTER 2 6' -> 'CHAPTER 26'
      - 'CHAPTER 1 7' -> 'CHAPTER 17'
      - 'PART I I' -> 'PART II'（可选）
    """
    s = line.strip()
    m = _CHAPTER_DIGITS_SPACED.match(s)
    if m:
        head = m.group(1)
        digits = re.sub(r"\s+", "", m.group(2))
        tail = (m.group(3) or "").strip()
        return f"{head} {digits}" + (f" {tail}" if tail else "")

    m = _PART_ROMAN_SPACED.match(s)
    if m:
        head = m.group(1)
        roman = re.sub(r"\s+", "", m.group(2)).upper()
        tail = (m.group(3) or "").strip()
        return f"{head} {roman}" + (f" {tail}" if tail else "")

    return s

def collapse_spaced_caps(text: str) -> str:
    """
    把 'C H A P T E R' 这类空格分隔的大写字母序列压缩为 'CHAPTER'
    只对“全是大写字母+空格”的片段动手，避免误伤普通句子
    """
    def repl(m):
        return m.group(0).replace(" ", "")
    return _SPACED_CAPS_RE.sub(repl, text)

def drop_footer_noise_lines(text: str) -> str:
    bad = [
        "kohanfx.com",
        "forexwinners.net",
        "printer:",
        "jwbt",
        "p1: ota",
        "wiley",
        "isbn",
    ]
    out = []
    for ln in text.split("\n"):
        l = ln.strip()
        ll = l.lower()
        if any(b in ll for b in bad):
            continue
        out.append(ln)
    return "\n".join(out)

def clean_text_basic(text: str) -> str:
    # 1) 去掉不可见字符
    text = text.replace("\x00", "")
    # 2) 统一空格
    text = re.sub(r"[ \t]+", " ", text)
    # 3) 去掉“只有页码/罗马数字”的行
    cleaned_lines = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s:
            cleaned_lines.append("")
            continue
        if _PAGE_NUM_RE.match(s) or _ROMAN_RE.match(s):
            continue
        cleaned_lines.append(ln)
    text = "\n".join(cleaned_lines)
    # 4) 修复断词连字符： "rever-\nsal" -> "reversal"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text

def join_hard_wrapped_lines(text: str) -> str:
    """
    把 PDF 的硬换行合并成段落：
    - 行末不是句末标点，且下一行看起来是同一段，就合并
    - 遇到明显标题/CHAPTER/PART/全大写行，则保留换行
    """
    lines = [ln.rstrip() for ln in text.split("\n")]
    out: List[str] = []

    def looks_like_heading(s: str) -> bool:
        s2 = s.strip()
        if not s2:
            return False
        if re.match(r"^(CHAPTER|Chapter)\s+\d+", s2):
            return True
        if re.match(r"^(PART|Part)\s+[IVXLC0-9]+", s2):
            return True
        # 大写比例高且较短，可能是标题
        letters = [c for c in s2 if c.isalpha()]
        if len(letters) >= 6:
            upper_ratio = sum(c.isupper() for c in letters) / len(letters)
            if upper_ratio > 0.80 and len(s2) < 80:
                return True
        return False

    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        if not cur:
            out.append("")
            i += 1
            continue

        if looks_like_heading(cur):
            out.append(cur)
            i += 1
            continue

        # 合并连续正文行
        buf = cur
        while i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if not nxt:
                break
            if looks_like_heading(nxt):
                break
            # 如果当前行以句末标点结束，认为段落结束
            if re.search(r"[.!?。！？:：]$", buf):
                break
            # 下一行首字母小写/数字/括号开头，通常是同段
            if re.match(r"^[a-z0-9(\[]", nxt):
                buf += " " + nxt
                i += 1
                continue
            # 否则也倾向合并（PDF 换行常不可靠）
            buf += " " + nxt
            i += 1

        out.append(buf)
        i += 1

    # 压缩多余空行
    text2 = "\n".join(out)
    text2 = re.sub(r"\n{3,}", "\n\n", text2).strip()
    return text2

def noise_score(text: str) -> float:
    """
    噪声评分：越高越像无效页（封面/版权/目录/索引/作者介绍等）
    这个版本：
      - 关键词大小写无关
      - 提供硬排除（出现就几乎必噪声）
      - 加入 index 页的结构特征（大量短行）
    """
    if not text:
        return 1.0

    raw = text
    s = re.sub(r"\s+", " ", raw).strip()
    if not s:
        return 1.0

    s_lower = s.lower()
    s_compact = re.sub(r"[^a-z0-9]+", "", s_lower)  # 用于匹配 abouttheauthor 这类变体

    # 1) 硬噪声关键词：出现就强烈倾向噪声
    hard_noise_kw = [
        "about the author", "about the website",
        "index", "contents", "copyright", "all rights reserved",
        "dedication", "acknowledgments",
        "printer:", "wiley", "isbn",
    ]
    hard_noise_kw_compact = [
        "abouttheauthor", "aboutthewebsite",
    ]

    if any(k in s_lower for k in hard_noise_kw) or any(k in s_compact for k in hard_noise_kw_compact):
        return 0.98  # 直接拉满，避免漏检

    # 2) 字母占比太低（多为页码/目录符号）
    letters = sum(ch.isalpha() for ch in s)
    ratio_letters = letters / max(1, len(s))

    # 3) index/目录结构特征：很多短行、条目式
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    short_lines = [ln for ln in lines if len(ln) <= 40]
    short_ratio = len(short_lines) / max(1, len(lines))

    score = 0.0
    if ratio_letters < 0.35:
        score += 0.6

    if len(s) < 220:
        score += 0.2

    # 如果短行比例很高，并且行数很多，通常是 index/目录类
    if len(lines) >= 35 and short_ratio >= 0.65:
        score += 0.6

    return min(1.0, score)


def is_noise_page(score: float, hard_exclude: bool) -> bool:
    if hard_exclude:
        return True
    return score >= 0.75

# ============ 结构化：识别 Part/Chapter（弱监督，够用） ============
_PART_RE = re.compile(r"^(?:PART|Part)\s*([IVXLC0-9]+)\b[: ]?(.*)$", re.IGNORECASE)
_CHAPTER_RE = re.compile(r"^(?:CHAPTER|Chapter)\s*([0-9]{1,3})\b[: ]?(.*)$")

def _looks_like_body(s: str) -> bool:
    # 过长基本就是正文
    words = s.split()
    if len(words) >= 18:
        return True
    # 句子特征：以句号结尾/包含 is/are/therefore 等
    sl = s.lower()
    if sl.endswith(".") or " therefore " in sl or " is " in sl or " are " in sl:
        return True
    # 典型正文开头
    if re.match(r"^(a|an|the|in|on|as|most|when|if)\b", sl):
        return True
    return False

def _stop_title_line(s: str) -> bool:
    s2 = s.strip()
    if not s2:
        return True
    if _looks_like_body(s2):   # ✅ 新增
        return True
    if "kohanfx.com" in s2.lower() or "forexwinners.net" in s2.lower():  # ✅ 新增
        return True
    if re.match(r"^(FIGURE|Figure)\b", s2):
        return True
    if re.match(r"^\d+(\.\d+)?$", s2):
        return True
    if s2.lower() in {"contents", "index"}:
        return True
    return False


def extract_structure_markers(lines: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    - 先 normalize 标题行（修复 'CHAPTER 2 6'）
    - 章标题通常在 CHAPTER 行之后的 1-2 行
    """
    part = None
    chapter = None

    # 只看页面顶部有限行，减少正文里“see Chapter 3”误触发
    scan = [normalize_heading_line(ln) for ln in lines[:25]]

    for i, ln in enumerate(scan):
        s = ln.strip()

        m1 = _PART_RE.match(s)
        if m1:
            roman = m1.group(1).upper()
            tail = (m1.group(2) or "").strip()
            title_bits = []
            if tail and not _stop_title_line(tail):
                title_bits.append(tail[:80])

            # PART 标题也可能在下一行
            j = i + 1
            while j < len(scan) and len(title_bits) < 2:
                nxt = scan[j].strip()
                if _stop_title_line(nxt) or _PART_RE.match(nxt) or _CHAPTER_RE.match(nxt):
                    break
                title_bits.append(nxt[:80])
                j += 1

            part = f"Part {roman}" + (f": {' '.join(title_bits)}" if title_bits else "")
            continue

        m2 = _CHAPTER_RE.match(s)
        if m2:
            num = m2.group(1)
            tail = (m2.group(2) or "").strip()
            title_bits = []

            # tail 有时是空，有时是垃圾（比如 '6'）
            if tail and (re.search(r"[A-Za-z]", tail)):
                title_bits.append(tail[:120])

            # 章标题通常在后面 1-2 行
            j = i + 1
            while j < len(scan) and len(title_bits) < 3:
                nxt = scan[j].strip()
                if _stop_title_line(nxt) or _PART_RE.match(nxt) or _CHAPTER_RE.match(nxt):
                    break
                # 必须含字母才算“标题”，防止把单独数字带进去
                if re.search(r"[A-Za-z]", nxt):
                    title_bits.append(nxt[:120])
                j += 1

            chapter = f"Chapter {num}" + (f": {' '.join(title_bits)}" if title_bits else "")
            continue

    return part, chapter

# ============ 切分：先按“页级连续+结构标记”，再按 token chunk ============

def split_by_tokens(text: str, max_tokens: int, overlap: int, model: str = "text-embedding-3-small") -> list[str]:
    if not tiktoken:
        # 没有 tiktoken 时，退化：按字符硬切（不完美，但至少不会爆长）
        step = max(200, max_tokens * 4)
        ov = overlap * 4
        out = []
        i = 0
        while i < len(text):
            j = min(len(text), i + step)
            piece = text[i:j].strip()
            if piece:
                out.append(piece)
            i = j - ov if overlap > 0 else j
            if i < 0: i = 0
            if i >= j: i = j
        return out

    enc = tiktoken.encoding_for_model(model)
    toks = enc.encode(text)
    out = []
    i = 0
    while i < len(toks):
        j = min(len(toks), i + max_tokens)
        piece = enc.decode(toks[i:j]).strip()
        if piece:
            out.append(piece)
        i = j - overlap if overlap > 0 else j
        if i < 0: i = 0
        if i >= j: i = j
    return out

def chunk_text(text: str, max_tokens: int = 900, overlap: int = 120) -> List[str]:
    # 先按空行粗分段
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    cur: List[str] = []
    cur_tokens = 0

    paras2 = []
    for p in paras:
        if token_count(p) > max_tokens:
            paras2.extend(split_by_tokens(p, max_tokens=max_tokens, overlap=0))  # 段落内部切，不用 overlap
        else:
            paras2.append(p)
    paras = paras2

    for p in paras:
        t = token_count(p)
        if cur and cur_tokens + t > max_tokens:
            chunks.append("\n\n".join(cur).strip())
            # overlap：从最后若干 token 的段落回退（简化：按段落回退）
            if overlap > 0:
                back: List[str] = []
                back_tokens = 0
                for bp in reversed(cur):
                    bt = token_count(bp)
                    if back_tokens + bt > overlap:
                        break
                    back.insert(0, bp)
                    back_tokens += bt
                cur = back
                cur_tokens = back_tokens
            else:
                cur = []
                cur_tokens = 0

        cur.append(p)
        cur_tokens += t

    if cur:
        chunks.append("\n\n".join(cur).strip())
    return chunks

def merge_and_dedup_raw_pieces(
    pieces: list[str],
    page_marker_re: re.Pattern,
    *,
    min_tokens: int = 250,
    soft_max_tokens: int = 1100,
) -> list[str]:
    """
    对 chunk_text() 产出的 pieces（仍含 <<PAGE:x>> marker）做：
      - 去掉空片段
      - 去掉与前一段“近重复”的片段
      - 把过短片段合并进前一段（只要合并后不超过 soft_max_tokens）
    注意：在去 marker 后计算 token，但返回仍保留 marker（确保 page 可追溯性）。
    """

    def clean(x: str) -> str:
        return page_marker_re.sub("", x).strip()

    def norm(x: str) -> str:
        return re.sub(r"\s+", " ", x).strip().lower()

    out: list[str] = []
    for raw in pieces:
        c = clean(raw)
        if not c:
            continue

        if out:
            prev_raw = out[-1]
            prev_c = clean(prev_raw)

            # 1) 近重复去重：短片段通常是 overlap 造成
            nc = norm(c)
            np = norm(prev_c)
            if nc and nc in np:
                continue
            if np and np in nc:
                out[-1] = raw
                continue

            # 2) 过短合并：把短尾巴并回上一段
            if token_count(c) < min_tokens:
                if token_count(prev_c) + token_count(c) <= soft_max_tokens:
                    out[-1] = prev_raw.rstrip() + "\n\n" + raw.lstrip()
                    continue

        out.append(raw)

    # 3) 最后一段若仍过短，尝试回并
    if len(out) >= 2:
        last_c = clean(out[-1])
        prev_c = clean(out[-2])
        if token_count(last_c) < min_tokens and token_count(prev_c) + token_count(last_c) <= soft_max_tokens:
            out[-2] = out[-2].rstrip() + "\n\n" + out[-1].lstrip()
            out.pop()

    return out
# ============ 主流程：页 -> PageItem -> ChunkItem ============

def build_page_items(book: str, pdf_path: Path, hard_exclude_pages: set[int]) -> List[PageItem]:
    pages = read_pdf_pages(pdf_path)
    top_counter, bottom_counter = compute_repeated_lines(pages, top_k=2, bottom_k=2)
    total = len(pages)

    items: List[PageItem] = []
    for i, raw in enumerate(pages):
        stripped = strip_headers_footers(raw, top_counter, bottom_counter, total_pages=total, threshold=0.30)
        basic = clean_text_basic(stripped)
        basic = drop_footer_noise_lines(basic)
        basic = collapse_spaced_caps(basic)

        raw_lines = [ln.strip() for ln in basic.split("\n") if ln.strip()]
        heading_lines = raw_lines[:30]   # 30 行足够识别 part/chapter

        joined = join_hard_wrapped_lines(basic)

        score = noise_score(joined)
        hard_ex = i in hard_exclude_pages
        noise = is_noise_page(score, hard_exclude=hard_ex)

        items.append(PageItem(
            book=book,
            pdf_path=str(pdf_path),
            page_index=i,
            text_raw=raw,
            text_clean=joined,
            noise_score=score,
            is_noise=noise,
            heading_lines=heading_lines
        ))
    return items

def build_chunks(pages: List[PageItem], max_tokens: int = 900, overlap: int = 120) -> List[ChunkItem]:
    chunks: List[ChunkItem] = []
    cur_part = None
    cur_chapter = None

    # 只用非噪声页拼接，按结构标记更新 metadata
    usable = [p for p in pages if not p.is_noise and p.text_clean.strip()]

    # 逐页累积，但遇到 Part/Chapter 变化时切一刀（避免跨章污染）
    buffer_texts: List[str] = []
    buffer_pages: List[int] = []

    def flush():
        if not buffer_texts:
            return
        text = "\n\n".join(buffer_texts).strip()
        page_start = min(buffer_pages)
        page_end = max(buffer_pages)
        page_marker_re = re.compile(r"<<PAGE:(\d+)>>")

        pieces = chunk_text(text, max_tokens=max_tokens, overlap=overlap)
        # 先合并短片段 + 去重（仍保留 marker）
        pieces = merge_and_dedup_raw_pieces(
            pieces,
            page_marker_re,
            min_tokens=250,
            soft_max_tokens=int(max_tokens * 1.2),
        )
        for idx, piece in enumerate(pieces):
            pages_in_piece = [int(x) for x in page_marker_re.findall(piece)]
            if pages_in_piece:
                ps = min(pages_in_piece)
                pe = max(pages_in_piece)
            else:
                ps = page_start
                pe = page_end

            # 去掉 marker 再写入 chunk
            piece_clean = page_marker_re.sub("", piece).strip()

            # ✅ 过滤空 chunk（解决“隔一个空白”）
            if not piece_clean:
                continue

            # 可选：过滤“几乎没有有效字母”的 chunk（例如只有网址/页眉页脚）
            alpha = sum(ch.isalpha() for ch in piece_clean)
            if alpha < 30:   # 阈值可调；先保守一点
                continue

            # 可选：过滤 token 极少的 chunk（防止 chunker 产出边角碎片）
            if token_count(piece_clean) < 40:
                continue

            cid = f"{usable[0].book}-{ps}-{pe}-{len(chunks)}-{idx}"
            chunks.append(ChunkItem(
                chunk_id=cid,
                book=usable[0].book,
                pdf_path=usable[0].pdf_path,
                part=cur_part,
                chapter=cur_chapter,
                page_start=ps,
                page_end=pe,
                text=piece_clean,
                n_tokens=token_count(piece_clean),
            ))
        buffer_texts.clear()
        buffer_pages.clear()

    for p in usable:
        lines = p.heading_lines if (p.heading_lines and len(p.heading_lines) > 0) \
        else [ln for ln in p.text_clean.split("\n") if ln.strip()]
        part, chapter = extract_structure_markers(lines)

        if (part and part != cur_part) or (chapter and chapter != cur_chapter):
            # 先把之前的 buffer 输出，再更新结构
            flush()
            if part:
                cur_part = part
            if chapter:
                cur_chapter = chapter

        buffer_texts.append(f"\n\n<<PAGE:{p.page_index}>>\n\n{p.text_clean}")
        buffer_pages.append(p.page_index)

        # 强制 flush：避免 chapter miss 时 buffer 无限制变大
        if len(buffer_pages) >= 8:
            flush()
        else:
            # 或者用 token 上限（更精确，但更耗一点）
            buf_text_tmp = "\n\n".join(buffer_texts)
            if token_count(buf_text_tmp) >= 6000:
                flush()

    flush()
    return chunks

def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

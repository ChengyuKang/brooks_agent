# ai_brooks_knowledge/debug_pdf_extract.py
from PyPDF2 import PdfReader

route_path = "C:/Users/16695/Desktop/LLM/tradeBooks/"
PDFS = {
    "trend": route_path + "trend1.pdf",
    "range": route_path + "range2.pdf",
    "reversal": route_path + "reversal3.pdf",
}

def inspect_pdf(pdf_path: str, name: str, sample_pages=(0, 1, 10, 50, -1)):
    reader = PdfReader(pdf_path)
    n = len(reader.pages)
    print(f"\n=== {name} ===")
    print("Total pages:", n)

    pages = []
    for p in sample_pages:
        idx = p if p >= 0 else n + p
        if idx < 0 or idx >= n:
            continue
        pages.append(idx)

    for idx in pages:
        text = reader.pages[idx].extract_text() or ""
        text_stripped = " ".join(text.split())
        print(f"\n--- page {idx+1}/{n} ---")
        print("raw_len:", len(text), "clean_len:", len(text_stripped))
        print("preview:", text_stripped[:400])

if __name__ == "__main__":
    for name, path in PDFS.items():
        inspect_pdf(path, name)

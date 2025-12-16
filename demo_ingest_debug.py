from pathlib import Path
from ai_brooks_knowledge.ingest_books import ingest_books, BookSpec

trend = r"C:\Users\16695\Desktop\LLM\tradeBooks\trend1.pdf"

ingest_books(
    books=[BookSpec("Trading Price Action Trends", Path(trend))],
    out_path=Path(r".\ai_brooks_knowledge\vectorstores\_tmp_test"),
    limit_pages=50,
    dry_run=True,
    debug=True,
)

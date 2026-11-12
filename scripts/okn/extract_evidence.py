"""Текст локальных PDF-первоисточников по страницам, без OCR сканов."""
from pathlib import Path

import pymupdf

R = Path(__file__).resolve().parents[2]
out = R / "tmp/okn-text"
out.mkdir(parents=True, exist_ok=True)
for path in sorted((R / "data/okn/evidence").glob("*.pdf")):
    with pymupdf.open(path) as document:
        assert len(document) > 0, path
        text = "\n".join(f"PAGE {i + 1}\n{page.get_text()}" for i, page in enumerate(document))
        (out / (path.stem + ".txt")).write_text(text, encoding="utf-8")
        print(path.name, len(document), flush=True)

"""Индекс всех PDF со страницы ГИКЭ, с повторным использованием сохраненных источников."""
import csv
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin

R = Path(__file__).resolve().parents[2]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        url = urljoin("https://okn-ra.ru", dict(attrs).get("href", ""))
        if tag == "a" and "/attachments/article/57/" in url and unquote(url).lower().endswith(".pdf"):
            self.urls.add(unquote(url))


def main():
    path = R / "data/okn/evidence_sources.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        sources = list(csv.DictReader(stream))
    known = {unquote(r["url"]): r for r in sources}
    parser = Links()
    parser.feed((R / "data/okn/evidence/inspection_gike.html").read_text(encoding="utf-8"))
    rows = []
    for url in sorted(parser.urls):
        if url not in known:
            source_id = "gike_" + hashlib.sha256(url.encode()).hexdigest()[:12]
            row = {"source_id": source_id, "url": url, "local_path": f"data/okn/evidence/{source_id}.pdf"}
            sources.append(row)
            known[url] = row
        title = url.rsplit("/", 1)[-1]
        rows.append({"source_id": known[url]["source_id"], "title": title, "url": url,
                     "local_path": known[url]["local_path"],
                     "kind": "сводка обсуждения" if "сводка" in title.lower() else "акт или приложение"})
    assert rows and len({r["source_id"] for r in rows}) == len(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source_id", "url", "local_path"])
        writer.writeheader()
        writer.writerows(sources)
    with (R / "data/okn/gike_document_index.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("PDF в разделе ГИКЭ:", len(rows), "не скачаны:", sum(not (R / r["local_path"]).exists() for r in rows))


if __name__ == "__main__":
    main()

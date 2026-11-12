"""Сохранить первоисточники, перечисленные в evidence_sources.csv."""
import csv
import hashlib
import sys
import urllib.parse
import urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[2]


def main():
    with (R / "data/okn/evidence_sources.csv").open(encoding="utf-8-sig", newline="") as stream:
        sources = list(csv.DictReader(stream))
    failed = []
    for source in sources:
        if sys.argv[1:] and source["source_id"] not in sys.argv[1:]:
            continue
        path = R / source["local_path"]
        if not path.exists():
            url = urllib.parse.quote(source["url"], safe=":/?=&%!-._~")
            request = urllib.request.Request(url, headers={"User-Agent": "altai-spatial-planning/okn-research"})
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    content = response.read()
            except (OSError, urllib.error.URLError) as error:
                print("FAILED", source["source_id"], str(error), flush=True)
                failed.append(source["source_id"])
                continue
            if path.suffix == ".pdf" and not content.startswith(b"%PDF"):
                raise ValueError("Ответ не PDF: " + source["url"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(path.name, path.stat().st_size, digest, flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

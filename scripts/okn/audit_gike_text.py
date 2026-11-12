"""Сопоставление исходных 118 ОКН с текстовым слоем всех PDF раздела ГИКЭ. Без OCR."""
import csv
import hashlib
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from summarize_evidence import read, write

R = Path(__file__).resolve().parents[2]
EXCLUDED = {"042111394490005", "041640477070006", "041640546170006"}


def norm(value):
    return " ".join(re.findall(r"[а-яa-z0-9]+", value.lower().replace("ё", "е")))


def pages(text):
    parts = re.split(r"(?:^|\n)PAGE (\d+)\n", text)
    return [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]


def aliases(row):
    values = []
    if "подсказка" in row["группа_проблемы"]:
        for text in [row["название"], row["название_СТП"]]:
            values.extend(re.findall(r'["«]([^"»]+)["»]', text))
            if not text.startswith("Комплекс памятников"):
                values.append(text.split(",")[0])
    if row["рег_номер"] == "041931331800004":
        values.extend(["Кумжулу", "Камышла"])
    if row["рег_номер"] == "041710818120005":
        values.append("Курумда")
    return sorted({norm(v) for v in values if len(norm(v)) >= 4})


def main():
    rows = [r for r in read("data/okn/egrokn_altai_unresolved_audit.csv") if r["рег_номер"] not in EXCLUDED]
    assert len(rows) == 118 and len({r["рег_номер"] for r in rows}) == 118
    index = read("data/okn/gike_document_index.csv")
    assert len(index) == len({r["source_id"] for r in index})
    prepared = {r["рег_номер"]: (r, aliases(r), norm(r["учетный_номер_СТП"])) for r in rows}
    inventory, hits = [], []
    for doc in index:
        path = R / doc["local_path"]
        text_path = R / "tmp/okn-text" / (path.stem + ".txt")
        if not path.exists() or not text_path.exists():
            raise FileNotFoundError(f"Сначала fetch_evidence.py и extract_evidence.py: {doc['source_id']}")
        items = pages(text_path.read_text(encoding="utf-8"))
        assert items and [n for n, _ in items] == list(range(1, len(items) + 1)), path
        low = [n for n, t in items if len(re.findall(r"[а-яА-ЯёЁ]", t)) < 80]
        inventory.append({**doc, "pages": len(items), "pages_with_little_russian_text": len(low),
                          "little_text_page_numbers": " | ".join(map(str, low)),
                          "text_chars": sum(len(t) for _, t in items),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for page, text in items:
            numbers = set(re.findall(r"(?<!\d)04\d{13}(?!\d)", text))
            compact = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
            repaired = set(re.findall(r"(?<!\d)04\d{13}(?!\d)", compact)) - numbers
            accounts = {norm(m.group()) for m in re.finditer(r"(?<!\d)04\s*[-–]\s*\d{4,6}(?!\d)", text)}
            normalized = " " + norm(text) + " "
            coordinate_like = bool(re.search(r"\d{2,3}\s*[°º˚]\s*\d", text))
            for reg, (row, names, account) in prepared.items():
                method, marker = "", ""
                if reg in numbers:
                    method, marker = "реестровый номер", reg
                elif reg in repaired:
                    method, marker = "номер после удаления пробелов между цифрами", reg
                elif account and account in accounts:
                    method, marker = "учетный номер СТП", row["учетный_номер_СТП"]
                else:
                    matching = [name for name in names if " " + name + " " in normalized]
                    if matching:
                        method, marker = "только название или топоним", " | ".join(matching)
                if method:
                    hits.append({"рег_номер": reg, "название_ОКН": row["название"],
                                 "source_id": doc["source_id"], "document": doc["title"], "url": doc["url"],
                                 "вид_документа": doc["kind"], "страница_PDF": page,
                                 "способ_поиска": method, "маркер": marker,
                                 "координатоподобный_текст_на_странице": "да" if coordinate_like else "нет",
                                 "интерпретация": "требует проверки роли упоминания; не доказательство координат ОКН"})
    by_reg = defaultdict(list)
    for hit in hits:
        by_reg[hit["рег_номер"]].append(hit)
    working = {r["рег_номер"]: r for r in read("data/okn/egrokn_altai_working.csv")}
    manual = {r["рег_номер"]: r for r in read("data/okn/gike_manual_review.csv")}
    assert len(manual) == 9 and set(manual) <= set(prepared)
    assert all(s in {d["source_id"] for d in index} for r in manual.values() for s in r["проверенные_source_ids"].split(" | "))
    summary = []
    for row in rows:
        reg = row["рег_номер"]
        found = by_reg[reg]
        numbered = [h for h in found if h["способ_поиска"] == "реестровый номер"]
        old = [h for h in found if h["способ_поиска"] == "учетный номер СТП"]
        status = "номер найден; роль и координаты требуют проверки" if numbered else "учетный номер найден; требуется сверка" if old else "только кандидаты по названию или разорванному номеру" if found else "в доступном тексте совпадений нет; сканы не исключены"
        summary.append({"рег_номер": reg, "название": row["название"], "статус_по_тексту": status,
                        "документов_с_реестровым_номером": len({h["source_id"] for h in numbered}),
                        "документов_всего_с_маркерами": len({h["source_id"] for h in found}),
                        "source_ids": " | ".join(sorted({h["source_id"] for h in found})),
                        "страницы": " | ".join(f"{s}: " + ",".join(str(p) for p in sorted({int(h['страница_PDF']) for h in found if h['source_id'] == s})) for s in sorted({h["source_id"] for h in found})),
                        "есть_точка_в_рабочем_слое": "да" if working[reg]["lat"] and working[reg]["lon"] else "нет",
                        "граница_проверки": "только текстовый слой PDF раздела ГИКЭ; OCR не выполнялся"})
    for row in summary:
        review = manual.get(row["рег_номер"], {})
        for field in ("роль_упоминания", "вывод", "координаты_без_OCR", "следующее_действие"):
            row["ручная_проверка_" + field] = review.get(field, "")
    assert len(summary) == 118 and len({r["рег_номер"] for r in summary}) == 118
    assert len({(h['рег_номер'], h['source_id'], h['страница_PDF']) for h in hits}) == len(hits)
    write("gike_text_inventory.csv", inventory)
    if hits:
        write("gike_text_hits.csv", hits)
    write("gike_text_review_118.csv", summary)
    boundaries = defaultdict(list)
    documents = {r["source_id"]: r for r in index}
    for vertex in read("data/okn/gike_boundaries_from_text.csv"):
        doc = documents[vertex["source_id"]]
        text = dict(pages((R / "tmp/okn-text" / (Path(doc["local_path"]).stem + ".txt")).read_text(encoding="utf-8")))[int(vertex["page"])]
        for axis in ("x_as_source", "y_as_source"):
            assert vertex[axis] in text, (vertex, axis)
        boundaries[vertex["рег_номер"]].append((float(vertex["x_as_source"]), float(vertex["y_as_source"])))
    checks = []
    for reg, vertices in boundaries.items():
        assert len(vertices) == 6
        pairs = list(zip(vertices, vertices[1:] + vertices[:1]))
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in pairs)) / 2
        perimeter = sum(math.dist(a, b) for a, b in pairs)
        if reg == "041931331800004":
            assert round(area / 10000, 1) == 20.4
            source_area, result = "20.4 га", "согласуется с округлением"
        else:
            assert reg == "041740766270006" and abs(perimeter - 352.55) < .01 and abs(area - 1595) > 3000
            source_area, result = "1595 м²", "противоречие площади; периметр совпадает"
        checks.append({"рег_номер": reg, "вершин": len(vertices), "площадь_м2": round(area, 2),
                       "периметр_м": round(perimeter, 2), "площадь_в_источнике": source_area, "результат": result})
    assert len(checks) == 2
    write("gike_boundary_checks.csv", checks)
    print("PDF:", len(inventory), "страниц:", sum(d["pages"] for d in inventory), "совпадений:", len(hits))
    print(Counter(r["статус_по_тексту"] for r in summary))


if __name__ == "__main__":
    main()

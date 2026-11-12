"""Учет сохраненных источников и покрытия 121 ОКН официальным перечнем."""
import csv
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

R = Path(__file__).resolve().parents[2]


def read(path):
    with (R / path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(name, rows):
    with (R / "data/okn" / name).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        url = dict(attrs).get("href", "")
        if tag == "a" and "/attachments/article/106/" in url:
            self.urls.add(url)


def main():
    inventory = []
    for row in read("data/okn/evidence_sources.csv"):
        path = R / row["local_path"]
        row["status"] = "сохранен" if path.exists() else "не скачан"
        row["bytes"] = path.stat().st_size if path.exists() else ""
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
        if path.suffix == ".html" and path.exists() and "<title>Минкульт - Вход</title>" in path.read_text(encoding="utf-8"):
            row["status"] = "сохранена страница входа, документ недоступен"
        inventory.append(row)
    write("evidence_inventory.csv", inventory)
    text = (R / "tmp/okn-text/inspection_federal_list.txt").read_text(encoding="utf-8")
    pages = re.split(r"PAGE (\d+)\n", text)
    page_ids = {pages[i]: set(re.findall(r"(?<!\d)\d{15}(?!\d)", pages[i + 1])) for i in range(1, len(pages), 2)}
    accepted = {r["рег_номер"]: r for r in read("data/okn/verified_geocoding.csv")}
    audit = read("data/okn/egrokn_altai_unresolved_audit.csv")
    findings = read("data/okn/named51_findings.csv")
    named = {r["рег_номер"] for r in audit if "подсказка" in r["группа_проблемы"]}
    reviews = {r["рег_номер"]: r for r in findings}
    log = json.loads((R / "data/okn/named51_search_log.json").read_text(encoding="utf-8"))
    searches = {r["reg"]: r for r in log["objects"]}
    assert len(findings) == len(reviews) == len(named) == 51
    assert set(reviews) == set(searches) == named
    assert all(len(r["queries"]) == 2 for r in searches.values())
    catalog = {r["source_id"]: r for r in inventory}
    checks = []
    named_rows = []
    gike = {r["рег_номер"]: r for r in read("data/okn/gike_text_review_118.csv")}
    assert len(gike) == 118
    for row in audit:
        reg = row["рег_номер"]
        page_numbers = [page for page, ids in page_ids.items() if reg in ids]
        status = "новые координаты не установлены"
        next_step = row["следующее_действие"]
        if reg in accepted:
            status = "внесен в отдельный рабочий слой с маркировкой точности"
            next_step = accepted[reg]["гео_основание"]
        elif reg == "041640509040006":
            status = "конфликт координат научной публикации и OSM"
            next_step = "Расхождение около 9.2 км; уточнить по плану раскопа и документу территории. Ни одну точку пока не принимать."
        elif reg == "041540298210006":
            status = "OSM согласуется с районом; точка ОКН не подтверждена"
            next_step = "Генплан, с. 51–52: описание у гаражного кооператива Восточный. Координаты на с. 58 относятся к ООПТ, не к границе ОКН."
        elif reg == "041931331800004":
            status = "OSM дает ориентир поселения, не границу ОКН"
        review = reviews.get(reg)
        source_ids = review["дополнительные_источники"].split(" | ") if review and review["дополнительные_источники"] else []
        assert all(s in catalog and catalog[s]["status"] == "сохранен" for s in source_ids), reg
        if review:
            if reg not in accepted:
                status = review["результат"]
            next_step = review["вывод"] + " " + review["следующее_действие"]
        checks.append({"рег_номер": reg, "название": row["название"],
                       "источник_перечня": "inspection_federal_list" if page_numbers else "",
                       "страницы_перечня_инспекции_2018": " | ".join(page_numbers),
                       "проверка": status, "основание_или_действие": next_step,
                       "индивидуальный_поиск_51": "выполнен" if review else "не входит в группу 51",
                       "дополнительные_источники": " | ".join(source_ids),
                       "страницы_дополнительных_источников": review["страницы_PDF"] if review else ""})
        if review:
            named_rows.append({"рег_номер": reg, "название": row["название"],
                               "поиск_по_номеру": searches[reg]["queries"][0],
                               "поиск_по_названию": searches[reg]["queries"][1],
                               "уровень_проверки": "индивидуальный веб-поиск; строка официального перечня" + ("; дополнительные первоисточники" if source_ids else ""),
                               "перечень_инспекции_страницы": " | ".join(page_numbers),
                               "дополнительные_источники": " | ".join(source_ids),
                               "страницы_PDF": review["страницы_PDF"],
                               "url_дополнительных_источников": " | ".join(catalog[s]["url"] for s in source_ids),
                               "результат": review["результат"], "вывод": review["вывод"],
                               "координаты_как_в_источнике": review["координаты_в_источнике"],
                               "в_рабочем_слое": "да" if reg in accepted else "нет",
                               "следующее_действие": review["следующее_действие"]})
    for row in checks:
        review = gike.get(row["рег_номер"], {})
        row["ГИКЭ_без_OCR_статус"] = review.get("статус_по_тексту", "вне группы 118; проверен на предыдущем этапе")
        row["ГИКЭ_источники"] = review.get("source_ids", "")
        row["ГИКЭ_страницы"] = review.get("страницы", "")
        row["ГИКЭ_ручной_вывод"] = review.get("ручная_проверка_вывод", "")
    assert len(checks) == 121 and len({r["рег_номер"] for r in checks}) == 121
    assert sum(bool(r["страницы_перечня_инспекции_2018"]) for r in checks) == 117
    write("okn_source_checks.csv", checks)
    write("named51_review.csv", named_rows)
    parser = Links()
    parser.feed((R / "data/okn/evidence/inspection_boundaries.html").read_text(encoding="utf-8"))
    # URL в манифесте могут содержать %20, в HTML — обычные пробелы.
    known = {unquote(r["url"]) for r in inventory}
    index = [{"url": url, "проверка": "скачан" if unquote(url) in known else "не просмотрен"} for url in sorted(parser.urls)]
    write("boundary_document_index.csv", index)
    print(f"Перечень инспекции: 117/121 по номеру. Приказы о границах: {len(index)} ссылок. Привязок: {len(accepted)}.")


if __name__ == "__main__":
    main()

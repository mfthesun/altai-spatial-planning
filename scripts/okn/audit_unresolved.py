"""Построчный разбор ОКН уровня X по локальной выгрузке и таблицам СТП."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[2]


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def norm(value):
    return " ".join(value.lower().replace("ё", "е").split())


def main():
    source = read(R / "data/okn/egrokn_altai_geocoded.csv")
    unresolved = [row for row in source if row["качество_гео"].startswith("X:")]
    stp = []
    for filename in ("okn_federal.csv", "okn_regional.csv", "okn_local.csv"):
        for row in read(R / "data/stp_extracted/okn" / filename):
            row["source"] = "data/stp_extracted/okn/" + filename
            stp.append(row)
    result = []
    for row in unresolved:
        reg = row["рег_номер"]
        matches = [s for s in stp if reg in re.findall(r"(?<!\d)\d{15}(?!\d)", s.get("Регистрационный номер", ""))]
        method = "регистрационный номер"
        if not matches:
            matches = [s for s in stp if norm(s.get("Наименование", "")) == norm(row["название"])]
            method = "точное название, требует проверки идентичности"
        assert len(matches) <= 1, (reg, "неоднозначное сопоставление СТП")
        match = matches[0] if matches else {}
        address = match.get("Адрес", "").strip()
        district = match.get("section", "").strip()
        name = row["название"]
        if reg == "042111394490005":
            group = "адрес найден в СТП"
            action = "Проверить здание по адресу СТП: Социалистическая, 6, Горно-Алтайск; затем геокодировать."
        elif reg == "041931331800004":
            group = "ликвидированный населенный пункт"
            action = "Найти границы достопримечательного места в приказе № 18 от 04.02.2019; центр Камлака не использовать."
        elif reg == "041710818120005":
            group = "населенный пункт вне справочника 247 НП"
            action = "Установить местоположение Курумды по документу охраны и адресным источникам; статус НП пока не подтвержден."
        elif reg == "041510332190005":
            group = "адрес без населенного пункта и ориентиров"
            action = "Найти описание территории братской могилы в документе охраны; Барагашское сельское поселение не задает точку."
        else:
            # shortcut: именная подсказка определяется вручную заданными маркерами,
            # при поиске координат каждое название сверять с документом охраны.
            search_name = name + " " + match.get("Наименование", "")
            search_name = re.sub(r'["«»](?:Керексуры|керексуры|усы)["«»]', "", search_name)
            named = bool(re.search(r'["«]|(?:Юстыд|Мухор-Тархат|Кара-Су|Азалу-Оозы|Улалин|Пазырык|Куюм|Бий Сееги|Иульчак|в Соузге|в Усть-)', search_name))
            group = "пустой адрес, есть именная или топонимическая подсказка" if named else "пустой адрес, общее название"
            action = "Искать карточку и документы по регистрационному номеру; сверить топоним, район и границы." if named else "Искать по регистрационному и учетному номерам СТП; название само по себе неоднозначно."
        if not row["район"]:
            label = " Предварительный район по названию в СТП: " if method.startswith("точное название") else " Район из СТП: "
            action += label + (district or "не найден") + "."
        documents = json.loads(row["документ_охраны"] or "[]")
        result.append({
            "рег_номер": reg, "название": name, "категория": row["категория"],
            "район_выгрузки": row["район"], "адрес_выгрузки": row["адрес"],
            "группа_проблемы": group, "следующее_действие": action,
            "район_СТП": district, "адрес_СТП": address,
            "название_СТП": match.get("Наименование", ""),
            "учетный_номер_СТП": match.get("Учетный номер", ""),
            "источник_СТП": match.get("source", ""),
            "сопоставление_СТП": method if match else "не найдено",
            "документы_охраны": " | ".join(f'{d.get("date", "")} № {d.get("number", "")}: {d.get("name", "")}' for d in documents),
            "ссылки_из_выгрузки": " | ".join(d.get("archive", {}).get("url", "") for d in documents),
        })
    assert len(result) == 121
    assert len({r["рег_номер"] for r in result}) == len(result)
    assert {r["рег_номер"] for r in result} == {r["рег_номер"] for r in unresolved}
    assert sum(bool(r["адрес_выгрузки"].strip()) for r in result) == 3
    by_id = {r["рег_номер"]: r for r in result}
    assert by_id["042111394490005"]["адрес_СТП"].endswith("дом 6")
    assert "Онгудайский" in by_id["041740876180026"]["район_СТП"]
    assert "Чемальский" in by_id["041640508970046"]["район_СТП"]
    for reg in ("041740869360036", "041740844150006"):
        assert by_id[reg]["группа_проблемы"] == "пустой адрес, общее название"
    for reg in ("041640487890006", "041640598430006", "041640509030006", "041640658930006", "041620508970006", "041640441100006"):
        assert "подсказка" in by_id[reg]["группа_проблемы"]
    target = R / "data/okn/egrokn_altai_unresolved_audit.csv"
    with target.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    print(json.dumps(Counter(r["группа_проблемы"] for r in result), ensure_ascii=False, indent=2))
    print("Сопоставления СТП:", Counter(r["сопоставление_СТП"] for r in result))


if __name__ == "__main__":
    main()

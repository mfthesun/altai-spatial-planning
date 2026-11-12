"""Кандидаты OSM для ОКН уровня X. Основной слой ОКН не изменяет."""
import csv
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[2]
QUERY = '''[out:json][timeout:120];area(3600145194)->.ra;
(nwr(area.ra)["historic"];nwr(area.ra)["heritage"];nwr(area.ra)["ref:mkrf"];
nwr(area.ra)["name"~"Бодунов|Калбак|Кумжулу|Курумда|Камышл",i];);out center tags;'''

COMMON = set('''археологические памятники памятников разных эпох эпохи эпоха эпох конец
начало нач тыс тысячелетия тысячелетие половина середина сер нэ до вв век века
курган курганы курганов курганная курганные группа группы групп гончарная мастерская
каменные каменных каменное каменный каменными каменная каменной каменного камней
изваяния изваяний изваяние изваяниями оленных оленный древний древних древняя
древние древнего древнетюркского древнетюрского периода период кочевников стоянка
столбы столб столбов столбами плиты плит плита плитами землю врытые
могильник могильников могильники могила могилы могилу родового начальника
комплекс комплексы памятник памятника наскальные изображения изображений надписи
надписей ритуальный погребальные сооружения энеолитической палеолита неолита
бронзы керексуры керексур усы усами каменными выкладками выкладки несколько
десятков насыпей насыпь двадцать двенадцать десять пять четыре три одна один
которых имеет ограду ограда ограды оградой каменными цепочки укрепления остатки
оросительный оросительные системы систем канал второго первого третьего конца
кон семьдесят семь сорок сто тридцать восемь три шестнадцать четырнадцать
усть кара таш оозы камень бабы мегалитический
многослойное поселение местонахождение территория бывшего села село селе деревня
город городе памятник павшим гражданской войне братская могила купеческий дом
пещера пещере пещеры урочище сооружений сооружения территорий н а д и в с у по
iv iii ii vi vii viii ix xi xii xiii xiv xv xvi xvii xviii xix xx вв тыс'''.split())


def words(text):
    return set(re.findall(r"[а-яa-z]+", text.lower().replace("ё", "е")))


def distinctive(text):
    return {w for w in words(text) - COMMON if len(w) >= 3}


def in_ring(x, y, ring):
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def districts(x, y, boundaries):
    names = []
    for feature in boundaries:
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        if any(in_ring(x, y, polygon[0]) and not any(in_ring(x, y, hole) for hole in polygon[1:]) for polygon in polygons):
            names.append(feature["properties"]["mo"])
    return " | ".join(names)


def self_check():
    assert not distinctive('Группа курганов, «керексуры» эпохи бронзы')
    assert "калбак" in distinctive('Петроглифический комплекс "Калбак-Таш"')
    assert in_ring(1, 1, [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]])
    assert not in_ring(3, 1, [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]])
    assert not (distinctive('Курганная группа "Кара-Бога"') & words('Кара-Бом'))
    assert not (distinctive('Стоянка в Усть-Майме') & words('Усть-Каракол'))


def main():
    self_check()
    path = R / "data/okn/osm_heritage_candidates_raw.json"
    if not path.exists():
        url = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
        request = urllib.request.Request(url + "?" + urllib.parse.urlencode({"data": QUERY}),
                                         headers={"User-Agent": "altai-spatial-planning/okn-research"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.load(response)
        if payload.get("remark") or "elements" not in payload:
            raise ValueError(f"Неполный ответ Overpass: {payload.get('remark', payload)}")
        payload["query"] = QUERY
        payload["endpoint"] = url
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("remark") or "elements" not in payload:
        raise ValueError("Неполная сохраненная выборка Overpass")
    print("OSM elements:", len(payload["elements"]), payload.get("osm3s"))
    with (R / "data/okn/egrokn_altai_unresolved_audit.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    boundaries = json.loads((R / "data/slides/layers/mo_boundaries.geojson").read_text(encoding="utf-8"))["features"]
    matches, summary = [], []
    for row in rows:
        reg = row["рег_номер"]
        tokens = distinctive(row["название"] + " " + row["название_СТП"])
        found = []
        for element in payload["elements"]:
            tags = element.get("tags", {})
            names = " | ".join(v for k, v in tags.items() if k in ("name", "name:ru", "alt_name", "old_name", "official_name", "loc_name", "description"))
            shared = tokens & words(names)
            references = " ".join(v for k, v in tags.items() if "ref" in k or "heritage" in k or k in ("website", "url"))
            id_match = reg in re.findall(r"(?<!\d)\d{15}(?!\d)", references)
            if not id_match and not shared:
                continue
            point = element.get("center", element)
            if "lat" not in point or "lon" not in point:
                continue
            mo = districts(point["lon"], point["lat"], boundaries)
            expected = row["район_выгрузки"] or row["район_СТП"].replace("муниципальный район", "район").replace("Город Горно-Алтайск", "г. Горно-Алтайск")
            district_status = "совпадает" if mo == expected else "проверить район"
            ids = set(re.findall(r"(?<!\d)\d{15}(?!\d)", references))
            basis = "регистрационный номер" if id_match else "именная подсказка"
            status = "кандидат, требуется проверка"
            review = "Сопоставление по названию не подтверждает идентичность ОКН."
            if district_status != "совпадает":
                status = "отклонен: другой район"
                review = "Координата OSM находится вне ожидаемого района."
            elif tags.get("waterway") or tags.get("natural") or tags.get("amenity") == "parking":
                status = "отклонен: другой тип объекта"
                review = "Это природный объект или парковка, точка памятника не установлена."
            elif tags.get("place"):
                status = "ориентир населенного пункта"
                review = "Подходит только как ориентир поиска территории, не координаты ОКН."
            elif reg == "042111394490005":
                status = "конфликт адреса, требуется проверка"
                review = "В СТП дом 6 по Социалистической, в OSM дом 23 на той же улице; совпадения фамилии недостаточно."
            if ids and not id_match:
                status = "другой реестровый номер OSM, проверить ансамбль"
            found.append({"рег_номер": reg, "название_ОКН": row["название"], "основание": basis,
                          "общие_слова": " | ".join(sorted(shared)), "статус": status,
                          "пояснение": review,
                          "район_ОКН": expected, "район_OSM": mo, "проверка_района": district_status,
                          "osm_url": f'https://www.openstreetmap.org/{element["type"]}/{element["id"]}',
                          "название_OSM": tags.get("name", ""), "historic": tags.get("historic", ""),
                          "lon": point["lon"], "lat": point["lat"],
                          "геометрия_точки": "узел OSM" if element["type"] == "node" else "центр bbox OSM, не граница ОКН",
                          "теги_OSM": json.dumps(tags, ensure_ascii=False, sort_keys=True)})
        matches.extend(found)
        viable = sum(r["статус"] == "кандидат, требуется проверка" for r in found)
        status = "кандидаты не найдены в выборке OSM"
        if found:
            status = "есть кандидаты, требуется проверка" if viable else "только ориентиры, конфликты или отклоненные пары"
        summary.append({"рег_номер": reg, "название": row["название"], "кандидатов": len(found),
                        "кандидатов_без_выявленных_конфликтов": viable, "статус": status})
    assert len(summary) == len(rows) == 121
    assert len({r["рег_номер"] for r in summary}) == 121
    assert len({(r["рег_номер"], r["osm_url"]) for r in matches}) == len(matches)
    for filename, records in (("osm_unresolved_candidates.csv", matches), ("osm_unresolved_summary.csv", summary)):
        if not records:
            raise ValueError("Пустая таблица: " + filename)
        with (R / "data/okn" / filename).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    print("Кандидатов:", len(matches), "ОКН с кандидатами:", sum(bool(r["кандидатов"]) for r in summary))


if __name__ == "__main__":
    main()

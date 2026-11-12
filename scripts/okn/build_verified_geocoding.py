"""Рабочий слой с проверенными привязками. Исторические A/B/X не перезаписывает."""
import csv
import json
from pathlib import Path

R = Path(__file__).resolve().parents[2]


def read(name):
    with (R / "data/okn" / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    baseline = read("egrokn_altai_geocoded.csv")
    additions = read("verified_geocoding.csv")
    existing = {r["рег_номер"]: r for r in baseline}
    assert len(existing) == len(baseline) == 288
    assert len({r["рег_номер"] for r in additions}) == len(additions)
    working = {reg: dict(row) for reg, row in existing.items()}
    extra = ["гео_источник", "гео_точность", "гео_основание"]
    for row in working.values():
        row.update({key: "" for key in extra})
    for row in additions:
        reg = row["рег_номер"]
        assert reg in working and existing[reg]["качество_гео"].startswith("X:"), reg
        assert row["качество_гео"].startswith(("C:", "D:")), reg
        x, y = float(row["lon"]), float(row["lat"])
        assert 83 < x < 90 and 48 < y < 53, reg
        assert all(row[key].strip() for key in extra), reg
        working[reg].update(row)
    for reg, row in existing.items():
        if row["качество_гео"].startswith(("A:", "B:")):
            assert all(working[reg][key] == value for key, value in row.items()), reg
    points = [r for r in working.values() if r["lat"] and r["lon"]]
    assert len(points) == 167 + len(additions)
    fields = list(baseline[0]) + extra
    with (R / "data/okn/egrokn_altai_working.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(working.values())
    features = []
    for row in points:
        properties = {"рег_номер": row["рег_номер"], "название": row["название"],
                      "категория": row["категория"], "район": row["район"],
                      "качество": row["качество_гео"], "НП": row["НП_гео"]}
        properties.update({key: row[key] for key in extra})
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(row["lon"]), float(row["lat"])]},
                         "properties": properties})
    output = {"type": "FeatureCollection", "features": features}
    (R / "data/okn/egrokn_altai_working.geojson").write_text(json.dumps(output, ensure_ascii=False, indent=1), encoding="utf-8")
    assert len(output["features"]) == len(points)
    print(f"Рабочий слой: {len(working)} ОКН, {len(points)} с точкой, {len(working) - len(points)} без точки")


if __name__ == "__main__":
    main()

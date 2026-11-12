"""Контроль оцифровки контура Калбак-Таша и источников трех рабочих привязок."""
import csv
import json
import math
from pathlib import Path

from pyproj import Transformer

from match_osm import districts, in_ring

R = Path(__file__).resolve().parents[2]
with (R / "data/okn/kalbak_boundary_msk04_1.csv").open(newline="") as stream:
    rows = list(csv.DictReader(stream))
xy = [(float(r["y_easting"]), float(r["x_northing"])) for r in rows]
assert len(xy) == 32 and xy[0] == xy[-1]
assert [int(r["point"]) for r in rows] == list(range(1, 32)) + [1]
# Перенос начала координат уменьшает потерю точности в формуле площади.
shifted = [(x - xy[0][0], y - xy[0][1]) for x, y in xy]
area = abs(sum(x * v - y * u for (x, y), (u, v) in zip(shifted, shifted[1:]))) / 2
assert abs(area - 207313) < 1, area
assert abs(math.dist(xy[0], xy[1]) - 212.81) < .02
# shortcut: общие параметры МСК и перехода СК-42, для юридической геометрии
# заменить официальным преобразованием и проверить по геодезическим пунктам.
crs = "+proj=tmerc +lat_0=0 +lon_0=85.4666666666667 +k=1 +x_0=1300000 +y_0=-5112900.56 +ellps=krass +towgs84=23.57,-140.95,-79.8,0,-0.35,-0.79,-0.22 +units=m +no_defs"
transform = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
polygon = [transform.transform(x, y) for x, y in xy]
assert in_ring(86.8193213, 50.4014897, polygon)
back = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
assert math.dist(back.transform(*polygon[0]), xy[0]) < .1
house = json.loads((R / "data/okn/evidence/bodunov_nominatim.json").read_text(encoding="utf-8"))[0]
assert house["osm_id"] == 87975217 and house["category"] == "building"
assert house["address"]["house_number"] == "6"
assert house["address"]["road"] == "Социалистическая улица"
assert house["address"]["city"] == "Горно-Алтайск"
with (R / "data/okn/verified_geocoding.csv").open(encoding="utf-8-sig", newline="") as stream:
    points = {r["рег_номер"]: r for r in csv.DictReader(stream)}
assert float(points["042111394490005"]["lon"]) == float(house["lon"])
assert float(points["042111394490005"]["lat"]) == float(house["lat"])
tarkhata = points["041640546170006"]
assert abs(float(tarkhata["lat"]) - (49 + 47 / 60 + 53.1 / 3600)) < 1e-9
assert abs(float(tarkhata["lon"]) - (88 + 29 / 60 + 46 / 3600)) < 1e-9
expected = {
    "041640508950006": (88 + 38.626 / 60, 49 + 52.609 / 60),
    "041640441270006": (86 + 10 / 60 + 51.44 / 3600, 50 + 11 / 60 + 11 / 3600),
    "041640508970036": (86 + 13.492 / 60, 51 + 1.704 / 60),
    "041640441100016": (85 + 58.629 / 60, 51 + 29.764 / 60),
    "041640441100026": (85 + 58.329 / 60, 51 + 29.957 / 60),
}
boundaries = json.loads((R / "data/slides/layers/mo_boundaries.geojson").read_text(encoding="utf-8"))["features"]
for reg, (x, y) in expected.items():
    row = points[reg]
    assert abs(float(row["lon"]) - x) < 1e-9 and abs(float(row["lat"]) - y) < 1e-9, reg
    assert districts(x, y, boundaries) == row["район"], reg
assert not {"041640508970026", "041640508970046", "041640508980006", "041640508990006"} & set(points)
with (R / "data/okn/pazyryk_boundary_source.csv").open(encoding="utf-8-sig", newline="") as stream:
    pazyryk = list(csv.DictReader(stream))
assert len(pazyryk) == 20 and len({int(r["point"]) for r in pazyryk}) == 20
for ring, stated in [("1", 81498), ("2", 74), ("3", 30465)]:
    vertices = [(float(r["x_northing"]), float(r["y_easting"])) for r in pazyryk if r["ring"] == ring]
    origin = vertices[0]
    vertices = [(x - origin[0], y - origin[1]) for x, y in vertices]
    vertices.append(vertices[0])
    measured = abs(sum(x * v - y * u for (x, y), (u, v) in zip(vertices, vertices[1:]))) / 2
    assert abs(measured - stated) < 1, (ring, measured)
assert all(r["crs_as_written"] == "МСК-04 зона 1" for r in pazyryk)
assert all(2272000 < float(r["y_easting"]) < 2273000 for r in pazyryk)
assert "041640441120006" not in points  # зона из заголовка не исправляется автоматически
print(f"Контур: 31 вершина, площадь {area:.2f} м²; OSM внутри. Адрес и координаты публикации проверены.")
print("Еще пять привязок: пересчет координат и район проверены. Неоднозначные координаты не включены.")
print("Пазырык: 20 вершин и площади трех контуров проверены; в WGS-84 не преобразован из-за противоречия зоны.")

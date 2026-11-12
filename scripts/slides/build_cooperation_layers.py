"""Трансграничные территории сотрудничества (OSM, Overpass).

Готовит слои для карт вместо схематичных стрелок — реальные ареалы за границей:
- coop_khakassia_oopt.geojson      полигоны ООПТ Хакасии (природный каркас);
- coop_tyva_archaeology.geojson    памятники археологии Тывы (керескуры, Аржан, петроглифы);
- coop_mongolia_oopt.geojson       Алтай-Таван-Богд (Монголия; ООПТ с границами в OSM);
- coop_kazakhstan_oopt.geojson     Катон-Карагай (Казахстан; ООПТ с границами в OSM);
- coop_china_oopt.geojson          пустой слой: в OSM нет границ ООПТ КНР в приграничье.

Источник: OpenStreetMap (overpass-api / зеркало maps.mail.ru). Дата скачивания — в файлах.
Показываем реальные ареалы, которые продолжаются за административную границу.
Запуск из корня: .venv/bin/python scripts/slides/build_cooperation_layers.py
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
from shapely.geometry import MultiPolygon, Point, Polygon

ROOT = Path(__file__).resolve().parents[2]
LAYERS = ROOT / "data/slides/layers"
OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"


CACHE = ROOT / "data/raw/overpass_cache"


def overpass(query: str, cache_name: str) -> dict:
    """Overpass с локальным кэшем: повторные запуски не дергают сервер."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / cache_name
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS, data=data)
    payload = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=280) as r:
                payload = json.loads(r.read().decode())
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(15 * (attempt + 1))
    cached.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def relation_to_multipolygon(members):
    """Собирает MultiPolygon из outer-контуров отношения (геометрия в lon/lat)."""
    polys = []
    for m in members:
        if m.get("role") != "outer":
            continue
        geom = m.get("geometry") or []
        if len(geom) < 4:
            continue
        coords = [(p["lon"], p["lat"]) for p in geom]
        try:
            polys.append(Polygon(coords))
        except Exception:
            continue
    return MultiPolygon(polys) if polys else None


def build_khakassia():
    q = (
        '[out:json][timeout:250];'
        'relation["boundary"="protected_area"]["protect_class"~"^(1|2|4)$"]'
        '(51.5,87.5,54.5,91.0);out body geom;'
    )
    d = overpass(q, 'coop_khakassia_oopt.json')
    # Алтайский заповедник — уже ядро карт РА; Убсунурская котловина — объект Тывы.
    skip = {"Алтайский заповедник", 'Заповедник «Убсунурская котловина»'}
    rows = []
    for e in d.get("elements", []):
        name = e.get("tags", {}).get("name", "").strip()
        if not name or name in skip:
            continue
        geom = relation_to_multipolygon(e.get("members", []))
        if geom and not geom.is_empty:
            try:
                from shapely.validation import make_valid
                geom = make_valid(geom)
            except Exception:
                geom = geom.buffer(0)
            rows.append({"name": name, "geometry": geom})
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf.to_file(LAYERS / "coop_khakassia_oopt.geojson", driver="GeoJSON")
    print("khakassia_oopt:", len(gdf), list(gdf.name))


BORDER = None


def ra_border():
    """Граница РА для исключения собственных ООПТ из слоёв соседей."""
    global BORDER
    if BORDER is None:
        BORDER = gpd.read_file(ROOT / "data/access_inputs/altai_boundary.geojson").union_all()
    return BORDER


def relation_layer(cache_name, out_name, name_ru):
    """Слой из готового кэша отношения Overpass (relation(<id>);out body geom;)."""
    d = json.loads((CACHE / cache_name).read_text(encoding="utf-8"))
    rows = []
    border_geom = ra_border().buffer(0.01)  # лента ~1 км: отсекает ООПТ внутри РА, сохраняет приграничные
    for e in d.get("elements", []):
        geom = relation_to_multipolygon(e.get("members", []))
        if not geom or geom.is_empty:
            continue
        try:
            from shapely.validation import make_valid
            geom = make_valid(geom)
        except Exception:
            geom = geom.buffer(0)
        if geom.intersection(border_geom).area > 0.5 * geom.area:
            continue  # ООПТ внутри РА — не сосед
        rows.append({"name": name_ru, "geometry": geom})
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326", geometry="geometry")
    gdf.to_file(LAYERS / out_name, driver="GeoJSON")
    print(out_name, ":", len(gdf))


def build_neighbors():
    # OSM не содержит границ ООПТ КНР в приграничье — слой Китая пуст, чтобы не выдумывать ареалы.
    relation_layer("rel_3126181.json", "coop_mongolia_oopt.geojson", "Алтай-Таван-Богд")
    relation_layer("rel_13158691.json", "coop_kazakhstan_oopt.geojson", "Катон-Карагай")
    gpd.GeoDataFrame({"name": [], "geometry": []}, crs="EPSG:4326", geometry="geometry").to_file(
        LAYERS / "coop_china_oopt.geojson", driver="GeoJSON")


def build_tyva():
    q = (
        '[out:json][timeout:180];'
        '(node["historic"="archaeological_site"](49.0,88.5,53.5,99.5);'
        ' way["historic"="archaeological_site"](49.0,88.5,53.5,99.5););out center;'
    )
    d = overpass(q, 'coop_tyva_archaeology.json')
    rows = []
    for e in d.get("elements", []):
        tags = e.get("tags", {})
        if e["type"] == "node":
            lat, lon = e.get("lat"), e.get("lon")
        else:
            c = e.get("center") or {}
            lat, lon = c.get("lat"), c.get("lon")
        if not lat:
            continue
        rows.append({
            "name": tags.get("name", "").strip() or "археологический объект",
            "kind": tags.get("historic", "archaeological_site"),
            "site_type": tags.get("site_type", ""),
            "geometry": Point(lon, lat),
        })
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf.to_file(LAYERS / "coop_tyva_archaeology.geojson", driver="GeoJSON")
    ker = (gdf.name == "керескур").sum()
    print("tyva_archaeology:", len(gdf), "named:", (gdf.name != "керескур").sum(), "kereskur:", ker)


if __name__ == "__main__":
    LAYERS.mkdir(parents=True, exist_ok=True)
    build_khakassia()
    build_neighbors()
    build_tyva()

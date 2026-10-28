"""Слои для пространственной модели (задача 08), которых нет в официальных выгрузках.

Контуры ООПТ — официальные, с карты ООПТ России: data/oopt/oopt_oczk_2026-10-28.geojson
(собирает scripts/model/merge_oopt_shp.py). Отсюда берётся только контур объекта всемирного
наследия ЮНЕСКО «Золотые горы Алтая» — из OSM (Nominatim /lookup, отношение 10904143).
Пишет data/model/layers/unesco_golden_mountains.geojson (EPSG:4326).
Запуск из корня репозитория: python scripts/model/build_model_layers.py
"""
import json
import urllib.request
from pathlib import Path

import geopandas as gpd
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "model" / "layers"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "altai-spatial-planning (ITMO course project)"}

url = "https://nominatim.openstreetmap.org/lookup?format=geojson&polygon_geojson=1&polygon_threshold=0.002&osm_ids=R10904143"
with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
    f = json.load(r)["features"][0]
g = gpd.GeoDataFrame([dict(osm_id="R10904143", name="Золотые горы Алтая", category="объект всемирного наследия ЮНЕСКО",
                           geometry=shape(f["geometry"]))], crs=4326)
g["area_osm_ha"] = (g.to_crs(32645).area / 1e4).round(0)
g.to_file(OUT / "unesco_golden_mountains.geojson", driver="GeoJSON")
print(g.drop(columns="geometry").to_string(index=False))

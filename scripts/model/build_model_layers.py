"""Слои для пространственной модели (задача 08): ООПТ и объект ЮНЕСКО.

Официальный перечень ООПТ — выгрузка с карты ООПТ России (карта.оцзк.рф, 28.10.2026):
data/oopt/oopt_oczk_2026-10-28.csv (атрибуты без геометрии). Контуры крупных ООПТ берутся
из OSM (Nominatim /lookup по osm_id) и сопоставляются с перечнем по названию.
Пишет data/model/layers/oopt_main.geojson (EPSG:4326).
Запуск из корня репозитория: python scripts/model/build_model_layers.py
"""
import json
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "model" / "layers"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "altai-spatial-planning (ITMO course project)"}

# объект OSM (R — отношение, W — линия) → название в перечне ОЦЗК (None — не ООПТ РА, а надстройка)
OSM_OBJ = {
    "R1624131": "Алтайский", "R1642254": "Катунский", "R7376880": "Сайлюгемский",
    "R14900378": "Зона покоя Укок", "R12591315": "Ак Чолушпа", "R13808244": "Уч Энмек",
    "W1448357089": "Белуха", "R7738226": "Сумультинский", "R15398996": "Шавлинский",
    "R1292452": "Телецкое озеро",  # в OSM — контур всего озера, площадь больше, чем у памятника природы
    "R10904143": None,  # объект всемирного наследия ЮНЕСКО «Золотые горы Алтая»
}

reg = pd.read_csv(ROOT / "data" / "oopt" / "oopt_oczk_2026-10-28.csv", sep=";", encoding="utf-8-sig")
reg = reg[~reg["Название"].astype(str).str.startswith("Итого")].set_index("Название")

url = ("https://nominatim.openstreetmap.org/lookup?format=geojson&polygon_geojson=1&polygon_threshold=0.002&osm_ids="
       + ",".join(OSM_OBJ))
with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
    feats = {f["properties"]["osm_type"][0].upper() + str(f["properties"]["osm_id"]): f for f in json.load(r)["features"]}

rows = []
for osm_id, name in OSM_OBJ.items():
    f = feats[osm_id]
    if name is None:
        attrs = dict(name="Золотые горы Алтая", category="объект всемирного наследия ЮНЕСКО", level="ЮНЕСКО", area_ha=None)
    else:
        a = reg.loc[name]
        attrs = dict(name=name, category=a["Категория"], level=a["Значение"], area_ha=float(a["Площадь, га"]))
    rows.append(dict(osm_id=osm_id, **attrs, geometry=shape(f["geometry"])))
g = gpd.GeoDataFrame(rows, crs=4326)
g["area_osm_ha"] = (g.to_crs(32645).area / 1e4).round(0)
g.to_file(OUT / "oopt_main.geojson", driver="GeoJSON")
print(g.drop(columns="geometry").to_string(index=False))

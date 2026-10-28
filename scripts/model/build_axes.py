"""Вторые оси опорного каркаса модели (задача 08) по реальным дорогам.

Каждая ось — кратчайший по времени путь на горном графе (results/altai_drive_mountain.urbangraph,
scripts/access/build_graph.py) через заданные сёла. Пишет data/model/layers/axes_secondary.geojson
(EPSG:4326) — его рисует scripts/model/make_model_map.py без графа.
Запуск из корня репозитория: python scripts/model/build_axes.py
"""
import os
from pathlib import Path

import geopandas as gpd
import iduedu as ie
import pandas as pd
from shapely.ops import linemerge, unary_union

ROOT = Path(__file__).resolve().parents[2]
RES = Path(os.getenv("ALTAI_RESULTS", ROOT / "results"))
OUT = ROOT / "data" / "model" / "layers"

AXES = {  # ось → сёла по порядку
    "Черга — Усть-Кан — Усть-Кокса — Карагай": ["село Черга", "село Усть-Кан", "село Усть-Кокса", "село Карагай"],
    "Акташ — Улаган": ["село Акташ", "село Улаган"],
}

g = ie.UrbanGraph.read(RES / "altai_drive_mountain.urbangraph")
st = pd.read_csv(ROOT / "data" / "dataset_v3" / "settlements.csv", sep=";", encoding="utf-8-sig")
st = gpd.GeoDataFrame(st, geometry=gpd.points_from_xy(st.longitude, st.latitude), crs=4326)
rows = []
for name, chain in AXES.items():
    pts = st[st.settlement.isin(chain)].drop_duplicates("settlement").set_index("settlement").loc[chain]
    nodes = g.nearest_nodes(pts.to_crs(g.crs))
    parts, km, mins = [], 0.0, 0.0
    for a, b in zip(nodes.iloc[:-1], nodes.iloc[1:]):
        e = g.path_to_edges(g.single_source_dijkstra_path(a, b, weight="time_min"), weight="time_min")
        parts += list(e.geometry)
        km += e["length_meter"].sum() / 1000
        mins += e["time_min"].sum()
    rows.append(dict(axis=name, km=round(km, 1), time_min=round(mins), geometry=linemerge(unary_union(parts))))
ax = gpd.GeoDataFrame(rows, crs=g.crs).to_crs(4326)
ax.to_file(OUT / "axes_secondary.geojson", driver="GeoJSON")
print(ax.drop(columns="geometry").to_string(index=False))

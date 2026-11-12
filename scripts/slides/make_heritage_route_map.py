"""Маршрут наследия Анос — Калбак-Таш — Кокоря и перспективная связь с Тывой.

Точки показа не обозначают границы ОКН. Пунктир к Тыве — предложение научно-образовательного
сотрудничества, не действующая дорога или согласованный туристический маршрут.
Запуск из корня: .venv/bin/python scripts/slides/make_heritage_route_map.py
"""
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from maptools import HALO, INK, MUTED, finish, map_figure, save_map

CRS = 32645
PURPLE = "#612e78"
ROAD = "#ad401f"
OUT = ROOT / "data/slides"


def main():
    border = gpd.read_file(ROOT / "data/access_inputs/altai_boundary.geojson").to_crs(CRS)
    mo = gpd.read_file(ROOT / "data/slides/layers/mo_boundaries.geojson").to_crs(CRS)
    roads = gpd.read_file(ROOT / "data/slides/layers/roads_main.geojson").to_crs(CRS)
    table = pd.read_csv(OUT / "heritage_route_points.csv")
    points = gpd.GeoDataFrame(
        table, geometry=gpd.points_from_xy(table.longitude, table.latitude), crs=4326
    ).to_crs(CRS).sort_values("order")
    assert len(points) == 3
    assert points["order"].tolist() == [1, 2, 3]

    fig, ax = map_figure()
    core = mo[mo.mo.isin(["Онгудайский район", "Кош-Агачский район"])]
    assert len(core) == 2
    core.plot(ax=ax, color=PURPLE, alpha=0.14, edgecolor=PURPLE, linewidth=0.7, zorder=1)
    mo.boundary.plot(ax=ax, color=MUTED, linewidth=0.4, zorder=2)
    roads.plot(ax=ax, color="#9c9893", linewidth=0.55, zorder=2)
    federal = roads.ref.fillna("").str.contains("Р-256", regex=False)
    roads[federal].plot(ax=ax, color=ROAD, linewidth=1.7, zorder=3)
    border.boundary.plot(ax=ax, color=INK, linewidth=1.0, zorder=4)

    for row in points.itertuples():
        ax.scatter(row.geometry.x, row.geometry.y, s=95, color=PURPLE, edgecolor="white", linewidth=1.0, zorder=7)
        ax.text(row.geometry.x, row.geometry.y, str(row.order), color="white", fontsize=8,
                fontweight="bold", ha="center", va="center", zorder=8)
    offsets = {"Анос": (12, 10), "Калбак-Таш": (12, 12), "Кокоря": (-12, -24)}
    short = {"Анос": "музей-усадьба", "Калбак-Таш": "существующая тропа", "Кокоря": "музей теленгитов"}
    for row in points.itertuples():
        offset = offsets[row.name]
        ax.annotate(f"{row.name}\n{short[row.name]}", (row.geometry.x, row.geometry.y),
                    xytext=offset, textcoords="offset points", fontsize=7.5, color=PURPLE,
                    ha="left" if offset[0] > 0 else "right", path_effects=HALO, zorder=8,
                    arrowprops={"arrowstyle": "-", "color": PURPLE, "lw": .6,
                                "shrinkA": 2, "shrinkB": 4})

    # Реальная археология Тывы у границы — продолжение маршрута за границей (вместо стрелки).
    x0, y0, x1, y1 = border.total_bounds
    extent = (x0 - 30000, y0 - 25000, x1 + 145000, y1 + 45000)
    ty = gpd.read_file(ROOT / "data/slides/layers/coop_tyva_archaeology.geojson").to_crs(CRS)
    ex0, ey0, ex1, ey1 = extent
    ty = ty[(ty.geometry.x >= ex0) & (ty.geometry.x <= ex1) & (ty.geometry.y >= ey0) & (ty.geometry.y <= ey1)]
    ker = ty[ty.name.eq("керескур")]
    named = ty[~ty.name.eq("керескур")]
    ax.scatter(ker.geometry.x, ker.geometry.y, s=8, color=PURPLE, zorder=6)
    ax.scatter(named.geometry.x, named.geometry.y, s=42, marker="D", facecolor="none",
               edgecolor=PURPLE, lw=1.0, zorder=7)
    kp = ker.geometry.union_all().representative_point() if len(ker) else None
    if kp:
        ax.text(kp.x + 16000, kp.y - 22000, "керескуры (Тыва)", fontsize=7.2, color=PURPLE,
                style="italic", ha="left", path_effects=HALO, zorder=8)

    handles = [
        Patch(facecolor=PURPLE, alpha=0.14, edgecolor=PURPLE,
              label="южное ядро федеральной археологии"),
        Line2D([], [], color=ROAD, lw=1.7, label="Р-256 «Чуйский тракт»"),
        Line2D([], [], color="#9c9893", lw=.6, label="автодороги"),
        Line2D([], [], marker="o", ls="", ms=7, color=PURPLE, label="точки посещения (1–3)"),
        Line2D([], [], marker="o", ls="", ms=4, color=PURPLE, label="археология Тывы (керескуры)"),
    ]
    finish(fig, ax, extent=extent, handles=handles, basemap_alpha=.5)
    save_map(fig, OUT / "map_heritage_route.png")


if __name__ == "__main__":
    main()

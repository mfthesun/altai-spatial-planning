"""Карты доступности школ и пунктов первичной медико-санитарной помощи (ПМСП) — единый макет maptools.

Читает data/access_results/services_by_settlement.geojson (scripts/access/services_access.py)
и data/access_inputs/schools_osm.geojson, primary_care_osm.geojson.
Пишет data/access_results/map_access_school.png и map_access_primary_care.png.
Запуск из корня репозитория: python scripts/access/make_services_maps.py
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from maptools import INK, MUTED, SURFACE, finish, map_figure, save_map  # noqa: E402

INP, OUT = ROOT / "data" / "access_inputs", ROOT / "data" / "access_results"
CRS = 32645
RAMP = ["#ef9a5f", "#e46a2e", "#bf4d1c", "#8f360e", "#5a1f05"]  # как в make_access_maps.py
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "figure.facecolor": SURFACE})

t = gpd.read_file(OUT / "services_by_settlement.geojson").to_crs(CRS)
schools = gpd.read_file(INP / "schools_osm.geojson").to_crs(CRS)
pmsp = gpd.read_file(INP / "primary_care_osm.geojson").to_crs(CRS)
pmsp = pmsp[~pmsp.kind.str.endswith("(план)")]
border = gpd.read_file(INP / "altai_boundary.geojson").to_crs(CRS)
roads = gpd.read_file(ROOT / "data" / "slides" / "layers" / "roads_main.geojson").to_crs(CRS)
bx0, by0, bx1, by1 = border.total_bounds
EXTENT = (bx0 - 15000, by0 - 15000, bx1 + 15000, by1 + 15000)
SIZE_NOTE = Line2D([], [], color=SURFACE, lw=0, label="размер кружка — число жителей")
BASE = [Line2D([], [], color=MUTED, lw=0.8, label="граница Республики Алтай"),
        Line2D([], [], color="#b9b8b1", lw=0.5, label="магистрали")]


def base():
    fig, ax = map_figure()
    border.boundary.plot(ax=ax, color=MUTED, lw=0.8, zorder=2)
    roads.plot(ax=ax, color="#b9b8b1", lw=0.5, zorder=1)
    return fig, ax


def dots(ax, col, bins, labels):
    cls = pd.cut(t[col], bins=bins, labels=False, right=True)
    o = t.assign(c=cls).sort_values("c")
    ax.scatter(o.geometry.x, o.geometry.y, s=8 + o.pop_2025_est ** 0.5 * 0.9, c=[RAMP[int(c)] for c in o.c],
               edgecolor=SURFACE, linewidth=0.6, zorder=3)
    return [Patch(color=RAMP[i], label=l) for i, l in enumerate(labels)]


# 1. школы: расстояние по дорогам до ближайшей школы (РНГП РА: пешком 1 км, подвоз 15 км; СП 42: подвоз до 30 км)
fig, ax = base()
h = dots(ax, "school_km", [-1, 1, 15, 30, 60, 1e6], ["до 1 (школа в селе)", "1–15 (подвоз по РНГП)", "15–30 (подвоз по СП 42)",
                                                    "30–60", "больше 60"])
ax.scatter(schools.geometry.x, schools.geometry.y, s=10, marker="s", color=INK, edgecolor=SURFACE, lw=0.4, zorder=4)
finish(fig, ax, extent=EXTENT, basemap_style="relief", basemap_alpha=0.5,
       title="Условные обозначения\nнаселённые пункты: расстояние\nпо дорогам до ближайшей школы, км",
       handles=h + [SIZE_NOTE, Line2D([], [], marker="s", ls="", ms=4, color=INK, label=f"школа (OSM, {len(schools)})")] + BASE)
save_map(fig, OUT / "map_access_school.png")

# 2. ПМСП: время до ближайшего пункта (РНГП РА, СП 42: 30 мин в сёлах) и дефицит по приказу № 543н
fig, ax = base()
h = dots(ax, "pmsp_min", [-1, 15, 30, 60, 120, 1e6], ["до 15", "15–30 (норматив — до 30)", "30–60", "60–120", "больше 120"])
MARK = {"ФАП": ("o", 12), "врачебная амбулатория": ("D", 16), "участковая больница / амбулатория (СТП)": ("D", 16),
        "больница, поликлиника": ("P", 34), "медпункт без названия": ("o", 8)}
for kind, (m, s) in MARK.items():
    p = pmsp[pmsp.kind == kind]
    ax.scatter(p.geometry.x, p.geometry.y, s=s, marker=m, facecolor=INK if m != "o" else SURFACE, edgecolor=INK,
               lw=0.7, zorder=4)
need = t[t.need_543n.str.startswith("нуж", na=False)]
ax.scatter(need.geometry.x, need.geometry.y, s=90, facecolor="none", edgecolor="#2a78d6", lw=1.2, zorder=5)
n_fap = len(pmsp[pmsp.kind.isin(["ФАП", "медпункт без названия"])])
n_amb = len(pmsp[pmsp.kind.isin(["врачебная амбулатория", "участковая больница / амбулатория (СТП)"])])
finish(fig, ax, extent=EXTENT, basemap_style="relief", basemap_alpha=0.5,
       title="Условные обозначения\nнаселённые пункты: время\nдо ближайшего пункта\nпервичной медпомощи, мин",
       handles=h + [SIZE_NOTE,
                    Line2D([], [], marker="o", ls="", ms=4, mfc=SURFACE, mec=INK, label=f"ФАП, медпункт (OSM, {n_fap})"),
                    Line2D([], [], marker="D", ls="", ms=4, color=INK, label=f"врачебная амбулатория, участковая больница ({n_amb})"),
                    Line2D([], [], marker="P", ls="", ms=6, color=INK, label="больница, поликлиника"),
                    Line2D([], [], marker="o", ls="", ms=9, mfc="none", mec="#2a78d6", mew=1.2,
                           label=f"нужен ФАП или амбулатория по приказу № 543н — по данным OSM, сверить с ФРМО ({len(need)})")] + BASE)
save_map(fig, OUT / "map_access_primary_care.png")
print("ok")

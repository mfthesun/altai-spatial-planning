"""Карты и таблицы доступности больниц по результатам relief/altai_access_mountain.ipynb.

Читает results/ (выход блокнота), пишет лёгкие итоги в data/access_results/:
таблицы по МО и НП, слои изохрон и PNG-карты для слайдов.
Запуск из корня репозитория: python scripts/access/make_access_maps.py
"""
import os
import shutil
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
RES = Path(os.getenv("ALTAI_RESULTS", ROOT / "results"))
INP = ROOT / "data" / "access_inputs"
OUT = ROOT / "data" / "access_results"
OUT.mkdir(exist_ok=True)
CRS = 32645  # UTM 45N для отрисовки

# ординальная шкала времени, светлое → тёмное (проверена validate_palette.js --ordinal)
RAMP = ["#ef9a5f", "#e46a2e", "#bf4d1c", "#8f360e", "#5a1f05"]
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})

t = gpd.read_file(RES / "time_to_hospital_flat_vs_mountain.geojson").to_crs(CRS)
hosp = gpd.read_parquet(INP / "hospitals_services.parquet").to_crs(CRS)
border = gpd.read_file(INP / "altai_boundary.geojson").to_crs(CRS)
# dist — верхняя граница ступени, мин; ступень 0 пустая
iso_ga = gpd.read_file(RES / "isochrones_gorno_altaysk_mountain.geojson").to_crs(CRS).query("dist > 0")
iso_h = gpd.read_file(RES / "isochrones_hospitals_mountain.geojson").to_crs(CRS).query("dist > 0")
edges = None  # подложка: магистрали из горного графа (нужен iduedu)
if (RES / "altai_drive_mountain.urbangraph").exists():
    import iduedu as ie
    e = ie.UrbanGraph.read(RES / "altai_drive_mountain.urbangraph").edges_gdf
    edges = e[e["highway"].astype(str).str.contains("trunk|primary|secondary")][["geometry"]].to_crs(CRS)
pop = t["pop_2025_est"]

# --- таблицы -----------------------------------------------------------------------------
def share(mask, d):
    return round(d.loc[mask, "pop_2025_est"].sum() / d["pop_2025_est"].sum() * 100, 1)

rows = []
for mo, d in list(t.groupby("mo")) + [("Республика Алтай", t)]:
    rows.append(dict(mo=mo, pop_2025_est=int(round(d.pop_2025_est.sum())), n_settl=len(d),
                     A60_share_mountain=share(d.tmin_mount_A <= 60, d), A60_share_flat=share(d.tmin_flat_A <= 60, d),
                     A60_pop_outside=int(round(d.loc[d.tmin_mount_A > 60, "pop_2025_est"].sum())),
                     A_tmax_min=round(d.tmin_mount_A.max()),
                     B120_share_mountain=share(d.tmin_mount_B <= 120, d), B120_share_flat=share(d.tmin_flat_B <= 120, d),
                     B_tmean_weighted_min=round((d.tmin_mount_B * d.pop_2025_est).sum() / d.pop_2025_est.sum())))
mo_tab = pd.DataFrame(rows)
mo_tab.to_csv(OUT / "access_by_mo.csv", index=False)
cols = ["id", "name", "mo", "pop_2025_est", "tmin_flat_A", "tmin_mount_A", "tmin_flat_B", "tmin_mount_B", "delta_A_min"]
t.to_crs(4326)[cols + ["geometry"]].round(1).to_file(OUT / "time_to_hospital.geojson", driver="GeoJSON")
t[cols].round(1).sort_values("tmin_mount_A", ascending=False).to_csv(OUT / "time_to_hospital.csv", index=False)
for f in ["provision_summary.csv", "isochrones_gorno_altaysk_mountain.geojson", "isochrones_hospitals_mountain.geojson"]:
    shutil.copy(RES / f, OUT / f)


# --- карты -------------------------------------------------------------------------------
def base(ax, title):
    border.boundary.plot(ax=ax, color=MUTED, lw=0.8)
    if edges is not None:
        edges.plot(ax=ax, color="#b9b8b1", lw=0.5, zorder=1)
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.set_axis_off()


def points(ax, col, bins, labels):
    cls = pd.cut(t[col], bins=bins, labels=False, right=True)
    order = t.assign(c=cls).sort_values("c")
    ax.scatter(order.geometry.x, order.geometry.y, s=8 + (order.pop_2025_est ** 0.5) * 0.9,
               c=[RAMP[int(c)] for c in order.c], edgecolor=SURFACE, linewidth=0.6, zorder=3)
    return [Patch(color=RAMP[i], label=l) for i, l in enumerate(labels)]


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


# 1. до ближайшей больницы (сценарий А, горный граф)
fig, ax = plt.subplots(figsize=(7.5, 8))
base(ax, "Время до ближайшей больницы с койками, мин (с поправкой на рельеф)")
iso_h[iso_h["dist"] == iso_h["dist"].max()].boundary.plot(ax=ax, color=INK, lw=0.6, ls="--", zorder=2)
h = points(ax, "tmin_mount_A", [-1, 30, 60, 90, 120, 1e6], ["до 30", "30–60", "60–90", "90–120", "больше 120"])
ax.scatter(hosp.geometry.x, hosp.geometry.y, marker="P", s=60, c=INK, edgecolor=SURFACE, zorder=4)
r = mo_tab.iloc[-1]
ax.text(0.01, 0.01, f"За 60 мин доезжают {r.A60_share_mountain:.1f} % жителей; вне зоны — {r.A60_pop_outside:,} чел.".replace(",", " "),
        transform=ax.transAxes, color=INK)
ax.legend(handles=h + [Line2D([], [], marker="P", ls="", c=INK, label="больница (11)"),
                       Line2D([], [], color=INK, ls="--", lw=0.6, label="зона 60 мин")],
          loc="upper right", frameon=False, title="Населённые пункты")
save(fig, "map_time_nearest_hospital.png")

# 2. до Республиканской больницы (сценарий Б)
fig, ax = plt.subplots(figsize=(7.5, 8))
base(ax, "Время до Республиканской больницы (Горно-Алтайск), мин")
for d, ls in zip(sorted(iso_ga["dist"].unique()), [":", "--", "-"]):
    iso_ga[iso_ga["dist"] == d].boundary.plot(ax=ax, color=INK, lw=0.6, ls=ls, zorder=2)
h = points(ax, "tmin_mount_B", [-1, 60, 120, 180, 240, 1e6], ["до 60", "60–120", "120–180", "180–240", "больше 240"])
ax.text(0.01, 0.01, f"За 120 мин доезжают {r.B120_share_mountain:.1f} % жителей", transform=ax.transAxes, color=INK)
ax.legend(handles=h + [Line2D([], [], color=INK, ls=ls, lw=0.6, label=f"изохрона {int(d)} мин")
                       for d, ls in zip(sorted(iso_ga["dist"].unique()), [":", "--", "-"])],
          loc="upper right", frameon=False, title="Населённые пункты")
save(fig, "map_time_republican_hospital.png")

# 3. доля жителей в нормативе по МО
m = mo_tab.iloc[:-1].sort_values("A60_share_mountain")
fig, ax = plt.subplots(figsize=(7.5, 4.5))
y = range(len(m))
ax.barh([i + 0.2 for i in y], m.A60_share_mountain, height=0.38, color="#2a78d6", label="до ближайшей из 11 больниц ≤ 60 мин")
ax.barh([i - 0.2 for i in y], m.B120_share_mountain, height=0.38, color="#eb6834", label="до Республиканской ≤ 120 мин")
for i, (a, b) in enumerate(zip(m.A60_share_mountain, m.B120_share_mountain)):
    ax.text(a + 1, i + 0.2, f"{a:.0f}", va="center", color=MUTED, fontsize=8)
    ax.text(b + 1, i - 0.2, f"{b:.0f}", va="center", color=MUTED, fontsize=8)
ax.set_yticks(list(y), m.mo.str.replace(" район", ""))
ax.set_xlim(0, 108); ax.set_xlabel("% жителей МО")
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
ax.set_title("Доля жителей в пределах норматива РНГП (горный граф)", loc="left", color=INK, fontsize=11, pad=34)
save(fig, "chart_access_share_by_mo.png")

print(mo_tab.to_string(index=False))

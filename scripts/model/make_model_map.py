"""Схема пространственной модели (задача 08, черновик к командной сессии).

Зоны ТЭЗ (гипотеза из docs/altai_context.md, разд. 6, по границам МО), узлы четырёх уровней,
опорные оси, внешние выходы и природный каркас (крупные ООПТ, объект ЮНЕСКО).
Историко-культурный каркас добавится после выгрузки ЕГРОКН.
Читает data/slides/layers/, data/model/layers/oopt_main.geojson, data/onp_candidates.csv,
data/dataset_v3/settlements.csv. Пишет data/model/map_model_draft.png.
Запуск из корня репозитория: python scripts/model/make_model_map.py
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import LineString, box

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from maptools import HALO, INK, MUTED, SURFACE, finish, map_figure, save_map  # noqa: E402

OUT = ROOT / "data" / "model"
LAY = ROOT / "data" / "slides" / "layers"
CRS = 32645
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "figure.facecolor": SURFACE})

# ТЭЗ — гипотеза команды (docs/altai_context.md, разд. 6); зона → МО по ОКТМО
TEZ = {
    "1. Северная агломерационная": (["84701000", "84615000", "84643000"], "#b9472a"),
    "2. Северо-восточная таёжная": (["84625000", "84645000"], "#3f7f6a"),
    "3. Центральная долинная": (["84650000", "84620000", "84635000"], "#c99a3b"),
    "4. Западная высокогорная": (["84640000"], "#6c7fa8"),
    "5. Южная пограничная": (["84610000", "84630000"], "#8a6a9a"),
}
CORE = ["г. Горно-Алтайск", "село Майма"]
INTER = ["село Кош-Агач", "село Усть-Кан"]               # межрайонные центры: сценарий здравоохранения, 81,1 % в 120 мин
NEW_POINTS = ["село Акташ", "село Кебезень", "село Каракокша"]  # новые точки стационарной помощи, 95,3 % в 60 мин


def csv(p):
    for sep in (";", ","):
        d = pd.read_csv(ROOT / p, sep=sep, encoding="utf-8-sig")
        if d.shape[1] > 1:
            return d
    raise ValueError(p)


mo = gpd.read_file(LAY / "mo_boundaries.geojson").to_crs(CRS)
border = gpd.read_file(ROOT / "data" / "access_inputs" / "altai_boundary.geojson").to_crs(CRS)
roads = gpd.read_file(LAY / "roads_main.geojson").to_crs(CRS)
kp = gpd.read_file(LAY / "key_points.geojson").to_crs(CRS).set_index("label")
oopt = gpd.read_file(ROOT / "data" / "model" / "layers" / "oopt_main.geojson").to_crs(CRS)
st = csv("data/dataset_v3/settlements.csv")
st = gpd.GeoDataFrame(st, geometry=gpd.points_from_xy(st.longitude, st.latitude), crs=4326).to_crs(CRS)
pt = lambda name: st[st.settlement.eq(name) | st.object_name.eq(name)].geometry.iloc[0]
onp = csv("data/onp_candidates.csv")
onp = gpd.GeoDataFrame(onp, geometry=gpd.points_from_xy(onp.longitude, onp.latitude), crs=4326).to_crs(CRS)
summ = csv("data/dataset_v4/mo_summary.csv")
centers = [f"село {c}" for c in summ.center if c != "Горно-Алтайск"]

fig, ax = map_figure()
# вуаль вне РА
outside = gpd.GeoSeries([box(*border.buffer(600000).total_bounds).difference(border.union_all())], crs=CRS)
outside.plot(ax=ax, color=SURFACE, alpha=0.55, lw=0, zorder=1)
# ТЭЗ
mo["oktmo"] = mo["oktmo"].astype(str)
for name, (codes, col) in TEZ.items():
    mo[mo.oktmo.isin(codes)].plot(ax=ax, color=col, alpha=0.28, lw=0, zorder=1.2)
    mo[mo.oktmo.isin(codes)].dissolve().boundary.plot(ax=ax, color=col, lw=1.6, zorder=2.5)
mo.boundary.plot(ax=ax, color=MUTED, lw=0.4, zorder=2)
# природный каркас
unesco = oopt[oopt.level == "ЮНЕСКО"]
oo = oopt[oopt.level != "ЮНЕСКО"]
oo.plot(ax=ax, facecolor="none", edgecolor="#2f6b3a", hatch="////", lw=0.8, zorder=2.2)
unesco.boundary.plot(ax=ax, color="#2f6b3a", lw=1.2, ls="--", zorder=2.3)
border.boundary.plot(ax=ax, color=INK, lw=1.4, zorder=3)
# опорный каркас: главная ось — Р-256 (Чуйский тракт), вторые оси
r256 = roads[roads.ref.str.contains("Р-256", na=False)]
tel = r256[r256.name.str.contains("Телецкий", na=False)]
chuy = r256.drop(tel.index)
chuy.plot(ax=ax, color=INK, lw=3.0, zorder=4)
tel.plot(ax=ax, color=INK, lw=1.8, zorder=4)
SECOND = [["село Черга", "село Усть-Кан", "село Усть-Кокса", "село Карагай"],  # широтная ось на запад (дорога в СТП до Казахстана)
          ["село Акташ", "село Улаган"]]
for chain in SECOND:
    gpd.GeoSeries([LineString([pt(n) for n in chain])], crs=CRS).plot(ax=ax, color=INK, lw=1.8, ls="--", zorder=4)
# узлы
ax.scatter(onp.geometry.x, onp.geometry.y, s=14, color=SURFACE, edgecolor=INK, lw=0.8, zorder=5)
c = gpd.GeoSeries([pt(n) for n in centers if n not in INTER], crs=CRS)
ax.scatter(c.x, c.y, s=45, color=INK, edgecolor=SURFACE, lw=0.8, zorder=6)
for n in INTER:
    p = pt(n)
    ax.scatter([p.x], [p.y], s=150, marker="s", color="#b9472a", edgecolor=INK, lw=1.2, zorder=7)
    ax.text(p.x + 9000, p.y + 6000, n.replace("село ", ""), fontsize=8.5, fontweight="bold", color=INK,
            path_effects=HALO, zorder=8)
for n in NEW_POINTS:
    p = pt(n)
    ax.scatter([p.x], [p.y], s=60, marker="P", color="#b9472a", edgecolor=SURFACE, lw=0.6, zorder=7)
    ax.text(p.x + 7000, p.y - 9000, n.replace("село ", ""), fontsize=7.5, color=INK, path_effects=HALO, zorder=8)
core = gpd.GeoSeries([pt(n) for n in CORE], crs=CRS)
ax.scatter(core.x, core.y, s=260, color="#b9472a", edgecolor=INK, lw=1.4, zorder=7)
ax.text(core.x.iloc[0] + 12000, core.y.iloc[0] - 3000, "Горно-Алтайск — Майма", fontsize=9, fontweight="bold",
        color=INK, path_effects=HALO, zorder=8)
# внешние выходы
for name, text, (dx, dy) in [("МАПП Ташанта", "Ташанта → Монголия", (-60000, -28000)),
                             ("Карагай", "→ Казахстан", (-45000, -22000)),
                             ("Кокоря", "→ Тыва", (14000, -4000)),
                             ("Бийск (ж/д)", "→ Бийск, Барнаул, Новосибирск", (-60000, 12000))]:
    p = kp.loc[name].geometry
    ax.scatter([p.x], [p.y], s=55, marker="D", color=SURFACE, edgecolor=INK, lw=1.4, zorder=7)
    ax.text(p.x + dx, p.y + dy, text, fontsize=7.5, color=INK, path_effects=HALO, zorder=8)
# подписи зон
for name, (codes, col) in TEZ.items():
    g = mo[mo.oktmo.isin(codes)].dissolve().representative_point().iloc[0]
    off = {"1": (15000, -20000), "2": (10000, 60000), "3": (20000, -45000), "4": (-30000, -35000)}.get(name[0], (0, 0))
    ax.text(g.x + off[0], g.y + off[1], name.split(". ")[0], fontsize=16, fontweight="bold", color=col, ha="center",
            va="center", alpha=0.9, path_effects=HALO, zorder=3.5)

x0, y0, x1, y1 = border.total_bounds
finish(fig, ax, extent=(x0 - 30000, y0 - 20000, x1 + 20000, y1 + 40000), basemap_style="relief",
       title="Условные обозначения\nпространственная модель (черновик)",
       handles=[Patch(facecolor=col, alpha=0.45, edgecolor=col, label=f"ТЭЗ {name}") for name, (_, col) in TEZ.items()] +
               [Line2D([], [], marker="o", ls="", ms=12, mfc="#b9472a", mec=INK, label="ядро: Горно-Алтайск — Майма"),
                Line2D([], [], marker="s", ls="", ms=9, mfc="#b9472a", mec=INK, label="межрайонный центр (предложение)"),
                Line2D([], [], marker="o", ls="", ms=6, mfc=INK, mec=SURFACE, label="районный центр"),
                Line2D([], [], marker="o", ls="", ms=4.5, mfc=SURFACE, mec=INK, label="кандидат в опорный населённый пункт (37)"),
                Line2D([], [], marker="P", ls="", ms=7, color="#b9472a", label="новая точка стационарной помощи (предложение)"),
                Line2D([], [], color=INK, lw=3.0, label="главная ось: Р-256 «Чуйский тракт»"),
                Line2D([], [], color=INK, lw=1.8, label="вторая ось: Р-256, подъезд к Телецкому озеру (Майма — Артыбаш)"),
                Line2D([], [], color=INK, lw=1.8, ls="--", label="вторые оси (схематично): Черга — Усть-Кан — Карагай, Акташ — Улаган"),
                Line2D([], [], marker="D", ls="", mfc=SURFACE, mec=INK, label="внешний выход"),
                Patch(facecolor="none", edgecolor="#2f6b3a", hatch="////", label="крупные ООПТ (природный каркас)"),
                Line2D([], [], color="#2f6b3a", lw=1.2, ls="--", label="объект ЮНЕСКО «Золотые горы Алтая»")])
save_map(fig, OUT / "map_model_draft.png")
print("ok")

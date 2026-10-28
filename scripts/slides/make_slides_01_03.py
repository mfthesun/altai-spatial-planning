"""Карты, хронология и таблицы для слайдов 01–03 главы региона (задача 07).

01 — положение и коридоры, 02 — муниципальная реформа, 03 — агломерация.
Читает data/slides/layers/ (собирает build_slide_layers.py), data/slides/reform_status.csv,
data/dataset_v4/mo_summary.csv, data/dataset_v3/settlements.csv, data/access_results/.
Пишет PNG и CSV в data/slides/. Запуск из корня репозитория: python scripts/slides/make_slides_01_03.py
"""
from pathlib import Path

import geopandas as gpd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "slides"
LAY = OUT / "layers"
CRS = 32645  # UTM 45N для отрисовки

RAMP = ["#ef9a5f", "#e46a2e", "#bf4d1c", "#8f360e", "#5a1f05"]  # как в scripts/access/make_access_maps.py
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
RU_FILL, FOREIGN_FILL, NODATA = "#ecebe6", "#f6f0e4", "#c9c8c1"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})


def csv(p):  # как в scripts/check_numbers.py: файлы репозитория бывают с ; и с ,
    for sep in (";", ","):
        d = pd.read_csv(ROOT / p, sep=sep, encoding="utf-8-sig")
        if d.shape[1] > 1:
            return d
    raise ValueError(p)


mo = gpd.read_file(LAY / "mo_boundaries.geojson").to_crs(CRS)
roads = gpd.read_file(LAY / "roads_main.geojson").to_crs(CRS)
nb = gpd.read_file(LAY / "neighbors_admin1.geojson").to_crs(CRS)
nb.loc[nb.name == "Altay", "name_ru"] = "Алтайский край"  # в Natural Earth name_ru ошибочно «Республика Алтай»
kp = gpd.read_file(LAY / "key_points.geojson").to_crs(CRS).set_index("label")
border = gpd.read_file(ROOT / "data" / "access_inputs" / "altai_boundary.geojson").to_crs(CRS)
summ = csv("data/dataset_v4/mo_summary.csv")
summ["oktmo"] = summ["oktmo"].astype(str)
st = csv("data/dataset_v3/settlements.csv")
st = gpd.GeoDataFrame(st, geometry=gpd.points_from_xy(st.longitude, st.latitude), crs=4326).to_crs(CRS)
centers = st[st.object_name.isin(["г. Горно-Алтайск"]) | st.settlement.isin(
    [f"село {c}" for c in summ.center if c != "Горно-Алтайск"])].drop_duplicates("mo")
r256 = roads[roads.ref.str.contains("Р-256", na=False)]


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def label(ax, pt, text, dx=6000, dy=6000, **kw):
    ax.annotate(text, (pt.x, pt.y), xytext=(pt.x + dx, pt.y + dy), color=kw.pop("color", INK),
                fontsize=kw.pop("fontsize", 8), **kw)


# --- 01. Положение и коридоры --------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 8))
nb.plot(ax=ax, color=[RU_FILL if a == "Russia" else FOREIGN_FILL for a in nb.admin], edgecolor=SURFACE, lw=1.2)
mo.plot(ax=ax, color="#ffffff", edgecolor=NODATA, lw=0.5)
border.boundary.plot(ax=ax, color=INK, lw=1.2)
roads[~roads.index.isin(r256.index)].plot(ax=ax, color="#9b9a94", lw=0.6)
r256.plot(ax=ax, color=RAMP[3], lw=2.2)
ax.scatter(centers.geometry.x, centers.geometry.y, s=14, color=INK, edgecolor=SURFACE, lw=0.8, zorder=4)
ga = centers[centers.mo == "г. Горно-Алтайск"].geometry.iloc[0]
ax.scatter([ga.x], [ga.y], s=60, color=INK, edgecolor=SURFACE, lw=1, zorder=5)
label(ax, ga, "Горно-Алтайск", dx=10000, dy=-4000, fontweight="bold")
for name, (dx, dy) in {"Бийск (ж/д)": (8000, 4000), "Барнаул": (8000, 0), "Новосибирск": (8000, 0)}.items():
    p = kp.loc[name].geometry
    ax.scatter([p.x], [p.y], s=14, color=MUTED, zorder=4)
    label(ax, p, name, dx=dx, dy=dy, color=MUTED)
for name, text, (dx, dy) in [("МАПП Ташанта", "МАПП Ташанта\n→ Монголия", (-95000, -40000)),
                             ("Карагай", "Карагай → Казахстан\n(дорога в СТП)", (-150000, -8000)),
                             ("Кокоря", "Кокоря → Тыва\n(дорога в СТП)", (10000, 10000)),
                             ("плато Укок", "плато Укок\n(граница с Китаем,\nпроезда нет)", (-150000, -20000))]:
    p = kp.loc[name].geometry
    ax.scatter([p.x], [p.y], s=40, marker="D", color=SURFACE, edgecolor=RAMP[3], lw=1.5, zorder=5)
    label(ax, p, text, dx=dx, dy=dy)
x0, y0, x1, y1 = border.total_bounds
view = box(x0 - 180000, y0 - 90000, x1 + 120000, y1 + 260000)
ru = nb[(nb.admin == "Russia") & ~nb.name.isin(["Gorno-Altay", "Novosibirsk"])]  # РА — границами МО; Новосибирская под легендой
for _, r in ru.iterrows():
    g = r.geometry.intersection(view)
    if g.area > 4e9:  # подписываем только регионы, заметные в кадре
        c = g.representative_point()
        ax.annotate(r.name_ru, (c.x, c.y), color=MUTED, fontsize=7.5, ha="center")
for country, ru_name, (dx, dy) in [("Kazakhstan", "КАЗАХСТАН", (0, 0)), ("Mongolia", "МОНГОЛИЯ", (20000, -70000)),
                                    ("China", "КИТАЙ", (0, 0))]:
    g = nb[nb.admin == country].union_all().intersection(view)
    if not g.is_empty:
        c = g.representative_point()
        ax.annotate(ru_name, (c.x + dx, c.y + dy), color=MUTED, fontsize=9, ha="center", fontweight="bold")
ax.set_xlim(view.bounds[0], view.bounds[2])
ax.set_ylim(view.bounds[1], view.bounds[3])
ax.set_axis_off()
ax.set_title("Республика Алтай: соседи и выходы за пределы республики", loc="left", color=INK, fontsize=11)
ax.legend(handles=[Line2D([], [], color=RAMP[3], lw=2.2, label="Р-256 «Чуйский тракт»"),
                   Line2D([], [], color="#9b9a94", lw=0.6, label="другие магистрали (OSM trunk/primary)"),
                   Line2D([], [], marker="o", ls="", color=INK, label="районные центры"),
                   Line2D([], [], marker="D", ls="", mfc=SURFACE, mec=RAMP[3], label="внешние выходы")],
          loc="upper left", frameon=False, fontsize=8)
save(fig, "map_01_position.png")

# --- 02. Муниципальная реформа: карта статусов ---------------------------------------------
ref = csv("data/slides/reform_status.csv")
ref["oktmo"] = ref["oktmo"].astype(str)
m = mo.merge(ref, on="oktmo", suffixes=("", "_r"))
STYLE = {"муниципальный округ с 01.01.2026": RAMP[3], "муниципальный округ с 01.01.2027": RAMP[1],
         "закон о статусе не найден": NODATA, "городской округ": INK}
fig, ax = plt.subplots(figsize=(7.5, 7.5))
m.plot(ax=ax, color=[STYLE[s] for s in m.status], edgecolor=SURFACE, lw=1.5)
for _, r in m.iterrows():
    if r.oktmo == "84701000":
        continue
    c = r.geometry.representative_point()
    if r.oktmo == "84615000":  # Майминский: точка подписи рядом с Горно-Алтайском
        c = type(c)(c.x - 14000, c.y - 16000)
    law = r.law.replace("Закон РА от ", "").split(" № ")[-1] if isinstance(r.law, str) else "закона нет"
    ax.annotate(f"{r.mo.replace(' район', '')}\n{law}", (c.x, c.y), ha="center", va="center", fontsize=7.5,
                color=SURFACE if r.status.endswith("2026") else INK)
gac = m[m.oktmo == "84701000"].geometry.iloc[0].centroid
ax.annotate("Горно-Алтайск\n(городской округ)", (gac.x, gac.y), xytext=(gac.x - 95000, gac.y + 25000),
            fontsize=7.5, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
ax.set_axis_off()
ax.set_title("Муниципальные округа вместо районов: статус на 28.10.2026", loc="left", color=INK, fontsize=11)
ax.legend(handles=[Patch(color=STYLE[k], label=k) for k in list(STYLE)[:3]], loc="lower left", frameon=False,
          fontsize=8)
save(fig, "map_02_reform_status.png")

# --- 02. Хронология реформы ----------------------------------------------------------------
EVENTS = [  # дата, подпись, ярус подписи (для разведения), тип: law — закон принят, force — вступление в силу, term — срок
    ("2025-03-20", "33-ФЗ: единая система\nпубличной власти", 1, "law"),
    ("2025-06-24", "54-РЗ: одноуровневая\nсистема МСУ", -1, "law"),
    ("2025-10-30", "88-РЗ: Турочак и Чоя;\nпереходный период\nдо 31.12.2026", 1, "law"),
    ("2026-01-01", "Турочакский и Чойский —\nмуниципальные округа", -1.6, "force"),
    ("2026-02-17", "2-РЗ: Улаган\nи Усть-Кан", 2.5, "law"),
    ("2026-07-06", "64-РЗ: Кош-Агач,\nУсть-Кокса, Шебалино", -1, "law"),
    ("2026-09-30", "76-РЗ: Онгудай; переходный\nпериод до 01.01.2028", 1, "law"),
    ("2027-01-01", "ещё 6 районов —\nмуниципальные округа\n(8 из 10)", -1.6, "force"),
    ("2028-01-01", "конец переходного\nпериода", 1, "term"),
]
MARK = {"law": dict(color=SURFACE, edgecolor=RAMP[3], marker="o"), "force": dict(color=RAMP[3], edgecolor=RAMP[3], marker="o"),
        "term": dict(color=SURFACE, edgecolor=INK, marker="s")}
fig, ax = plt.subplots(figsize=(11, 3.6))
d = pd.to_datetime([e[0] for e in EVENTS])
ax.axhline(0, color=MUTED, lw=1)
ax.axvline(pd.Timestamp("2026-10-28"), color=RAMP[1], lw=1, ls="--")
ax.annotate("сейчас (28.10.2026)", (pd.Timestamp("2026-10-28"), 3.5), xytext=(4, 0), textcoords="offset points",
            color=MUTED, fontsize=7.5, ha="left", va="top")
for (_, text, lvl, kind), x in zip(EVENTS, d):
    ax.vlines(x, 0, lvl * 0.8, color=NODATA, lw=0.8)
    ax.scatter([x], [0], s=50, zorder=3, lw=1.5, **MARK[kind])
    ax.annotate(f"{x:%d.%m.%Y}\n{text}", (x, lvl * 0.85), ha="center", va="bottom" if lvl > 0 else "top",
                fontsize=7.5, color=INK, bbox=dict(boxstyle="square,pad=0.1", fc=SURFACE, ec="none"))
ax.set_ylim(-3.2, 3.6)
ax.set_xlim(pd.Timestamp("2025-01-15"), pd.Timestamp("2028-04-01"))
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
for s in ("left", "right", "top"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.set_yticks([])
ax.set_title("Муниципальная реформа Республики Алтай: законы и сроки", loc="left", color=INK, fontsize=11)
ax.legend(handles=[Line2D([], [], marker="o", ls="", mfc=SURFACE, mec=RAMP[3], label="закон принят"),
                   Line2D([], [], marker="o", ls="", color=RAMP[3], label="вступление в силу"),
                   Line2D([], [], marker="s", ls="", mfc=SURFACE, mec=INK, label="срок по закону")],
          loc="upper left", frameon=False, fontsize=8)
save(fig, "timeline_02_reform.png")

# --- 03. Агломерация: таблица -------------------------------------------------------------
s = summ.set_index("mo")
agl = s.loc[["г. Горно-Алтайск", "Майминский район"]]
p25, p23 = s["Население 1.01.2025, чел."], s["Население 1.01.2023, чел."]
cagr = lambda a, b: (a / b) ** 0.5 - 1  # 2023 → 2025, два года
g_agl = cagr(agl["Население 1.01.2025, чел."].sum(), agl["Население 1.01.2023, чел."].sum())
g_ga = cagr(p25["г. Горно-Алтайск"], p23["г. Горно-Алтайск"])
g_mm = cagr(p25["Майминский район"], p23["Майминский район"])
tm = csv("data/access_results/time_to_hospital.csv")  # tmin_mount_B — до Республиканской больницы в Горно-Алтайске
rows = [
    ("Население агломерации 1.01.2025, чел.", agl["Население 1.01.2025, чел."].sum()),
    ("Население агломерации 1.01.2023, чел.", agl["Население 1.01.2023, чел."].sum()),
    ("Доля населения РА, %", 100 * agl["Население 1.01.2025, чел."].sum() / p25.sum()),
    ("Площадь агломерации, км²", agl["Площадь, км²"].sum()),
    ("Доля площади РА, %", 100 * agl["Площадь, км²"].sum() / s["Площадь, км²"].sum()),
    ("Площадь РА, км²", s["Площадь, км²"].sum()),
    ("Население РА 1.01.2025, чел.", p25.sum()),
    ("Плотность Горно-Алтайск, чел./км²", s.loc["г. Горно-Алтайск", "Плотность, чел/км²"]),
    ("Плотность РА, чел./км²", p25.sum() / s["Площадь, км²"].sum()),
    ("Темп агломерации 2023→2025, % в год", 100 * g_agl),
    ("Темп Горно-Алтайска 2023→2025, % в год", 100 * g_ga),
    ("Темп Майминского района 2023→2025, % в год", 100 * g_mm),
    ("Тренд 2023–2025, продлённый до 2035: агломерация, чел.", agl["Население 1.01.2025, чел."].sum() * (1 + g_agl) ** 10),
    ("То же: Горно-Алтайск, чел.", p25["г. Горно-Алтайск"] * (1 + g_ga) ** 10),
] + [(f"Жителей РА в {t} мин от Горно-Алтайска (горный граф), %",
      100 * tm.loc[tm.tmin_mount_B <= t, "pop_2025_est"].sum() / tm.pop_2025_est.sum()) for t in (30, 60, 90)]
agg = pd.DataFrame(rows, columns=["показатель", "значение"])
agg["значение"] = agg["значение"].round(2)
agg.to_csv(OUT / "agglomeration_03.csv", index=False)
print(agg.to_string(index=False))
V = dict(rows)

# --- 03. Агломерация: карта изохрон -------------------------------------------------------
iso = gpd.read_file(ROOT / "data" / "access_results" / "isochrones_gorno_altaysk_mountain.geojson").to_crs(CRS)
iso = iso[iso["dist"] > 0].sort_values("dist", ascending=False)
fig, ax = plt.subplots(figsize=(7.5, 7))
nb[nb.admin == "Russia"].plot(ax=ax, color=RU_FILL, edgecolor=SURFACE, lw=1)
mo.plot(ax=ax, color="#ffffff", edgecolor=NODATA, lw=0.6)
# ступенчатые изохроны ObjectNat — непересекающиеся кольца: 0–30, 30–60, 60–90 мин (dist — верхняя граница)
iso_col = {30: "#e9a17a", 60: "#f3c6a8", 90: "#f9e3d3"}
for _, r in iso.iterrows():
    gpd.GeoSeries([r.geometry], crs=CRS).plot(ax=ax, color=iso_col[int(r["dist"])], lw=0)
mo[mo.oktmo.isin(["84701000", "84615000"])].boundary.plot(ax=ax, color=INK, lw=1.4)
roads.plot(ax=ax, color="#9b9a94", lw=0.6)
r256.plot(ax=ax, color=RAMP[3], lw=1.8)
big = st[st.population >= 1000]
ax.scatter(big.geometry.x, big.geometry.y, s=4 + big.population ** 0.5 * 0.6, color=INK, edgecolor=SURFACE,
           lw=0.6, zorder=4)
for n in ["г. Горно-Алтайск", "село Майма", "село Чемал", "село Манжерок", "село Чоя", "село Шебалино", "село Турочак"]:
    r = st[st.object_name.eq(n) | st.settlement.eq(n)]
    if len(r):
        label(ax, r.geometry.iloc[0], n.replace("село ", "").replace("г. ", ""), dx=4000, dy=2500, fontsize=7.5)
ax.set_xlim(ga.x - 110000, ga.x + 110000)
ax.set_ylim(ga.y - 130000, ga.y + 70000)
ax.set_axis_off()
ax.set_title("Горно-Алтайская агломерация: время в пути от Горно-Алтайска", loc="left", color=INK, fontsize=11)
share_t = {t: V[f"Жителей РА в {t} мин от Горно-Алтайска (горный граф), %"] for t in (30, 60, 90)}
ax.legend(handles=[Patch(color=iso_col[30], label=f"до 30 мин — {share_t[30]:.0f} % жителей РА"),
                   Patch(color=iso_col[60], label=f"30–60 мин (всего до 60 мин — {share_t[60]:.0f} %)"),
                   Patch(color=iso_col[90], label=f"60–90 мин (всего до 90 мин — {share_t[90]:.0f} %)"),
                   Line2D([], [], color=INK, lw=1.4, label="Горно-Алтайск + Майминский район")],
          loc="lower right", frameon=True, facecolor=SURFACE, edgecolor="none", fontsize=8)
save(fig, "map_03_agglomeration.png")

# --- 03. Агломерация: три прогноза к 2035 г. ----------------------------------------------
# источники: СТП Том 1 (122,6 тыс., документы терпланирования МО); мастер-план Горно-Алтайска 2025
# (+13,4 тыс. в городе и +14,8 тыс. в Майминском районе от 2025 г.); тренд Росстата 2023–2025 (расчёт выше)
fc = [("Факт 1.01.2025", V["Население агломерации 1.01.2025, чел."] / 1000, MUTED),
      ("Тренд 2023–2025\nдо 2035 г.", V["Тренд 2023–2025, продлённый до 2035: агломерация, чел."] / 1000, RAMP[3]),
      ("Мастер-план\nГорно-Алтайска", (V["Население агломерации 1.01.2025, чел."] + 13400 + 14800) / 1000, RAMP[1]),
      ("Документы МО\n(по СТП)", 122.6, RAMP[1])]
fig, ax = plt.subplots(figsize=(6.5, 3.4))
bars = ax.barh([f[0] for f in fc][::-1], [f[1] for f in fc][::-1], color=[f[2] for f in fc][::-1], height=0.6)
for b, f in zip(bars, fc[::-1]):
    ax.annotate(f"{f[1]:.1f}", (b.get_width(), b.get_y() + b.get_height() / 2), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=8, color=INK)
ax.set_xlim(0, 140)
ax.set_xlabel("жителей агломерации, тыс. чел.", color=MUTED)
ax.grid(axis="x", color="#e4e3de", lw=0.6)
ax.set_axisbelow(True)
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)
ax.tick_params(left=False)
ax.set_title("Агломерация к 2035 г.: прогнозы документов против тренда", loc="left", color=INK, fontsize=11)
save(fig, "chart_03_agglomeration_forecasts.png")

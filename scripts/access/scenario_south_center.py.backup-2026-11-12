"""Сценарии для «Мероприятий»: межрайонный медицинский центр на юге и новые точки стационарной помощи.

1. Межрайонный центр (уровень Б, норматив 120 мин). Одна или две районные больницы
   повышаются до межрайонного центра. Считаем, сколько жителей окажется в 120 мин от
   Республиканской больницы или от центра. Используется OD-матрица блокнота, граф не нужен.
2. Новые точки уровня А (норматив 60 мин). Жадный подбор до 3 сёл: в каждом шаге берётся село,
   которое добавит больше всего жителей в 60-минутную зону. Нужен горный граф.

Запуск из корня репозитория: python scripts/access/scenario_south_center.py
"""
import itertools
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RES = Path(os.getenv("ALTAI_RESULTS", ROOT / "results"))
INP = ROOT / "data" / "access_inputs"
OUT = ROOT / "data" / "access_results"

settl = gpd.read_parquet(INP / "settlements_demand.parquet").set_index("id")
hosp = gpd.read_parquet(INP / "hospitals_services.parquet").set_index("id")
od = pd.read_parquet(RES / "od_mountain_all_hospitals.parquet")
od.columns = od.columns.astype(int)
pop = settl["pop_2025_est"]
SOUTH = ["Кош-Агачский район", "Улаганский район", "Онгудайский район", "Усть-Коксинский район", "Усть-Канский район"]
south = settl["mo"].isin(SOUTH)
REP = 1  # Республиканская больница


def metrics(t, thr):
    ok = t <= thr
    return dict(share=round(pop[ok].sum() / pop.sum() * 100, 1), pop_within=int(round(pop[ok].sum())),
                share_south=round(pop[ok & south].sum() / pop[south].sum() * 100, 1),
                tmean=round((t * pop).sum() / pop.sum()), tmean_south=round((t[south] * pop[south]).sum() / pop[south].sum()))


# --- 1. межрайонный центр ----------------------------------------------------------------
cand = [i for i in hosp.index if i not in (REP, 2)]  # Майминская РБ в 10 мин от Республиканской — не кандидат
rows = [dict(centers="нет (только Республиканская)", k=0, **metrics(od[REP], 120))]
for k in (1, 2):
    for c in itertools.combinations(cand, k):
        rows.append(dict(centers=" + ".join(hosp.loc[list(c), "name"]), k=k, **metrics(od[[REP, *c]].min(axis=1), 120)))
mc = pd.DataFrame(rows)
mc["gain_pop"] = mc.pop_within - mc.pop_within.iloc[0]
mc = mc.sort_values(["k", "share"], ascending=[True, False])
mc.to_csv(OUT / "scenario_interdistrict_center.csv", index=False)
print(mc.groupby("k").head(4).to_string(index=False))

# --- 2. новые точки уровня А -------------------------------------------------------------
import iduedu as ie  # noqa: E402

g = ie.UrbanGraph.read(RES / "altai_drive_mountain.urbangraph")
ss = g.od_matrix(gdf_origins=settl, gdf_destinations=settl, weight="time_min")
if hasattr(ss, "sparse"):
    ss = ss.sparse.to_dense()
ss = ss.astype(float).fillna(1e5)
ss.columns = ss.columns.astype(int)
sites = settl.index[(pop >= 300) & (od.min(axis=1) > 30)]  # село от 300 жителей, не рядом с действующей больницей
cur = od.min(axis=1)
steps = [dict(step=0, site="действующие 11 больниц", mo="", site_pop=None, **metrics(cur, 60))]
for step in (1, 2, 3):
    gain = {s: pop[(ss[s] <= 60) & (cur > 60)].sum() for s in sites}
    best = max(gain, key=gain.get)
    cur = pd.concat([cur, ss[best]], axis=1).min(axis=1)
    steps.append(dict(step=step, site=settl.loc[best, "name"], mo=settl.loc[best, "mo"],
                      site_pop=int(round(pop[best])), **metrics(cur, 60)))
    sites = sites.drop(best)
nw = pd.DataFrame(steps)
nw["pop_outside"] = int(round(pop.sum())) - nw.pop_within
nw.to_csv(OUT / "scenario_new_points_60min.csv", index=False)
print(nw.to_string(index=False))

# --- 3. устойчивость к погрешности модели: порог 120 мин ± 15 % --------------------------
sens = []
for thr in (102, 120, 138):
    for k in (1, 2):
        best = max(itertools.combinations(cand, k), key=lambda c: metrics(od[[REP, *c]].min(axis=1), thr)["share"])
        sens.append(dict(threshold=thr, k=k, centers=" + ".join(hosp.loc[list(best), "name"]),
                         share=metrics(od[[REP, *best]].min(axis=1), thr)["share"], share_base=metrics(od[REP], thr)["share"]))
pd.DataFrame(sens).to_csv(OUT / "scenario_interdistrict_sensitivity.csv", index=False)

# --- 4. картинки -------------------------------------------------------------------------
import sys  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from maptools import finish, map_figure, no_yo, save_map  # noqa: E402

RAMP = ["#ef9a5f", "#e46a2e", "#bf4d1c", "#8f360e", "#5a1f05"]
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#ffffff"  # фон слайдов презентации
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
CRS = 32645
border = gpd.read_file(INP / "altai_boundary.geojson").to_crs(CRS)
pts = settl.to_crs(CRS)
CENTERS = [8, 9]  # Кош-Агачская + Усть-Канская — лучшая пара
bx0, by0, bx1, by1 = border.total_bounds
for name, ids in [("map_scenario_center_now.png", [REP]),            # сейчас: только Республиканская
                  ("map_scenario_center_two.png", [REP, *CENTERS])]:  # + центры в Кош-Агаче и Усть-Кане
    fig, ax = map_figure()
    t = od[ids].min(axis=1)
    cls = pd.cut(t, [-1, 60, 120, 180, 240, 1e6], labels=False)
    o = pts.assign(c=cls).sort_values("c")
    border.boundary.plot(ax=ax, color=MUTED, lw=0.8)
    ax.scatter(o.geometry.x, o.geometry.y, s=6 + o.pop_2025_est ** 0.5 * 0.7, c=[RAMP[int(c)] for c in o.c],
               edgecolor=SURFACE, linewidth=0.5, zorder=3)
    hp = hosp.loc[ids].to_crs(CRS)
    ax.scatter(hp.geometry.x, hp.geometry.y, marker="P", s=80, c=INK, edgecolor=SURFACE, zorder=4)
    m = metrics(t, 120)
    print(f"{name}: в 120 мин {m['share']:.1f} % жителей, на юге {m['share_south']:.1f} %")  # для подписи к рисунку
    finish(fig, ax, extent=(bx0 - 15000, by0 - 15000, bx1 + 15000, by1 + 15000),
           handles=[Patch(color=RAMP[i], label=l) for i, l in enumerate(["до 60", "60–120", "120–180", "180–240", "больше 240"])] +
                   [Line2D([], [], color=SURFACE, lw=0, label="размер кружка — число жителей"),
                    Line2D([], [], marker="P", ls="", ms=9, color=INK,
                           label="Республиканская больница" if len(ids) == 1 else "Республиканская больница\nи межрайонные центры"),
                    Line2D([], [], color=MUTED, lw=0.8, label="граница Республики Алтай")],
           title="Условные обозначения\nнаселённые пункты: время\nдо ближайшего центра, мин", basemap_style="relief", basemap_alpha=0.5)
    save_map(fig, OUT / name)

show = pd.concat([mc[mc.k == 0].head(1), mc[mc.k == 1].head(3), mc[mc.k == 2].head(1)])
lab = show.centers.str.replace(" РБ", "").str.replace("Кош-Агачская", "Кош-Агач").str.replace("Усть-Канская", "Усть-Кан") \
    .str.replace("Онгудайская", "Онгудай").str.replace("нет (только Республиканская)", "сейчас")
fig, ax = plt.subplots(figsize=(7.5, 3.6))
y = list(range(len(show)))[::-1]
ax.barh(y, show.share, height=0.6, color="#2a78d6")
for yi, v, gp in zip(y, show.share, show.gain_pop):
    ax.text(v + 1, yi, f"{v:.1f} %" + (f"  (+{gp / 1000:.1f} тыс. чел.)" if gp else ""), va="center", color=MUTED, fontsize=8)
ax.set_yticks(y, lab)
ax.set_xlim(0, 105)
ax.set_xlabel("% жителей республики в 120 мин от многопрофильной больницы")
ax.spines[["top", "right"]].set_visible(False)
no_yo(fig)
fig.savefig(OUT / "chart_scenario_interdistrict_center.png", dpi=200, bbox_inches="tight")
plt.close(fig)

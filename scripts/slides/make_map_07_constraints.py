"""Карта «Природный каркас и ограничения развития» для слайда 07 (задача 04).

Слои: ООПТ по официальным контурам (карта ООПТ России, 28.10.2026; федеральные и
крупные региональные — штриховкой, мелкие региональные — значками), НП в зоне
подтопления (СТП, табл. 1.5) и НП с риском разрыва связи в паводок (табл. 1.6).
Лавиноопасные участки дорог геометрии не имеют (табличные данные СТП) — на карте
не показаны, упоминаются в тезисах слайда.

Запуск:  python scripts/slides/make_map_07_constraints.py
Выход:   data/slides/map_07_constraints.png (2000x1400, макет scripts/maptools.py)
"""
import csv
import re
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))
from maptools import HALO, INK, MUTED, context_boundaries, finish, map_figure, save_map  # noqa: E402

GREEN_D, GREEN_L, RED, ORANGE = "#3f7f6a", "#a3c6b2", "#b9472a", "#e46a2e"
OUT = R / "data/slides"

ra = gpd.read_file(R / "data/access_inputs/altai_boundary.geojson").to_crs(32645)
oopt = gpd.read_file(R / "data/oopt/oopt_oczk_2026-10-28.geojson").to_crs(32645)
big = oopt[oopt["area_ha"] >= 1000]
small = oopt[oopt["area_ha"] < 1000]

setts = pd.read_csv(R / "data/dataset_v3/settlements.csv", sep=";")
setts["short"] = setts["settlement"].str.replace(
    r"^(село|с\s|с\.\s*|город|г\s|г\.\s*|поселок|п\s|п\.\s*)\s*", "", regex=True, case=False
).str.strip().str.lower().str.replace("ё", "е")


def _squash(s: str) -> str:
    """без пробелов и дефисов — чтобы «Большой-Яломан» = «Большой Яломан», «НижняяТалда» = «Нижняя Талда»."""
    return s.replace(" ", "").replace("-", "").replace(".", "")


def flood_pts(path: str) -> gpd.GeoDataFrame:
    rows = list(csv.DictReader(open(R / path, encoding="utf-8-sig")))
    seen, miss = {}, []
    for r in rows:
        np_, mo = r.get("Населенный пункт", "").strip(), r.get("Муниципальное образование", "").strip()
        if not np_ or np_.startswith("№") or np_ == "Населенный пункт" or "Итого" in np_:
            continue
        if np_ in {v[0] for v in seen.values()}:
            continue
        stem = mo.replace("муниципальное образование", "").replace("район", "").strip()
        # строка может перечислять несколько НП: «Карасук, п.Куташ»; скобки — «Шебалино (часть села)»
        tokens = [t.strip() for t in np_.split("(")[0].split(",") if t.strip()]
        for token in tokens:
            token = re.sub(r"^(село|с\.|поселок|п\.)\s*", "", token.strip(), flags=re.I).strip()
            ntok, nshort = _squash(token.lower()), setts["short"].map(_squash)
            hit = setts[(nshort == ntok) & setts["mo"].str.contains(stem)]
            if not len(hit):  # имя уникально в РА — берём без привязки к району
                cand = setts[nshort == ntok]
                if len(cand) == 1:
                    hit = cand
            if not len(hit) and len(ntok) >= 6:  # префикс: «Сайдыс» → «Средний Сайдыс» не берём, но «НижняяТалда» найдём
                cand = setts[nshort.str.startswith(ntok)]
                if len(cand) == 1:
                    hit = cand
            if len(hit):
                seen[token] = (token, hit.iloc[0]["latitude"], hit.iloc[0]["longitude"])
            else:
                miss.append((stem, token))
    print(f"{Path(path).name}: НП в списке {len(seen) + len(miss)}, привязано {len(seen)}, без координат {len(miss)}")
    for m in miss:
        print("  нет в перечне НП:", m)
    gdf = gpd.GeoDataFrame(
        {"НП": [v[0] for v in seen.values()]},
        geometry=gpd.points_from_xy([v[2] for v in seen.values()], [v[1] for v in seen.values()]),
        crs=4326,
    ).to_crs(32645)
    return gdf


flood = flood_pts("data/stp_extracted/chs/flood_zone_settlements_1.csv")
cut = flood_pts("data/stp_extracted/chs/flood_zone_settlements_2.csv")

fig, ax = map_figure()
ax.set_facecolor("#ffffff")

fed = big[big["level"] == "Федеральное"]
reg_big = big[big["level"] == "Региональное"]
fed.plot(ax=ax, facecolor="none", edgecolor=GREEN_D, linewidth=1.0, hatch="////", zorder=3)
reg_big.plot(ax=ax, facecolor="none", edgecolor=GREEN_D, linewidth=0.7, hatch="\\\\\\", zorder=3)
small.plot(ax=ax, color=GREEN_D, marker="o", markersize=12, zorder=4)
cut.plot(ax=ax, color=ORANGE, marker="s", markersize=26, edgecolor=INK, linewidth=0.5, zorder=5)
flood.plot(ax=ax, color=RED, marker="^", markersize=34, edgecolor=INK, linewidth=0.5, zorder=6)
neighbors = gpd.read_file(R / 'data/slides/layers/neighbors_admin1.geojson').to_crs(32645)
boundary_keys = context_boundaries(ax, neighbors, ra)
nearby = pd.concat([gpd.read_file(R / f'data/slides/layers/{name}.geojson').to_crs(32645)
                    for name in ['coop_khakassia_oopt', 'coop_kazakhstan_oopt',
                                 'coop_mongolia_oopt', 'coop_china_oopt']], ignore_index=True)
nearby.plot(ax=ax, facecolor='none', edgecolor='#6c9767', linewidth=.8, hatch='...', zorder=3)
for lon, lat, name in [(84.95, 53.17, 'АЛТАЙСКИЙ КРАЙ'), (87.2, 52.96, 'КУЗБАСС'),
                       (90.05, 52.06, 'ХАКАСИЯ'), (89.52, 50.85, 'ТЫВА'),
                       (83.96, 49.77, 'КАЗАХСТАН'), (88.64, 49.06, 'МОНГОЛИЯ'),
                       (87.6, 47.9, 'КИТАЙ')]:
    p = gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs=4326).to_crs(32645).iloc[0]
    ax.text(p.x, p.y, name, fontsize=7, color=MUTED, ha='center', path_effects=HALO, zorder=10)

bx = ra.total_bounds
all_bounds = pd.concat([oopt.geometry, nearby.geometry], ignore_index=True).total_bounds
EXTENT = (min(bx[0] - 150000, all_bounds[0] - 20000), min(bx[1] - 150000, all_bounds[1] - 20000),
          max(bx[2] + 150000, all_bounds[2] + 20000), max(bx[3] + 180000, all_bounds[3] + 20000))
ox0, oy0, ox1, oy1 = oopt.total_bounds
assert len(oopt) == 55
assert EXTENT[0] <= ox0 and EXTENT[1] <= oy0 and EXTENT[2] >= ox1 and EXTENT[3] >= oy1

handles = [
    Patch(facecolor="none", edgecolor=GREEN_D, hatch="///", label="ООПТ федерального значения"),
    Patch(facecolor="none", edgecolor=GREEN_D, hatch="\\\\\\", label="ООПТ региональные"),
    Line2D([], [], marker="o", ls="", ms=5, color=GREEN_D, label="памятники природы"),
    Line2D([], [], marker="^", ls="", ms=8, mfc=RED, mec=INK, label="зона подтопления"),
    Line2D([], [], marker="s", ls="", ms=7, mfc=ORANGE, mec=INK, label="риск разрыва связи в паводок"),
    Patch(facecolor='none', edgecolor='#6c9767', hatch='...', label='ООПТ соседних регионов и стран (выборка)'),
]
finish(fig, ax, extent=EXTENT, handles=handles + boundary_keys, title="Условные обозначения", basemap_style="relief")
save_map(fig, OUT / "map_07_constraints.png")
plt.close(fig)
print("сохранено:", OUT / "map_07_constraints.png")

"""Доступность школ и пунктов первичной медико-санитарной помощи (ПМСП) по горному графу.

Нормативы (подробно — docs/access_services.md):
- школа: РНГП РА (приказ Минстроя РА от 01.04.2025 № П-07-01/0180, ред. 22.04.2026) — пешеходная
  доступность 1 000 м, транспортная 15 км; СП 42.13330.2016, табл. 10.1 — подвоз не дальше 30 км;
- ПМСП в сёлах: РНГП РА и СП 42.13330.2016 — транспортная доступность 30 мин в одну сторону;
- где нужен ФАП или амбулатория: приказ Минздравсоцразвития № 543н, п. 19.2–19.6.
Читает results/altai_drive_mountain.urbangraph (scripts/access/build_graph.py), data/access_inputs/.
Пишет data/access_results/services_*.csv|geojson и results/od_mountain_all_hospitals.parquet
(нужна scripts/access/scenario_south_center.py).
Запуск из корня репозитория: python scripts/access/services_access.py
"""
import os
from pathlib import Path

import geopandas as gpd
import iduedu as ie
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RES = Path(os.getenv("ALTAI_RESULTS", ROOT / "results"))
INP = ROOT / "data" / "access_inputs"
OUT = ROOT / "data" / "access_results"

SCHOOL_WALK_KM, SCHOOL_BUS_KM, SCHOOL_BUS_MAX_KM = 1.0, 15.0, 30.0  # РНГП РА; СП 42.13330.2016
PMSP_MIN = 30          # РНГП РА, СП 42.13330.2016: ПМСП в сёлах — 30 мин в одну сторону
IN_VILLAGE_KM = 2.0    # «в населённом пункте»: объект не дальше 2 км по дорогам от точки НП (допущение)
IN_TOWN_KM = 4.0       # то же для НП больше 2 000 жителей: они протяжённее (допущение)
FAP_KM = 6.0           # приказ № 543н, п. 19.2, 19.4

g = ie.UrbanGraph.read(RES / "altai_drive_mountain.urbangraph")
settl = gpd.read_parquet(INP / "settlements_demand.parquet").set_index("id")
hosp = gpd.read_parquet(INP / "hospitals_services.parquet").set_index("id")
schools = gpd.read_file(INP / "schools_osm.geojson")
pmsp = gpd.read_file(INP / "primary_care_osm.geojson")
pmsp = pmsp[~pmsp.kind.str.endswith("(план)")]  # планируемые амбулатории СТП — не в базовом расчёте
pop = settl["pop_2025_est"]


def od(dest, weight):
    m = g.od_matrix(gdf_origins=settl, gdf_destinations=dest, weight=weight)
    if hasattr(m, "sparse"):
        m = m.sparse.to_dense()
    return m.astype(float).fillna(1e5)  # NaN — недостижимо


# --- больницы: OD для сценариев и самопроверка ----------------------------------------------
odh = od(hosp, "time_min")
odh.columns = odh.columns.astype(str)
odh.to_parquet(RES / "od_mountain_all_hospitals.parquet")
share60 = round(pop[odh.min(axis=1) <= 60].sum() / pop.sum() * 100, 1)
print("самопроверка: жителей в 60 мин от больницы, %", share60, "(в docs/access_results.md — 92,2)")

# --- школы ----------------------------------------------------------------------------------
sk = od(schools, "length_meter").min(axis=1) / 1000
st = od(schools, "time_min").min(axis=1)

# --- ПМСП: два варианта — все пункты и без медпунктов без названия ---------------------------
named = pmsp[pmsp.kind != "медпункт без названия"]
doctor = pmsp[pmsp.kind.isin(["врачебная амбулатория", "больница, поликлиника", "участковая больница / амбулатория (СТП)"])]
pt_all, pk_all = od(pmsp, "time_min").min(axis=1), od(pmsp, "length_meter").min(axis=1) / 1000
pt_named = od(named, "time_min").min(axis=1)
dk = od(doctor, "length_meter").min(axis=1) / 1000  # до ближайшей врачебной помощи

t = settl[["name", "mo", "pop_2025_est", "geometry"]].copy()
t["school_km"], t["school_min"] = sk.round(1), st.round(1)
t["pmsp_min"], t["pmsp_km"], t["pmsp_named_min"] = pt_all.round(1), pk_all.round(1), pt_named.round(1)
t["doctor_km"] = dk.round(1)
t["school_class"] = np.select([sk <= SCHOOL_WALK_KM, sk <= SCHOOL_BUS_KM, sk <= SCHOOL_BUS_MAX_KM],
                              ["в селе (≤ 1 км)", "подвоз ≤ 15 км", "подвоз 15–30 км"], "дальше 30 км")


# правила № 543н, п. 19: что должно быть в НП при его численности и удалённости
def need_543n(r):
    p = r.pop_2025_est
    if p < 100:
        return "выездные формы (меньше 100 жителей)" if r.pmsp_km > FAP_KM else ""
    if p <= 300:
        return "нужен ФАП или фельдшерский здравпункт" if r.pmsp_km > FAP_KM else ""
    if p <= 1000:
        return "нужен ФАП или фельдшерский здравпункт" if r.pmsp_km > IN_VILLAGE_KM else ""
    if p <= 2000:
        if r.doctor_km > FAP_KM:
            return "нужна врачебная амбулатория или ВОП" if r.doctor_km > IN_VILLAGE_KM else ""
        return "нужен ФАП или фельдшерский здравпункт" if r.pmsp_km > IN_VILLAGE_KM else ""
    return "нужна врачебная амбулатория" if r.doctor_km > IN_TOWN_KM else ""


t["need_543n"] = t.apply(need_543n, axis=1)

# --- итоги по МО ----------------------------------------------------------------------------
def share(mask, d):
    return round(d.loc[mask, "pop_2025_est"].sum() / d["pop_2025_est"].sum() * 100, 1)


rows = []
for mo, d in list(t.groupby("mo")) + [("Республика Алтай", t)]:
    rows.append(dict(
        mo=mo, pop_2025_est=int(d.pop_2025_est.sum()), n_settl=len(d),
        school_in_village_share=share(d.school_km <= SCHOOL_WALK_KM, d),
        school_15km_share=share(d.school_km <= SCHOOL_BUS_KM, d),
        school_30km_share=share(d.school_km <= SCHOOL_BUS_MAX_KM, d),
        school_over15_pop=int(d.loc[d.school_km > SCHOOL_BUS_KM, "pop_2025_est"].sum()),
        pmsp_30min_share=share(d.pmsp_min <= PMSP_MIN, d),
        pmsp_30min_share_named=share(d.pmsp_named_min <= PMSP_MIN, d),
        pmsp_over30_pop=int(d.loc[d.pmsp_min > PMSP_MIN, "pop_2025_est"].sum()),
        need_fap_settl=int(d.need_543n.str.startswith("нужен ФАП").sum()),
        need_amb_settl=int(d.need_543n.str.startswith("нужна врачебная").sum()),
        need_543n_pop=int(d.loc[d.need_543n.str.startswith("нуж"), "pop_2025_est"].sum())))
mo_tab = pd.DataFrame(rows)
mo_tab.to_csv(OUT / "services_by_mo.csv", index=False)
cols = ["name", "mo", "pop_2025_est", "school_km", "school_min", "school_class", "pmsp_min", "pmsp_km",
        "pmsp_named_min", "doctor_km", "need_543n"]
t.reset_index()[["id"] + cols].sort_values("pmsp_min", ascending=False).to_csv(OUT / "services_by_settlement.csv", index=False)
t.reset_index()[["id"] + cols + ["geometry"]].to_crs(4326).to_file(OUT / "services_by_settlement.geojson", driver="GeoJSON")
t[t.need_543n.str.startswith("нуж")].reset_index()[["id"] + cols].sort_values(["need_543n", "pop_2025_est"],
    ascending=[True, False]).to_csv(OUT / "services_need_543n.csv", index=False)
print(mo_tab.to_string(index=False))

import nbformat as nbf
nb=nbf.v4.new_notebook(); C=[]
md=lambda s:C.append(nbf.v4.new_markdown_cell(s)); code=lambda s:C.append(nbf.v4.new_code_cell(s))
md("""# Республика Алтай: доступность больниц с учётом рельефа
Граф IduEdu → поправка на рельеф по спутниковой ЦМР Copernicus GLO-30 → OD-матрица → обеспеченность и изохроны (ObjectNat).

Склонируйте репозиторий на Google Drive и укажите путь в `REPO`. Результаты пишутся в `results/`.""")
code("""!pip -q install iduedu==2.2.0 objectnat==2.1.0 rasterio""")
code("""from google.colab import drive; drive.mount('/content/drive')
REPO = '/content/drive/MyDrive/altai-spatial-planning'   # <- путь к клону репозитория на Drive
INPUT_DIR = f'{REPO}/data/access_inputs'; RELIEF_DIR = f'{REPO}/relief'
OUT_DIR = f'{REPO}/results'
import sys, os; sys.path.insert(0, RELIEF_DIR); os.makedirs(OUT_DIR, exist_ok=True); os.chdir(INPUT_DIR)
import geopandas as gpd, pandas as pd, numpy as np, iduedu as ie
from objectnat import get_service_provision, get_stepped_graph_isochrones
import mountain_speed as ms
terr = gpd.read_file('territory_graph_buffer30km.geojson')
settl = gpd.read_parquet('settlements_demand.parquet').set_index('id')
hosp = gpd.read_parquet('hospitals_services.parquet').set_index('id')
hosp_rep = gpd.read_file('hospitals_services_republican.geojson').set_index('id')
origins = gpd.read_file('isochrone_origins.geojson')""")
md("""## 1. Граф: дороги OSM, включая `highway=track`
Стандартный фильтр `drive` в IduEdu исключает `track`, а в горах Алтая на них держится часть сёл. Сохраняем теги `surface`, `tracktype`.""")
code("""g = ie.get_drive_graph(territory=terr, network_type='custom', custom_filter=ms.DRIVE_WITH_TRACKS,
                       osm_edge_tags=['highway','surface','tracktype','smoothness','name'])
g.write(f'{OUT_DIR}/altai_drive_flat.urbangraph')
print(g); g.edges_gdf['highway'].astype(str).value_counts().head(12)""")
md("""## 2. Поправка на рельеф, кривые и покрытие
Скачиваются нужные тайлы Copernicus DEM (≈30–40 МБ каждый, всего ~30 тайлов).""")
code("""gm, rep = ms.adjust_graph(g.copy(), dem_dir=f'{OUT_DIR}/dem')
print(rep)
gm.write(f'{OUT_DIR}/altai_drive_mountain.urbangraph')
gm.edges_gdf[['highway','surface','length_meter','time_min_flat','time_min','grade_max','min_radius_m','v_avg_kmh']].describe()""")
md("""## 3. Калибровка по эталонным временам
Заполните `ref_min` в `calibration_pairs.csv` (время по Яндекс/2ГИС без пробок, ссылки в столбце `yandex`). Если медианное отношение заметно отличается от 1, задайте `global_k` и повторите шаг 2.""")
code("""pairs = pd.read_csv(f'{RELIEF_DIR}/calibration_pairs.csv')
if pairs.ref_min.notna().any():
    p = pairs.dropna(subset=['ref_min'])
    for name, G in [('flat', g), ('mountain', gm)]:
        tab, k = ms.calibrate(G, p); print(name, 'median ref/model =', round(k, 2)); display(tab[['name','ref_min','model_min','ratio']])
    # пример: gm, rep = ms.adjust_graph(g.copy(), dem_dir=f'{OUT_DIR}/dem', params={'global_k': k})
else:
    print('Заполните ref_min')""")
md("## 4. OD-матрицы НП × больницы")
code("os.chdir(OUT_DIR)")
code("""def od(G, dest):
    m = G.od_matrix(gdf_origins=settl, gdf_destinations=dest, weight='time_min')
    if hasattr(m, 'sparse'): m = m.sparse.to_dense()   # od_matrix отдаёт sparse, NaN = недостижимо
    return m.astype(float).fillna(1e5)
OD = {}
for name, G in [('flat', g), ('mountain', gm)]:
    OD[name, 'A'] = od(G, hosp); OD[name, 'B'] = od(G, hosp_rep)
    OD[name, 'A'].to_parquet(f'od_{name}_all_hospitals.parquet')
print({k: v.shape for k, v in OD.items()})""")
md("## 5. Обеспеченность: А — 11 больниц, 60 мин; Б — Республиканская, 120 мин")
code("""rows, res = [], {}
for name in ['flat', 'mountain']:
    for sc, S, thr in [('A', hosp, 60), ('B', hosp_rep, 120)]:
        r = get_service_provision(buildings=settl, distance_matrix=OD[name, sc], services=S, threshold=thr, seed=42)
        d = r.demand_rows; res[name, sc] = d
        pop = settl['demand']; within = (OD[name, sc].min(axis=1) <= thr)
        rows.append(dict(graph=name, scenario=sc, threshold=thr,
                         pop_within_share=round(pop[within].sum()/pop.sum()*100, 1),
                         provision_mean=round((d.provision_value*pop).sum()/pop.sum(), 3),
                         settl_outside=int((~within).sum())))
        settl.join(d.add_prefix(f'{sc}_')).to_file(f'provision_{name}_{sc}.geojson', driver='GeoJSON')
summary = pd.DataFrame(rows); summary.to_csv('provision_summary.csv', index=False); summary""")
md("## 6. Разница «плоский vs горный» по НП")
code("""cmp = settl[['name','mo','pop_2025_est','geometry']].copy()
for sc in ['A','B']:
    cmp[f'tmin_flat_{sc}'] = OD['flat', sc].min(axis=1); cmp[f'tmin_mount_{sc}'] = OD['mountain', sc].min(axis=1)
cmp['delta_A_min'] = cmp.tmin_mount_A - cmp.tmin_flat_A
cmp.to_file('time_to_hospital_flat_vs_mountain.geojson', driver='GeoJSON')
cmp.sort_values('delta_A_min', ascending=False).head(15)[['name','mo','tmin_flat_A','tmin_mount_A','delta_A_min']]""")
md("## 7. Изохроны 30/60/90 мин от Горно-Алтайска и от больниц (горный граф)")
code("""iso = get_stepped_graph_isochrones(gm, gdf_origins=origins.iloc[[0]], weight_value_cutoff=90, step=30, geometry_type='radius')
iso.to_file('isochrones_gorno_altaysk_mountain.geojson', driver='GeoJSON')
iso_h = get_stepped_graph_isochrones(gm, gdf_origins=hosp.reset_index(), weight_value_cutoff=60, step=30, geometry_type='radius')
iso_h.to_file('isochrones_hospitals_mountain.geojson', driver='GeoJSON')
iso.plot(alpha=.4)""")
md("## 8. Выгрузка результатов")
code("""!zip -q results_mountain.zip *.geojson *.csv od_*.parquet
print('Готово: results_mountain.zip')""")
nb.cells=C; nbf.write(nb,'altai_access_mountain.ipynb')

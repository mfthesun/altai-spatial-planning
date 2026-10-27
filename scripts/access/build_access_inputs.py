import pandas as pd, geopandas as gpd, json
from shapely.geometry import Point
from shapely.ops import unary_union
import os
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
RAW = os.environ.get('ALTAI_RAW', str(REPO / 'data' / 'raw')) + '/'
B = str(REPO / 'data' / 'access_inputs') + '/'; O = B
# boundary
bd=gpd.read_file(B+'altai_boundary.geojson').to_crs(4326)
bd=bd[['osm_id','name','geometry']]; bd['name']='Республика Алтай'
bd.to_file(O+'altai_boundary.geojson',driver='GeoJSON')
# graph territory: boundary + 30 km buffer (captures Бийск ~25 km beyond border, Артыбаш/Телецкое shore etc.)
b3=bd.to_crs(32645); from shapely.geometry import LineString
corr=gpd.GeoSeries([LineString([(85.21,52.54),(85.70,52.42),(85.90,52.10),(85.96,51.96)])],crs=4326).to_crs(32645).buffer(15000)
terr=gpd.GeoDataFrame({'name':['РА + буфер 30 км + коридор Бийск (Р-256)']},geometry=[b3.buffer(30000).union_all().union(corr.union_all())],crs=32645).to_crs(4326)
terr.to_file(O+'territory_graph_buffer30km.geojson',driver='GeoJSON')
# settlements
d=pd.read_csv(RAW + 'allsett/data_allsettlements_anon_156_v20260925.csv',sep=';',usecols=range(12),dtype=str)
n=d[(d.region=='Республика Алтай')&(d.object_level=='Населенный пункт')].copy()
n['population']=pd.to_numeric(n.population).astype(int)
for c in ['latitude','longitude']: n[c]=n[c].astype(float)
n['oktmo_mo']=n.oktmo.str[:5]+'000'
mo=pd.read_csv(str(REPO / 'data' / 'dataset_v3' / 'mo_summary.csv'),sep=';',dtype={'oktmo':str})[['oktmo','mo','Население 1.01.2025, чел.']]
mo.columns=['oktmo_mo','mo','pop_mo_2025']
n=n.merge(mo,on='oktmo_mo',how='left')
k=n.groupby('oktmo_mo').population.transform('sum')
n['pop_2025_est']=(n.population*n.pop_mo_2025/k).round().astype(int)
BEDS_GENERAL=1148  # Республиканская 645 + 10 РБ 503 (СТП, табл. Ш.7.5)
TOTAL=int(n.pop_2025_est.sum())
rate=BEDS_GENERAL/TOTAL*1000
n['demand_beds']=(n.pop_2025_est*rate/1000).round(3)
n['demand']=n.pop_2025_est   # для provision в "людях"
n=n.reset_index(drop=True); n.insert(0,'id',n.index+1)
sg=gpd.GeoDataFrame(n[['id','object_name','mo','oktmo','oktmo_mo','mun_lower','population','pop_2025_est','demand','demand_beds','latitude','longitude']].rename(columns={'object_name':'name','population':'pop_2020'}),
   geometry=[Point(x,y) for x,y in zip(n.longitude,n.latitude)],crs=4326)
sg.to_file(O+'settlements_demand.geojson',driver='GeoJSON'); sg.to_parquet(O+'settlements_demand.parquet')
# hospitals (СТП табл. Ш.7.4–Ш.7.5, сверено со сканом стр. 131–136); координаты = точка НП, адрес для уточнения
H=[('Республиканская больница','г. Горно-Алтайск','г. Горно-Алтайск, пр. Коммунистический, 120–140','республиканская',645,1300),
('Майминская РБ','село Майма','с. Майма, ул. Строителей, 6','районная',72,168),
('Чойская РБ','село Чоя','с. Гусевка, ул. 40 лет Победы, 2а','районная',20,116),
('Турочакская РБ','село Турочак','с. Турочак, ул. Набережная, 1','районная',36,222),
('Шебалинская РБ','село Шебалино','с. Шебалино, ул. Федорова, 24','районная',53,250),
('Онгудайская РБ','село Онгудай','с. Онгудай, ул. Космонавтов, 84','районная',56,310),
('Улаганская РБ','село Улаган','с. Улаган, ул. Больничная, 30','районная',46,150),
('Кош-Агачская РБ','село Кош-Агач','с. Кош-Агач, ул. Медицинская, 3','районная',81,504),
('Усть-Канская РБ','село Усть-Кан','с. Усть-Кан, ул. Юбилейная, 3','районная',43,212),
('Усть-Коксинская РБ','село Усть-Кокса','с. Усть-Кокса, ул. Советская, 153','районная',50,207),
('Чемальская РБ','село Чемал','с. Чемал, ул. Чемальская, 4','районная',46,255)]
h=pd.DataFrame(H,columns=['name','settlement','address','level','beds','visits_shift'])
h=h.merge(n[['object_name','oktmo_mo','mo','latitude','longitude']].rename(columns={'object_name':'settlement'}),on='settlement',how='left')
assert h.latitude.notna().all()
h['capacity']=(h.beds*1000/rate).round().astype(int)   # ёмкость в жителях при региональной обеспеченности
h['capacity_beds']=h.beds
h['scenario_A_60min']=True
h['scenario_B_120min']=h.level.eq('республиканская')
OSM={'Республиканская больница':(51.9594991,85.9200243,'way/235877888'),'Майминская РБ':(52.0010714,85.8886047,'way/742194220'),
'Чойская РБ':(52.0171485,86.5392111,'relation/7313060'),'Турочакская РБ':(52.2612486,87.1164636,'way/888702169'),
'Шебалинская РБ':(51.2833673,85.6753670,'way/792502607'),'Онгудайская РБ':(50.7394112,86.1439057,'way/752158593'),
'Улаганская РБ':(50.6292818,87.9625143,'way/925644933'),'Кош-Агачская РБ':(50.0174343,88.6695348,'way/319514918'),
'Усть-Канская РБ':(50.9371768,84.7679132,'way/633820923'),'Усть-Коксинская РБ':(50.2709246,85.6370169,'way/691958030'),
'Чемальская РБ':(51.4190208,85.9965905,'way/416630101')}
from pyproj import Geod; g=Geod(ellps='WGS84')
h['shift_m']=[round(g.inv(lo,la,OSM[n][1],OSM[n][0])[2]) for n,la,lo in zip(h.name,h.latitude,h.longitude)]
h['latitude']=h.name.map(lambda n:OSM[n][0]); h['longitude']=h.name.map(lambda n:OSM[n][1])
h['osm_id']=h.name.map(lambda n:OSM[n][2])
h['coord_source']='OSM amenity=hospital (Nominatim, 27.10.2026), сверено с адресом СТП'
h.insert(0,'id',range(1,len(h)+1))
hg=gpd.GeoDataFrame(h,geometry=[Point(x,y) for x,y in zip(h.longitude,h.latitude)],crs=4326)
hg.to_file(O+'hospitals_services.geojson',driver='GeoJSON'); hg.to_parquet(O+'hospitals_services.parquet')
rep=hg[hg.scenario_B_120min].copy(); rep['capacity']=TOTAL; rep.to_file(O+'hospitals_services_republican.geojson',driver='GeoJSON')
# isochrone origins
orig=[('Горно-Алтайск (центр города)','центр',51.958188,85.96035),
('Аэропорт Горно-Алтайск','транспорт',51.9667,85.8333)]
og=gpd.GeoDataFrame(pd.DataFrame(orig,columns=['name','type','lat','lon']),geometry=[Point(x,y) for _,_,y,x in orig],crs=4326)
og.insert(0,'id',[1,2])
rc=hg[['id','name','mo','geometry']].copy(); rc['type']='больница'
rc.to_file(O+'isochrone_origins_hospitals.geojson',driver='GeoJSON')
# checks
inside=sg.within(bd.union_all()).sum(); hin=hg.within(bd.union_all()).sum()
print(json.dumps(dict(settl=len(sg),pop2020=int(sg.pop_2020.sum()),pop2025=TOTAL,beds=int(h.beds.sum()),beds_rb=int(h.beds[h.level=='районная'].sum()),
 rate_per_1000=round(rate,3),cap_total=int(h.capacity.sum()),settl_inside=int(inside),hosp_inside=int(hin),mo_null=int(sg.mo.isna().sum())),ensure_ascii=False))

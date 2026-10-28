"""Граф дорог для расчётов доступности — шаги 1–2 блокнота relief/altai_access_mountain.ipynb без Colab.

1. Граф OSM (IduEdu, фильтр DRIVE_WITH_TRACKS: с грунтовками track) по территории РА с буфером 30 км.
2. Поправка на рельеф по Copernicus DEM GLO-30 (relief/mountain_speed.py).
Пишет results/altai_drive_flat.urbangraph и results/altai_drive_mountain.urbangraph (в git не входят).
Уже скачанный граф и тайлы рельефа повторно не загружаются.
Запуск из корня репозитория: OVERPASS_URL=<зеркало> python scripts/access/build_graph.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = Path(os.getenv("ALTAI_RESULTS", ROOT / "results"))
RES.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "relief"))

import geopandas as gpd  # noqa: E402  (OVERPASS_URL должен быть задан до импорта iduedu)
import iduedu as ie  # noqa: E402
import mountain_speed as ms  # noqa: E402

terr = gpd.read_file(ROOT / "data" / "access_inputs" / "territory_graph_buffer30km.geojson")
flat_path, mount_path = RES / "altai_drive_flat.urbangraph", RES / "altai_drive_mountain.urbangraph"

if flat_path.exists():
    g = ie.UrbanGraph.read(flat_path)
else:
    g = ie.get_drive_graph(territory=terr, network_type="custom", custom_filter=ms.DRIVE_WITH_TRACKS,
                           osm_edge_tags=["highway", "surface", "tracktype", "smoothness", "name", "ref"])
    g.write(flat_path)
print(g)

if not mount_path.exists():
    gm, rep = ms.adjust_graph(g.copy(), dem_dir=RES / "dem")
    print(rep)
    gm.write(mount_path)
print("готово:", flat_path, mount_path)

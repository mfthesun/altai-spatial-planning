"""Объединяет 55 shp ООПТ с карты ООПТ России (карта.оцзк.рф, выгрузка 28.10.2026) в один слой.

Вход: data/raw/oopt/oopt_shp.zip (в репозиторий не входит, см. data/raw/README.md) —
архив с 55 zip, по одному на ООПТ, внутри shp в EPSG:4326, кодировка UTF-8 (файл .cst).
Выход: data/oopt/oopt_oczk_2026-10-28.geojson (EPSG:4326) с атрибутами реестра и площадью контура.
Запуск из корня репозитория: python scripts/model/merge_oopt_shp.py
"""
import io
import os
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(os.getenv("OOPT_ZIP", ROOT / "data" / "raw" / "oopt" / "oopt_shp.zip"))
OUT = ROOT / "data" / "oopt" / "oopt_oczk_2026-10-28.geojson"
COLS = {"nid": "nid", "title": "name", "sig": "level", "category_t": "category", "status_tit": "status",
        "start_date": "start_date", "area": "area_ha", "agency_tit": "agency"}
LEVEL = {"federal": "Федеральное", "regional": "Региональное", "local": "Местное"}

frames = []
with zipfile.ZipFile(SRC) as outer, tempfile.TemporaryDirectory() as tmp:
    for name in sorted(n for n in outer.namelist() if n.endswith(".zip")):
        dest = Path(tmp) / Path(name).stem
        with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
            for m in inner.namelist():  # только файлы слоя, без путей за пределы папки
                if "/" not in m.strip("/") and Path(m).suffix.lower() in {".shp", ".shx", ".dbf", ".prj", ".cst", ".cpg"}:
                    dest.mkdir(parents=True, exist_ok=True)
                    (dest / m).write_bytes(inner.read(m))
        shp = next(dest.glob("*.shp"))
        cst = shp.with_suffix(".cst")
        enc = cst.read_text().strip() if cst.exists() else "UTF-8"
        frames.append(gpd.read_file(shp, encoding=enc))

g = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs).to_crs(4326)
g = g[list(COLS) + ["geometry"]].rename(columns=COLS)
g["level"] = g["level"].map(LEVEL).fillna(g["level"])
g["start_date"] = pd.to_datetime(g["start_date"]).dt.strftime("%Y-%m-%d")
g["geometry"] = g.geometry.make_valid()
g["area_geom_ha"] = (g.to_crs(32645).area / 1e4).round(2)
g.sort_values("area_ha", ascending=False).to_file(OUT, driver="GeoJSON")
print(f"{len(g)} ООПТ → {OUT.relative_to(ROOT)}; площадь по реестру {g.area_ha.sum():,.0f} га, по контурам {g.area_geom_ha.sum():,.0f} га")

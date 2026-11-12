"""Выделить продолжение Р-256 — A0306 из Shapefile-выгрузки Geofabrik Mongolia.

Запуск: .venv/bin/python scripts/slides/build_mongolia_road.py /path/to/mongolia-261111-free.shp.zip
Источник: https://download.geofabrik.de/asia/mongolia-261111-free.shp.zip (OSM).
"""
import argparse
from pathlib import Path

import geopandas as gpd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive', type=Path)
args = parser.parse_args()
roads = gpd.read_file(f'zip://{args.archive.resolve()}!gis_osm_roads_free_1.shp',
                      bbox=(89, 48.5, 90.6, 49.85))
road = roads[roads.ref.eq('A0306') & roads.fclass.eq('trunk')].copy()
assert len(road) > 0 and road.geometry.is_valid.all()
assert road.total_bounds[1] < 49 and road.total_bounds[3] > 49.6
out = Path(__file__).resolve().parents[2] / 'data/slides/layers/road_mongolia_a0306.geojson'
road.to_file(out, driver='GeoJSON')
print(f'{len(road)} отрезков A0306; {road.to_crs(32645).length.sum()/1000:.1f} км; {out}')

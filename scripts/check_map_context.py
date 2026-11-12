"""Проверка контекстных границ и стыковки дороги без загрузки подложки."""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box

from maptools import _shared_boundaries, context_boundaries

ROOT = Path(__file__).resolve().parents[1]
frame = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 1, 3, 2)], crs=32645)
edges = _shared_boundaries(frame)
assert len(edges) == 1 and edges.iloc[0].length == 1  # общая сторона, без внешнего края и угловой точки

neighbors = gpd.read_file(ROOT / 'data/slides/layers/neighbors_admin1.geojson').to_crs(32645)
border = gpd.read_file(ROOT / 'data/access_inputs/altai_boundary.geojson').to_crs(32645)
for group in [neighbors[neighbors.iso_a2.eq('RU')], neighbors.dissolve(by='iso_a2')]:
    edges = _shared_boundaries(group)
    assert abs(edges.length.sum() - edges.union_all().length) < 1e-6  # нет дублирующихся сторон
fig, ax = plt.subplots()
assert all(key.get_linestyle() == '-' for key in context_boundaries(ax, neighbors, border))
plt.close(fig)

roads = gpd.read_file(ROOT / 'data/slides/layers/roads_main.geojson').to_crs(32645)
mongolia = gpd.read_file(ROOT / 'data/slides/layers/road_mongolia_a0306.geojson').to_crs(32645)
assert len(mongolia) > 0 and mongolia.geometry.is_valid.all()
assert mongolia.geometry.union_all().distance(roads[roads.ref.str.contains('Р-256', na=False)].geometry.union_all()) < 1
print('OK: общие границы без дублей и точек, сплошные линии, A0306 стыкуется с Р-256')

"""Проверка контекстных границ и стыковки дороги без загрузки подложки."""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx
import numpy as np
from shapely.geometry import box

from maptools import _shared_boundaries, _wrap, basemap, context_boundaries, prioritize_map_labels

ROOT = Path(__file__).resolve().parents[1]
assert _wrap('Кош-Агачский район', 8).splitlines() == ['Кош‑Агачский', 'район']
assert '110\u00a0кВ' in _wrap('ПС 110 кВ', 7)
assert '5–40\u00a0МВт' in _wrap('станция, 5–40 МВт', 12)
assert _wrap('https://example.org/map_model_draft.png', 10) == 'https://example.org/map_model_draft.png'
assert _wrap('-15–20 км', 10) == '-15–20\u00a0км'
fig, ax = plt.subplots()
ax.set_xlim(400000, 500000); ax.set_ylim(5500000, 5600000)
original_add = cx.add_basemap
levels = []
def fetch_extent(ax, **kwargs):
    assert ax.get_xlim()[0] < 400000 and ax.get_xlim()[1] > 500000
    assert ax.get_ylim()[0] < 5500000 and ax.get_ylim()[1] > 5600000
    levels.append(kwargs['zoom'])
    tile = np.full((11, 11, 4), (51, 52, 54, 255), dtype=np.uint8) if len(levels) == 1 else np.full((11, 11, 4), 255, dtype=np.uint8)
    ax.imshow(tile)
cx.add_basemap = fetch_extent
try:
    basemap(ax)
    assert ax.get_xlim() == (400000, 500000) and ax.get_ylim() == (5500000, 5600000)
    assert levels[1] == levels[0] - 1 and len(ax.images) == 1
finally:
    cx.add_basemap = original_add
    plt.close(fig)
frame = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 1, 3, 2)], crs=32645)
edges = _shared_boundaries(frame)
assert len(edges) == 1 and edges.iloc[0].length == 1  # общая сторона, без внешнего края и угловой точки

neighbors = gpd.read_file(ROOT / 'data/slides/layers/neighbors_admin1.geojson').to_crs(32645)
shared_tuva_khakassia = neighbors[neighbors.name.eq('Tuva')].geometry.iloc[0].boundary.intersection(
    neighbors[neighbors.name.eq('Khakass')].geometry.iloc[0].boundary)
assert shared_tuva_khakassia.length > 195000  # независимое упрощение оставляло только 161,6 км
border = gpd.read_file(ROOT / 'data/access_inputs/altai_boundary.geojson').to_crs(32645)
for group in [neighbors[neighbors.iso_a2.eq('RU')], neighbors.dissolve(by='iso_a2')]:
    edges = _shared_boundaries(group)
    assert abs(edges.length.sum() - edges.union_all().length) < 1e-6  # нет дублирующихся сторон
fig, ax = plt.subplots()
assert all(key.get_linestyle() == '-' for key in context_boundaries(ax, neighbors, border))
line, = ax.plot([0, 1], [0, 1], zorder=40)
label = ax.text(.5, .5, 'Название', zorder=1)
prioritize_map_labels(fig)
assert label.get_zorder() > line.get_zorder()
plt.close(fig)

roads = gpd.read_file(ROOT / 'data/slides/layers/roads_main.geojson').to_crs(32645)
mongolia = gpd.read_file(ROOT / 'data/slides/layers/road_mongolia_a0306.geojson').to_crs(32645)
assert len(mongolia) > 0 and mongolia.geometry.is_valid.all()
assert mongolia.geometry.union_all().distance(roads[roads.ref.str.contains('Р-256', na=False)].geometry.union_all()) < 1
print('OK: общие границы без дублей и точек, сплошные линии, A0306 стыкуется с Р-256')

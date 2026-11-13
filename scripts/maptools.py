"""Единый макет карт для презентации: поле карты, условные обозначения, указатель севера, линейка.

Все карты одного размера, элементы оформления всегда на одних и тех же местах,
чтобы карты вставлялись в слайды без подгонки. Заголовков на картах нет —
они пишутся в презентации как заголовки слайдов и подписи к рисункам.

    fig, ax = map_figure()
    ... рисуем слои в UTM 45N (EPSG:32645) ...
    finish(fig, ax, extent=(x0, y0, x1, y1), handles=[...], basemap="relief")
    save_map(fig, path)

Подложка обязательна — тайлы Esri без подписей (подписи на карте только наши), варианты в BASEMAPS.
Атрибуция Esri печатается в правом нижнем углу поля карты: это условие использования подложек.

Указатель севера повёрнут на сближение меридианов в центре карты: в UTM 45N сетка
отклоняется от истинного севера на 1–2° на краях республики (центральный меридиан 87° в. д.).
"""
import math
import re
import textwrap
import numpy as np
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.patheffects as pe
import xyzservices.providers as xyz
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrow, Rectangle
from matplotlib.lines import Line2D
from pyproj import Transformer
from shapely import get_parts, line_merge, union_all

FIG_SIZE = (10, 7)                    # дюймы; при DPI 200 — 2000 × 1400 px
DPI = 200
MAP_RECT = (0.01, 0.015, 0.69, 0.97)  # поле карты в долях рисунка: x, y, ширина, высота
LEGEND_ANCHOR = (0.715, 0.985)        # левый верхний угол условных обозначений, доли рисунка
NORTH_LOC = (0.955, 0.875)            # основание стрелки севера, доли поля карты
SCALE_LOC = (0.035, 0.035)            # левый нижний угол линейки, доли поля карты
SCALE_FRAC = 0.25                     # длина линейки — около четверти ширины поля
NICE_KM = [2, 4, 10, 20, 50, 100, 200, 400]  # середина линейки (половина длины) — целое число км
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#ffffff"  # фон слайдов презентации
FEDERAL, REGIONAL, MINOR_ROAD = '#ad401f', '#33637d', '#9c9893'
HALO = [pe.withStroke(linewidth=2.5, foreground=SURFACE)]
TITLE_WRAP, LABEL_WRAP = 34, 34       # символов в строке колонки условных обозначений
ATTR_LOC = (0.995, 0.006)             # правый нижний угол поля карты: атрибуция подложки
font_manager.fontManager.addfont(Path(__file__).resolve().parents[1] / 'assets/fonts/Inter.ttf')
font_manager.fontManager.addfont(Path(__file__).resolve().parents[1] / 'assets/fonts/Inter-Bold.ttf')


def _shared_boundaries(frame):
    edges = frame.geometry.copy()
    for idx, geom in frame.geometry.items():
        shared = geom.boundary.intersection(frame.drop(index=idx).geometry.union_all().boundary)
        edges.loc[idx] = union_all([p for p in get_parts(shared) if p.geom_type in ('LineString', 'MultiLineString')])
    # Общие стороны рисуем один раз, соединяя смежные ребра в длинные линии.
    merged = line_merge(edges[~edges.is_empty].union_all())
    return gpd.GeoSeries(list(get_parts(merged)), crs=frame.crs)


def context_boundaries(ax, neighbors, border):
    """Различимые границы: субъекты РФ, страны и Республика Алтай."""
    assert neighbors.crs == border.crs and neighbors.iso_a2.nunique() >= 3
    halo = [pe.withStroke(linewidth=3.5, foreground=SURFACE)]
    _shared_boundaries(neighbors[neighbors.iso_a2.eq('RU')]).plot(
        ax=ax, color='#626262', lw=.85, ls='-', path_effects=halo, zorder=3.2)
    _shared_boundaries(neighbors.dissolve(by='iso_a2')).plot(
        ax=ax, color='#252525', lw=1.15, ls='-', path_effects=halo, zorder=3.4)
    border.boundary.plot(ax=ax, color=INK, lw=2.0, path_effects=halo, zorder=3.6)
    return [Line2D([], [], color='#626262', lw=.85, ls='-', label='границы субъектов РФ'),
            Line2D([], [], color='#252525', lw=1.15, ls='-', label='государственные границы'),
            Line2D([], [], color=INK, lw=2.0, label='граница Республики Алтай')]

# Подложки Esri только без подписей: все надписи на картах — наши и на русском.
# World Gray Canvas и World Topo Map не подходят: на них английские названия.
BASEMAPS = {  # стиль: (источник тайлов, атрибуция по-русски — правообладатель и источники данных)
    "relief": (xyz.Esri.WorldShadedRelief, "© Esri, World Shaded Relief; источник: Esri"),
    "terrain": (xyz.Esri.WorldTerrain, "© Esri, World Terrain Base; источники: USGS, Esri, TANA, DeLorme, NPS"),
    "imagery": (xyz.Esri.WorldImagery, "© Esri, World Imagery; источники: Esri, i-cubed, USDA, USGS, AEX, GeoEye, "
                                       "Getmapping, Aerogrid, IGN, IGP, UPR-EGP и сообщество пользователей ГИС"),
}


SHORT = re.compile(r"(?<![\w-])([\w№]{1,2}) ")  # слово короче трёх букв не остаётся в конце строки
NUM = re.compile(r"(\d) (?=[^\s—–])")  # число не отрывается от следующего слова или единицы


def _wrap(text, width):
    """Перенос по словам; после коротких слов — неразрывный пробел, «—» не начинает строку."""
    lines = (NUM.sub("\\1\u00a0", SHORT.sub("\\1\u00a0", line)).replace(" —", "\u00a0—") for line in text.split("\n"))
    return "\n".join(textwrap.fill(re.sub(r"(?<=[А-Яа-я])-(?=[А-Яа-я0-9])", "‑", line), width, break_long_words=False, break_on_hyphens=False) for line in lines)


def map_figure():
    """Рисунок стандартного размера с полем карты на стандартном месте."""
    plt.rcParams['font.family'] = 'Inter'
    fig = plt.figure(figsize=FIG_SIZE)
    ax = fig.add_axes(MAP_RECT)
    ax.set_axis_off()
    return fig, ax


def set_extent(ax, x0, y0, x1, y1):
    """Охват карты, расширенный до пропорций поля: масштаб по осям одинаковый, поле не сжимается."""
    fw, fh = ax.figure.get_size_inches()
    box = (MAP_RECT[3] * fh) / (MAP_RECT[2] * fw)  # высота / ширина поля
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if h / w < box:
        h = w * box
    else:
        w = h / box
    ax.set_aspect("auto")
    ax.set_xlim(cx - w / 2, cx + w / 2)
    ax.set_ylim(cy - h / 2, cy + h / 2)


def scale_bar(ax, loc=SCALE_LOC, frac=SCALE_FRAC, segments=4, fontsize=7.5):
    """Линейка из чередующихся чёрно-белых отрезков на светлой подложке; длина — «круглое» число км."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    w, h = x1 - x0, y1 - y0
    km = max([k for k in NICE_KM if k * 1000 <= frac * w] or NICE_KM[:1])
    seg = km * 1000 / segments
    bx, by = x0 + loc[0] * w, y0 + loc[1] * h
    bh = 0.011 * h
    ax.add_patch(Rectangle((bx - 0.015 * w, by - 0.012 * h), km * 1000 + 0.05 * w, bh + 0.055 * h,
                           facecolor=SURFACE, edgecolor="none", alpha=0.85, zorder=19))
    for i in range(segments):
        ax.add_patch(Rectangle((bx + i * seg, by), seg, bh, facecolor=INK if i % 2 == 0 else SURFACE,
                               edgecolor=INK, lw=0.6, zorder=20))
    for i, lab in [(0, "0"), (segments // 2, f"{km / 2:g}"), (segments, f"{km:g} км")]:
        ax.text(bx + i * seg, by + bh * 1.8, lab, ha="center", va="bottom", fontsize=fontsize, color=INK,
                path_effects=HALO, zorder=21)


def north_arrow(ax, crs=32645, loc=NORTH_LOC, size=0.07, fontsize=10):
    """Стрелка на истинный север с буквой «С»."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    lon, lat = Transformer.from_crs(crs, 4326, always_xy=True).transform(cx, cy)
    nx, ny = Transformer.from_crs(4326, crs, always_xy=True).transform(lon, lat + 0.1)
    ang = math.atan2(nx - cx, ny - cy)  # отклонение истинного севера от вертикали карты, рад
    w, h = x1 - x0, y1 - y0
    L = size * h
    bx, by = x0 + loc[0] * w, y0 + loc[1] * h
    dx, dy = L * math.sin(ang), L * math.cos(ang)
    ax.add_patch(FancyArrow(bx, by, dx, dy, width=L * 0.12, head_width=L * 0.42, head_length=L * 0.45,
                            length_includes_head=True, color=INK, zorder=20, path_effects=HALO))
    ax.text(bx + dx * 1.25, by + dy * 1.25, "С", ha="center", va="bottom", fontsize=fontsize, fontweight="bold",
            color=INK, path_effects=HALO, zorder=21)


def basemap(ax, style="relief", crs=32645, alpha=1.0):
    """Подложка Esri под всеми слоями и её атрибуция в правом нижнем углу поля.

    alpha < 1 приглушает подложку для карт с большим числом цветных знаков.
    Zoom подбирается под ширину поля карты в пикселях, чтобы подложка не растягивалась
    (иначе рельеф выходит «мыльным» при сохранении в 2000 px).
    """
    src, attribution = BASEMAPS[style]
    fw, _ = ax.figure.get_size_inches()
    field_px = fw * DPI * MAP_RECT[2]
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    width_m = max(abs(x1 - x0), 1.0)
    zoom = min(12, max(0, math.ceil(math.log2(field_px * 40075016.0 / (256.0 * width_m)))))
    # Запас тайлов закрывает пустые углы мозаики после перепроецирования в UTM.
    ax.set_xlim(x0 - .05 * width_m, x1 + .05 * width_m)
    ax.set_ylim(y0 - .05 * (y1 - y0), y1 + .05 * (y1 - y0))
    cx.add_basemap(ax, crs=f"EPSG:{crs}", source=src, attribution=False, zorder=-10,
                   reset_extent=True, alpha=alpha, zoom=zoom)
    # Пустой серый тайл Esri встречается на одном уровне пирамиды; берем тот же слой уровнем ниже.
    raster = np.asarray(ax.images[-1].get_array())
    if ((raster[..., :3] == (51, 52, 54)).all(axis=-1)).sum() > 100:
        ax.images[-1].remove()
        cx.add_basemap(ax, crs=f"EPSG:{crs}", source=src, attribution=False, zorder=-10,
                       reset_extent=True, alpha=alpha, zoom=max(0, zoom - 1))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.text(*ATTR_LOC, f"Подложка: {attribution}", transform=ax.transAxes, ha="right", va="bottom",
            fontsize=5.5, color=MUTED, path_effects=HALO, zorder=21, wrap=True)


def finish(fig, ax, extent, handles, title="Условные обозначения", crs=32645, basemap_style="relief",
           basemap_alpha=1.0):
    """Охват, подложка, рамка, указатель севера, линейка и условные обозначения — на стандартных местах."""
    set_extent(ax, *extent)
    basemap(ax, basemap_style, crs, basemap_alpha)
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False, edgecolor=MUTED, lw=0.8, zorder=30))
    north_arrow(ax, crs=crs)
    scale_bar(ax)
    for hd in handles:
        hd.set_label(_wrap(hd.get_label(), LABEL_WRAP))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=LEGEND_ANCHOR, frameon=False, fontsize=8,
               title=_wrap(title, TITLE_WRAP), title_fontsize=9, alignment="left", labelspacing=0.7, handlelength=2.2)


def no_yo(fig):
    """В презентации пишем «е» вместо «ё» — во всех надписях рисунка, включая легенду."""
    for t in fig.findobj(lambda a: hasattr(a, "get_text") and hasattr(a, "set_text")):
        s = t.get_text()
        if "ё" in s or "Ё" in s:
            t.set_text(s.replace("ё", "е").replace("Ё", "Е"))


def save_map(fig, path):
    """Без обрезки по содержимому: все карты одного размера, оформление на одних местах."""
    prioritize_map_labels(fig)
    no_yo(fig)
    fig.canvas.draw()
    for legend in fig.legends:
        bounds = legend.get_window_extent(fig.canvas.get_renderer())
        assert fig.bbox.contains(bounds.x0, bounds.y0) and fig.bbox.contains(bounds.x1, bounds.y1), f'Легенда выходит за холст: {path}'
    fig.savefig(path, dpi=DPI)
    plt.close(fig)


def prioritize_map_labels(fig):
    """Надписи поверх геометрии; легенды и другие оси не меняют порядок друг друга."""
    for ax in fig.axes:
        label_layer = max([artist.get_zorder() for artist in ax.collections + ax.lines + ax.patches] + [30]) + 1
        for text in ax.texts:
            text.set_zorder(label_layer)

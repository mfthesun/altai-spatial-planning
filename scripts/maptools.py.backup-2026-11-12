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

import contextily as cx
import matplotlib.patheffects as pe
import xyzservices.providers as xyz
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Rectangle
from pyproj import Transformer

FIG_SIZE = (10, 7)                    # дюймы; при DPI 200 — 2000 × 1400 px
DPI = 200
MAP_RECT = (0.01, 0.015, 0.69, 0.97)  # поле карты в долях рисунка: x, y, ширина, высота
LEGEND_ANCHOR = (0.715, 0.985)        # левый верхний угол условных обозначений, доли рисунка
NORTH_LOC = (0.955, 0.875)            # основание стрелки севера, доли поля карты
SCALE_LOC = (0.035, 0.035)            # левый нижний угол линейки, доли поля карты
SCALE_FRAC = 0.25                     # длина линейки — около четверти ширины поля
NICE_KM = [2, 4, 10, 20, 50, 100, 200, 400]  # середина линейки (половина длины) — целое число км
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#ffffff"  # фон слайдов презентации
HALO = [pe.withStroke(linewidth=2.5, foreground=SURFACE)]
TITLE_WRAP, LABEL_WRAP = 34, 34       # символов в строке колонки условных обозначений
ATTR_LOC = (0.995, 0.006)             # правый нижний угол поля карты: атрибуция подложки
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
    return "\n".join(textwrap.fill(line, width) for line in lines)


def map_figure():
    """Рисунок стандартного размера с полем карты на стандартном месте."""
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
    """
    src, attribution = BASEMAPS[style]
    cx.add_basemap(ax, crs=f"EPSG:{crs}", source=src, attribution=False, zorder=-10, reset_extent=True, alpha=alpha)
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
    no_yo(fig)
    fig.savefig(path, dpi=DPI)
    plt.close(fig)

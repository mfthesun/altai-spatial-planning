"""Оформление карт для презентации: масштабная линейка и указатель севера.

Карты рисуются в метрической проекции (UTM 45N, EPSG:32645), поэтому линейка строится в метрах осей.
Указатель севера повёрнут на сближение меридианов в центре карты: в UTM 45N сетка
отклоняется от истинного севера на 1–2° на краях республики (центральный меридиан 87° в. д.).
"""
import math

import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrow, Rectangle
from pyproj import Transformer

NICE_KM = [2, 4, 10, 20, 50, 100, 200, 400]  # середина линейки (половина длины) — целое число км
INK, SURFACE = "#0b0b0b", "#fcfcfb"
HALO = [pe.withStroke(linewidth=2.5, foreground=SURFACE)]


def scale_bar(ax, loc=(0.04, 0.04), frac=0.22, segments=4, fontsize=7.5):
    """Линейка из чередующихся чёрно-белых отрезков; длина — «круглое» число км, около frac ширины карты.

    loc — левый нижний угол в долях осей.
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    w, h = x1 - x0, y1 - y0
    km = max(k for k in NICE_KM if k * 1000 <= frac * w) if frac * w >= 1000 else 1
    seg = km * 1000 / segments
    bx, by = x0 + loc[0] * w, y0 + loc[1] * h
    bh = 0.012 * h
    for i in range(segments):
        ax.add_patch(Rectangle((bx + i * seg, by), seg, bh, facecolor=INK if i % 2 == 0 else SURFACE,
                               edgecolor=INK, lw=0.6, zorder=20))
    for i, lab in [(0, "0"), (segments // 2, f"{km / 2:g}"), (segments, f"{km:g} км")]:
        ax.text(bx + i * seg, by + bh * 1.8, lab, ha="center", va="bottom", fontsize=fontsize, color=INK,
                path_effects=HALO, zorder=21)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)


def north_arrow(ax, crs=32645, loc=(0.94, 0.90), size=0.07, fontsize=10):
    """Стрелка на истинный север с буквой «С». loc — основание стрелки в долях осей, size — длина в долях высоты."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    to_ll = Transformer.from_crs(crs, 4326, always_xy=True)
    to_xy = Transformer.from_crs(4326, crs, always_xy=True)
    lon, lat = to_ll.transform(cx, cy)
    nx, ny = to_xy.transform(lon, lat + 0.1)
    ang = math.atan2(nx - cx, ny - cy)  # отклонение истинного севера от вертикали карты, рад
    w, h = x1 - x0, y1 - y0
    L = size * h
    bx, by = x0 + loc[0] * w, y0 + loc[1] * h
    dx, dy = L * math.sin(ang), L * math.cos(ang)
    ax.add_patch(FancyArrow(bx, by, dx, dy, width=L * 0.12, head_width=L * 0.42, head_length=L * 0.45,
                            length_includes_head=True, color=INK, zorder=20))
    ax.text(bx + dx * 1.25, by + dy * 1.25, "С", ha="center", va="bottom", fontsize=fontsize, fontweight="bold",
            color=INK, path_effects=HALO, zorder=21)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)

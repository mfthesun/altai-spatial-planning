"""Опорный план, дорожная сеть, межрегиональные связи и сеть команды."""

from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from maptools import FEDERAL, REGIONAL, MINOR_ROAD, HALO, INK, context_boundaries, finish, map_figure, save_map

DATA = ROOT / 'data'
OUT = DATA / 'slides'
CRS = 32645
TOURISM = '#853483'
ECONOMY = '#096953'
PROTECTED = '#4e9464'


def geo(path):
    return gpd.read_file(DATA / path).to_crs(CRS)


def points(table):
    return gpd.GeoDataFrame(
        table, geometry=gpd.points_from_xy(table.longitude, table.latitude), crs=4326
    ).to_crs(CRS)


def symbol(marker, color, label, fill=None):
    return Line2D([], [], marker=marker, ls='', ms=6, mec=color, mfc=('none' if marker == 'o' and color == INK else fill or color), label=label)


def mark(ax, geometry, label, color=INK, marker='o', offset=(4, 4), size=23, leader=False):
    plain_settlement = marker == 'o' and color == INK
    ax.scatter(geometry.x, geometry.y, marker=marker, s=size,
               facecolors='none' if plain_settlement else color,
               edgecolors=color if plain_settlement else 'white', linewidths=.65, zorder=8)
    if label:
        ax.annotate(label, (geometry.x, geometry.y), xytext=offset, textcoords='offset points',
                    color=color, fontsize=7.3, path_effects=HALO,
                    ha='right' if offset[0] < 0 else 'left', zorder=10,
                    arrowprops={'arrowstyle': '-', 'color': color, 'lw': .65,
                                'shrinkA': 2, 'shrinkB': 3} if leader else None)


def main():
    border = geo('access_inputs/altai_boundary.geojson')
    mo = geo('slides/layers/mo_boundaries.geojson')
    roads = geo('slides/layers/roads_main.geojson')
    federal = roads.ref.fillna('').str.contains('Р-256', regex=False)
    axes = geo('model/layers/axes_secondary.geojson')
    st = points(pd.read_csv(DATA / 'dataset_v3/settlements.csv', sep=';'))
    names = st.set_index('settlement').geometry
    onp = points(pd.read_csv(DATA / 'onp_candidates.csv'))
    x0, y0, x1, y1 = border.total_bounds
    interior = (x0 - 26000, y0 - 24000, x1 + 24000, y1 + 27000)
    road_keys = [
        Line2D([], [], color=FEDERAL, lw=1.8, label='Р-256 и подъезд к Телецкому озеру; A0306 в Монголии'),
        Line2D([], [], color=REGIONAL, lw=1.1, label='Основные региональные направления'),
        Line2D([], [], color=MINOR_ROAD, lw=.7, label='Другие магистральные дороги OSM'),
    ]

    def base(external=False):
        fig, ax = map_figure()
        if external:
            context_boundaries(ax, geo('slides/layers/neighbors_admin1.geojson'), border)
            geo('slides/layers/r256_barnaul.geojson').plot(ax=ax, color=FEDERAL, lw=1.65, zorder=4)
        else:
            mo.boundary.plot(ax=ax, color='#8b8a83', lw=.45, zorder=1)
        connector = roads.ref.fillna('').str.contains('84К-102|32[КР]-589')
        roads[~(federal | connector)].plot(ax=ax, color=MINOR_ROAD, lw=.65, zorder=2)
        roads[connector].plot(ax=ax, color=REGIONAL, lw=1.1, zorder=3)
        axes.plot(ax=ax, color=REGIONAL, lw=1.1, zorder=3)
        roads[federal].plot(ax=ax, color=FEDERAL, lw=1.65, zorder=4)
        geo('slides/layers/road_mongolia_a0306.geojson').plot(ax=ax, color=FEDERAL, lw=1.65, zorder=4)
        if not external:
            border.boundary.plot(ax=ax, color=INK, lw=.95, zorder=2)
        return fig, ax

    def save(fig, ax, extent, handles, name):
        finish(fig, ax, extent, handles, basemap_alpha=.5)
        save_map(fig, OUT / f'map_{name}.png')

    def settlement(name):
        return names.loc['г. Горно-Алтайск' if name == 'Горно-Алтайск' else f'село {name}']

    fig, ax = base()
    for name, offset in {
        'Горно-Алтайск': (-5, 8), 'Чемал': (4, -10), 'Турочак': (-5, 6),
        'Артыбаш': (4, -8), 'Усть-Кан': (-4, 5), 'Онгудай': (4, 4),
        'Усть-Кокса': (-4, -10), 'Акташ': (-5, 8), 'Улаган': (4, 6),
        'Кош-Агач': (-6, 5), 'Чоя': (-4, 9),
    }.items():
        mark(ax, settlement(name), name, offset=offset)
    checkpoint = points(pd.read_csv(OUT / 'interregional_points.csv'))
    checkpoint = checkpoint[checkpoint.kind.eq('checkpoint')].iloc[0].geometry
    mark(ax, checkpoint, 'МАПП Ташанта\nвыход в Монголию', FEDERAL, 'D', (-8, -18), 38, leader=True)
    save(fig, ax, interior, road_keys + [symbol('o', INK, 'Населенный пункт / развилка'),
         symbol('D', FEDERAL, 'Международный пункт пропуска')],
         'roads_course')

    fig, ax = base()
    st.plot(ax=ax, facecolor='none', edgecolor='#77877f', markersize=st.population.clip(lower=1).pow(.48)*.36,
            lw=.5, alpha=.68, zorder=5)
    for name, label, offset in [
        ('Горно-Алтайск', 'Горно-Алтайск — Майма', (-4, 10)),
        ('Усть-Кан', 'Усть-Кан', (-5, 5)), ('Онгудай', 'Онгудай', (4, 5)),
        ('Усть-Кокса', 'Усть-Кокса', (-4, -10)), ('Кош-Агач', 'Кош-Агач', (-5, 6)),
    ]:
        mark(ax, settlement(name), label, ECONOMY, 's', offset, 38)
    for name, label, offset in [
        ('Манжерок', 'Курорт «Манжерок»', (-8, -5)), ('Чемал', 'Чемал', (6, -6)),
        ('Артыбаш', 'Артыбаш — Иогач', (4, 4)),
        ('Тюнгур', 'Тюнгур / Белуха', (4, 4)), ('Акташ', 'Акташ / Чуйский тракт', (-5, 5)),
    ]:
        mark(ax, settlement(name), label, TOURISM, '^', offset, 43)
    save(fig, ax, interior, road_keys + [
        symbol('o', '#77877f', 'населённые пункты (размер — население)', 'none'),
        symbol('s', ECONOMY, 'экономический узел'),
        symbol('^', TOURISM, 'туристический узел'),
    ], 'support_plan')

    fig, ax = base()
    st.plot(ax=ax, facecolor='none', edgecolor='#8e948f', markersize=5, lw=.5, alpha=.55, zorder=5)
    official = pd.read_csv(OUT / 'onp_decree_222.csv', dtype={'oktmo': str})
    official = official.merge(st.assign(oktmo=st.oktmo.astype(str)), on='oktmo',
                                validate='one_to_one', how='left', indicator=True)
    assert (official._merge == 'both').all(), 'Не все ОНП сопоставлены по ОКТМО'
    official = gpd.GeoDataFrame(official, geometry='geometry', crs=CRS)
    additions = onp[~onp.oktmo.astype(str).isin(official.oktmo)]
    assert (len(official), len(additions)) == (9, 6)
    official.plot(ax=ax, color=ECONOMY, markersize=32, edgecolor='white', lw=.5, zorder=7)
    onp_key = [symbol('o', ECONOMY, 'сельские ОНП по постановлению № 222 (9)'),
               symbol('D', FEDERAL, 'опорные центры (6)', 'white')]
    export_comparison(official, onp, additions)
    additions.plot(ax=ax, facecolor='none', edgecolor=FEDERAL, marker='D', markersize=46, lw=1.1, zorder=6)
    for name, offset in {
        'Акташ': (-10, 10), 'Кебезень': (18, 18), 'Каракокша': (24, -20),
        'Иогач': (-24, 24), 'Беляши': (-10, 8), 'Катанда': (10, -10),
    }.items():
        p = onp.loc[onp['name'].str.endswith(name), 'geometry'].iloc[0]
        ax.annotate(name, (p.x, p.y), xytext=offset, textcoords='offset points',
                    fontsize=7.3, ha='right' if offset[0] < 0 else 'left',
                    path_effects=HALO, zorder=10,
                    arrowprops={'arrowstyle': '-', 'color': FEDERAL, 'lw': .65,
                                'shrinkA': 2, 'shrinkB': 3})
    save(fig, ax, interior, onp_key + [symbol('o', '#8e948f', 'Другие населенные пункты', 'none')]
         + road_keys, 'onp_course')

    # Резервная карта: те же ОНП и дороги, плюс сохраненный расчет доступности.
    access = geo('access_results/time_to_hospital.geojson')
    isolated = access[access.tmin_mount_A > 60]
    assert len(isolated) == 56 and round(isolated.pop_2025_est.sum()) == 16479
    fig, ax = base()
    st.plot(ax=ax, facecolor='none', edgecolor='#8e948f', markersize=5, lw=.5, zorder=5)
    isolated.plot(ax=ax, facecolor='none', edgecolor=FEDERAL, markersize=48, lw=1.1, zorder=6)
    official.plot(ax=ax, color=ECONOMY, markersize=32, edgecolor='white', lw=.5, zorder=7)
    additions.plot(ax=ax, facecolor='none', edgecolor=FEDERAL, marker='D', markersize=46, lw=1.1, zorder=7)
    for name, offset in [('Горно-Алтайск', (-5, 8)), ('Усть-Кан', (-5, 5)), ('Кош-Агач', (-6, 5))]:
        mark(ax, settlement(name), name, offset=offset, size=15)
    save(fig, ax, interior, [symbol('o', FEDERAL, 'вне 60 мин от больницы: 56 НП', 'none')]
         + onp_key + road_keys, 'settlement_vulnerability')

    fig, ax = base(external=True)
    for lon, lat, label in [
        (84.95, 53.17, 'АЛТАЙСКИЙ КРАЙ'), (87.20, 52.96, 'КУЗБАСС'),
        (89.52, 50.85, 'ТЫВА'), (90.05, 52.06, 'ХАКАСИЯ'),
        (83.96, 49.77, 'КАЗАХСТАН'), (88.64, 49.06, 'МОНГОЛИЯ'),
        (87.6, 47.9, 'КИТАЙ'),
    ]:
        point = points(pd.DataFrame({'longitude': [lon], 'latitude': [lat]})).geometry.iloc[0]
        ax.text(point.x, point.y, label, color='#52514e', fontsize=7.4, ha='center',
                path_effects=HALO, clip_on=True, zorder=10)
    protected = geo('oopt/oopt_oczk_2026-10-28.geojson')
    katun = protected[protected['name'].eq('Катунский')]
    assert len(katun) == 1
    katun.plot(ax=ax, color=PROTECTED, edgecolor=ECONOMY, alpha=.76, lw=.7, zorder=3)
    # Трансграничные территории сотрудничества — реальные границы вместо стрелок.
    OOPT_HATCH = dict(facecolor='none', edgecolor=PROTECTED, hatch='///', lw=.7, zorder=3)
    kh = geo('slides/layers/coop_khakassia_oopt.geojson')
    kh.plot(ax=ax, **OOPT_HATCH)
    for nm, short in [('Шорский национальный парк', 'Шорский нацпарк'),
                      ('Хакасский заповедник', 'Хакасский заповедник')]:
        g = kh[kh.name.eq(nm)]
        if len(g):
            p = g.geometry.iloc[0].representative_point()
            dx, dy = (-25000, 45000) if nm == 'Шорский национальный парк' else (20000, 18000)
            short = short.replace(' нацпарк', '\nнацпарк').replace(' заповедник', '\nзаповедник')
            ax.text(p.x + dx, p.y + dy, short, fontsize=6.4, color='#2c5a3e', ha='center',
                    path_effects=HALO, zorder=10)
    for fname in ('coop_mongolia_oopt', 'coop_kazakhstan_oopt', 'coop_china_oopt'):
        g = geo(f'slides/layers/{fname}.geojson')
        if len(g):
            g.plot(ax=ax, **OOPT_HATCH)
    for fname, short in [('coop_mongolia_oopt', 'Алтай-Таван-Богд'),
                         ('coop_kazakhstan_oopt', 'Катон-Карагай')]:
        g = geo(f'slides/layers/{fname}.geojson')
        if len(g):
            p = g.geometry.iloc[0].representative_point()
            dx, dy = (30000, -60000) if fname == 'coop_mongolia_oopt' else (-20000, 10000)
            ax.annotate(short, (p.x, p.y), (p.x + dx, p.y + dy), fontsize=6.4,
                        color='#2c5a3e', ha='left' if dx > 0 else 'right', path_effects=HALO,
                        arrowprops={'arrowstyle': '-', 'color': '#2c5a3e', 'lw': .5}, zorder=10)
    ARCH = '#612e78'
    ty = geo('slides/layers/coop_tyva_archaeology.geojson')
    ker = ty[ty.name.eq('керескур')]
    named = ty[~ty.name.eq('керескур')]
    ax.scatter(ker.geometry.x, ker.geometry.y, s=6, color=ARCH, zorder=4)
    ax.scatter(named.geometry.x, named.geometry.y, s=30, marker='D', facecolor='none',
               edgecolor=ARCH, lw=.9, zorder=5)
    kp = ker.geometry.union_all().representative_point()
    ax.text(kp.x - 6000, kp.y - 28000, 'керескуры', fontsize=6.4, color=ARCH, ha='right',
            style='italic', path_effects=HALO, zorder=5)
    outside = points(pd.read_csv(OUT / 'interregional_points.csv'))
    outside = outside[outside.kind != 'protected']  # ООПТ — полигонами, не точками
    for row in outside.itertuples():
        style = {
            'airport': (REGIONAL, '^', 40), 'hub': (REGIONAL, 's', 30),
            'settlement': (INK, 'o', 15), 'protected': (ECONOMY, 'D', 30),
            'checkpoint': (FEDERAL, 'D', 30),
        }[row.kind]
        mark(ax, row.geometry, row.label.replace('|', '\n'), style[0], style[1],
             (row.dx, row.dy), style[2], leader=row.label == 'Аэропорт|Горно-Алтайск')
    bounds = gpd.GeoSeries(pd.concat([kh.geometry, roads.geometry], ignore_index=True), crs=CRS).total_bounds
    extent = (min(x0-140000, bounds[0]-20000), y0-150000,
              max(x1+105000, bounds[2]+20000), max(y1+162000, bounds[3]+20000))
    assert extent[0] < bounds[0] and extent[2] > bounds[2] and extent[3] > bounds[3]
    save(fig, ax, extent, road_keys + [
        symbol('^', REGIONAL, 'Аэропорт'), symbol('s', REGIONAL, 'Транспортный узел'),
        symbol('D', FEDERAL, 'Пункт пропуска'),
        Patch(facecolor=PROTECTED, alpha=.76, edgecolor=ECONOMY, label='Катунский заповедник'),
        Patch(facecolor='none', edgecolor=PROTECTED, hatch='///', label='ООПТ соседних регионов и стран'),
        Line2D([], [], marker='o', ls='', ms=4, color=ARCH, label='керескуры у Кокори (Республика Алтай)'),
        Line2D([], [], marker='D', ls='', ms=4, mfc='none', mec=ARCH, label='другие памятники археологии (OSM)'),
        Line2D([], [], color='#626262', lw=.85, ls='-', label='границы субъектов РФ'),
        Line2D([], [], color='#252525', lw=1.15, ls='-', label='государственные границы'),
        Line2D([], [], color=INK, lw=2.0, label='граница Республики Алтай'),
    ], 'interregional')


def export_comparison(official, onp, additions):
    both = official.oktmo.isin(onp.oktmo.astype(str))
    result = pd.concat([
        official[['oktmo', 'settlement', 'mo', 'pdf_page']].assign(
            status=both.map({True: 'оба перечня', False: 'только постановление № 222'})
        ),
        additions.rename(columns={'name': 'settlement'})[['oktmo', 'settlement', 'mo', 'основание']]
        .assign(status='перспективный опорный центр команды'),
    ], ignore_index=True)
    result['pdf_page'] = result.pdf_page.astype('Int64')
    result.to_csv(OUT / 'onp_comparison.csv', index=False)


if __name__ == '__main__':
    main()

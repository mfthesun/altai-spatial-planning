"""
mountain_speed.py — поправка времени движения на рельеф, извилистость и покрытие
для графа IduEdu (UrbanGraph, тип drive). Республика Алтай, курс «Пространственное планирование».

Идея:
  1. Высоты: Copernicus DEM GLO-30 (спутниковая радарная съёмка TanDEM-X, 30 м,
     открытый бакет AWS s3://copernicus-dem-30m, без регистрации).
  2. По каждому ребру графа точки через 25 м: высота, уклон, радиус кривизны.
  3. Скорость на каждом 25-метровом отрезке:
        v = min(v_покрытия, v_кривой) * k_уклона
     где v_кривой = sqrt(127 * R * (mu + i_вираж))   [формула устойчивости на кривой,
     R = V² / 127(μ + i) — стандарт проектирования дорог].
  4. Время ребра = сумма длин отрезков / скоростей; для двусторонних рёбер —
     среднее «туда» и «обратно» (UrbanGraph хранит один вес на ребро).

Использование в Colab (после get_drive_graph, до od_matrix):

    !pip install iduedu rasterio
    from mountain_speed import DRIVE_WITH_TRACKS, adjust_graph, calibrate
    g = ie.get_drive_graph(territory=terr, network_type="custom",
                           custom_filter=DRIVE_WITH_TRACKS,
                           osm_edge_tags=["highway","surface","tracktype","smoothness","name"])
    g, report = adjust_graph(g, dem_dir="dem")
    g.write("altai_drive_mountain.urbangraph")

Все коэффициенты вынесены в PARAMS и подлежат калибровке (функция calibrate).
"""
from __future__ import annotations

import math
import os
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from pyproj import Transformer

# --- фильтр Overpass: как drive в IduEdu, но БЕЗ исключения highway=track ---------------
DRIVE_WITH_TRACKS = (
    '["highway"]["area"!~"yes"]["access"!~"private"]'
    '["highway"!~"abandoned|bridleway|bus_guideway|construction|corridor|cycleway|elevator|'
    'escalator|footway|no|path|pedestrian|planned|platform|proposed|raceway|razed|service|steps"]'
    '["tracktype"!~"grade5"]'
    '["motor_vehicle"!~"no"]["motorcar"!~"no"]'
    '["service"!~"alley|driveway|emergency_access|parking|parking_aisle|private"]'
)

PARAMS = dict(
    step_m=25.0,            # шаг дискретизации ребра
    smooth_pts=5,           # окно медианного сглаживания высот (DSM-шум от леса)
    grade_base_m=100.0,     # база расчёта уклона
    chord_pts=2,            # радиус по точкам i-k, i, i+k (k*step = 50 м)
    mu=0.15, superelev=0.02,  # сцепление и вираж в формуле кривой
    r_cap=2000.0,           # радиус, выше которого кривая не ограничивает скорость
    up_free=0.04, up_k=4.0, up_min=0.5,      # подъём: штраф сверх 4 %
    down_free=0.06, down_k=3.0, down_min=0.6,  # спуск: штраф сверх 6 %
    global_k=1.0,           # общий калибровочный множитель времени
)

# скорость по классу дороги, км/ч (как в IduEdu) + track
HIGHWAY_KMH = {"motorway": 110, "trunk": 90, "primary": 60, "secondary": 60, "tertiary": 60,
               "unclassified": 40, "residential": 40, "living_street": 20, "track": 25,
               "motorway_link": 90, "trunk_link": 90, "primary_link": 60,
               "secondary_link": 60, "tertiary_link": 60}
# потолок скорости по покрытию, км/ч
SURFACE_CAP = {"asphalt": None, "concrete": None, "paved": None, "paving_stones": 50,
               "compacted": 50, "fine_gravel": 50, "gravel": 45, "unpaved": 35, "pebblestone": 35,
               "dirt": 25, "ground": 25, "earth": 25, "grass": 15, "sand": 15, "mud": 10}
TRACKTYPE_CAP = {"grade1": 45, "grade2": 35, "grade3": 25, "grade4": 15}


# --- Copernicus DEM ------------------------------------------------------------------------
def _tile_name(lat: int, lon: int) -> str:
    ns, ew = ("N" if lat >= 0 else "S"), ("E" if lon >= 0 else "W")
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"


def cop_dem_url(lat: int, lon: int) -> str:
    n = _tile_name(lat, lon)
    return f"https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"


def download_tiles(tiles: set[tuple[int, int]], dem_dir: str | Path) -> dict:
    dem_dir = Path(dem_dir); dem_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for lat, lon in sorted(tiles):
        p = dem_dir / f"{_tile_name(lat, lon)}.tif"
        if not p.exists():
            try:
                urllib.request.urlretrieve(cop_dem_url(lat, lon), p)
            except Exception as e:  # тайла нет (океан) или сеть
                print("нет тайла", lat, lon, e); continue
        paths[(lat, lon)] = p
    return paths


def sample_dem(lon: np.ndarray, lat: np.ndarray, dem_dir="dem") -> np.ndarray:
    import rasterio
    z = np.full(lon.shape, np.nan, dtype="float32")
    tl = np.floor(lat).astype(int); tn = np.floor(lon).astype(int)
    keys = set(zip(tl.tolist(), tn.tolist()))
    paths = download_tiles(keys, dem_dir)
    for (a, b), p in paths.items():
        m = (tl == a) & (tn == b)
        with rasterio.open(p) as src:
            arr = src.read(1)
            r, c = rasterio.transform.rowcol(src.transform, lon[m], lat[m])
            r = np.clip(np.asarray(r), 0, arr.shape[0] - 1); c = np.clip(np.asarray(c), 0, arr.shape[1] - 1)
            z[m] = arr[r, c]
    return z


# --- геометрия -----------------------------------------------------------------------------
def densify(edges: gpd.GeoDataFrame, step: float) -> pd.DataFrame:
    """Точки вдоль каждого ребра с шагом step (CRS графа метрический)."""
    eid, dist, xs, ys = [], [], [], []
    for i, geom in zip(range(len(edges)), edges.geometry.values):
        L = geom.length
        n = max(int(math.ceil(L / step)), 1)
        d = np.linspace(0, L, n + 1)
        pts = [geom.interpolate(x) for x in d]
        eid.append(np.full(n + 1, i)); dist.append(d)
        xs.append([p.x for p in pts]); ys.append([p.y for p in pts])
    return pd.DataFrame({"e": np.concatenate(eid), "d": np.concatenate(dist),
                         "x": np.concatenate(xs), "y": np.concatenate(ys)})


def _radius(x, y, k):
    """Радиус окружности через точки i-k, i, i+k (векторно внутри одного ребра)."""
    R = np.full(len(x), np.inf)
    if len(x) < 2 * k + 1:
        return R
    ax, ay = x[:-2 * k], y[:-2 * k]; bx, by = x[k:-k], y[k:-k]; cx, cy = x[2 * k:], y[2 * k:]
    a = np.hypot(bx - cx, by - cy); b = np.hypot(ax - cx, ay - cy); c = np.hypot(ax - bx, ay - by)
    area2 = np.abs((bx - ax) * (cy - ay) - (cx - ax) * (by - ay))
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(area2 > 1e-6, a * b * c / (2 * area2), np.inf)
    R[k:-k] = r
    return R


def _base_kmh(row) -> float:
    h = row.get("highway")
    if isinstance(h, (list, tuple)):
        h = h[0]
    v = HIGHWAY_KMH.get(h, 40)
    caps = [SURFACE_CAP.get(row.get("surface")), TRACKTYPE_CAP.get(row.get("tracktype"))]
    caps = [c for c in caps if c]
    if h == "track" and not caps:
        caps = [25]
    return float(min([v] + caps))


def _grade_factor(g, P):
    up = np.clip(1 - P["up_k"] * np.maximum(g - P["up_free"], 0), P["up_min"], 1)
    dn = np.clip(1 - P["down_k"] * np.maximum(-g - P["down_free"], 0), P["down_min"], 1)
    return np.where(g >= 0, up, dn)


# --- главное -------------------------------------------------------------------------------
def adjust_graph(graph, dem_dir="dem", params: dict | None = None, inplace=True):
    P = {**PARAMS, **(params or {})}
    g = graph if inplace else graph.copy()
    E = g.edges_gdf
    pts = densify(E, P["step_m"])
    tr = Transformer.from_crs(E.crs, 4326, always_xy=True)
    lon, lat = tr.transform(pts.x.values, pts.y.values)
    pts["z"] = sample_dem(np.asarray(lon), np.asarray(lat), dem_dir)

    base = E.apply(_base_kmh, axis=1).values
    k = P["chord_pts"]; nb = max(int(P["grade_base_m"] / P["step_m"] / 2), 1)
    t_fwd = np.zeros(len(E)); t_bwd = np.zeros(len(E))
    gain = np.zeros(len(E)); loss = np.zeros(len(E)); gmax = np.zeros(len(E)); rmin = np.full(len(E), np.inf)
    for e, grp in pts.groupby("e", sort=True):
        d = grp.d.values; z = pd.Series(grp.z.values).interpolate(limit_direction="both").values
        if np.isnan(z).all():
            z = np.zeros_like(d)
        zs = pd.Series(z).rolling(P["smooth_pts"], center=True, min_periods=1).median().values
        seg = np.diff(d)
        # уклон по базе ±grade_base/2
        idx = np.arange(len(d)); i0 = np.clip(idx - nb, 0, len(d) - 1); i1 = np.clip(idx + nb, 0, len(d) - 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            gp = np.where(d[i1] > d[i0], (zs[i1] - zs[i0]) / (d[i1] - d[i0]), 0.0)
        gs = 0.5 * (gp[:-1] + gp[1:])                     # уклон отрезка
        R = _radius(grp.x.values, grp.y.values, k)
        Rs = np.minimum(R[:-1], R[1:]); Rs = np.where(np.isfinite(Rs), Rs, P["r_cap"])
        vcur = np.sqrt(127 * np.minimum(Rs, P["r_cap"]) * (P["mu"] + P["superelev"]))
        # торможение перед кривой: скользящий минимум ±50 м
        w = max(int(50 / P["step_m"]), 1) * 2 + 1
        vcur = pd.Series(vcur).rolling(w, center=True, min_periods=1).min().values
        v0 = np.minimum(base[e], vcur)
        vf = np.maximum(v0 * _grade_factor(gs, P), 5.0)
        vb = np.maximum(v0 * _grade_factor(-gs, P), 5.0)
        t_fwd[e] = np.sum(seg / (vf * 1000 / 60)); t_bwd[e] = np.sum(seg / (vb * 1000 / 60))
        dz = np.diff(zs); gain[e] = dz[dz > 0].sum(); loss[e] = abs(dz[dz < 0].sum())
        gmax[e] = np.abs(gs).max() if len(gs) else 0; rmin[e] = Rs.min() if len(Rs) else np.inf

    oneway = E["oneway"].astype(bool).values if "oneway" in E else np.zeros(len(E), bool)
    t_new = np.where(oneway, t_fwd, 0.5 * (t_fwd + t_bwd)) * P["global_k"]
    E["time_min_flat"] = E["time_min"].values
    E["time_min"] = np.round(t_new, 4)
    E["elev_gain_m"] = gain.round(1); E["elev_loss_m"] = loss.round(1)
    E["grade_max"] = gmax.round(3); E["min_radius_m"] = np.minimum(rmin, P["r_cap"]).round(0)
    E["v_avg_kmh"] = (E["length_meter"] / 1000 / (E["time_min"] / 60)).round(1)
    g.edges_gdf = E
    g.update_adjacency_matrix(weight="time_min")
    rep = dict(edges=len(E), dem_nan_share=float(np.isnan(pts.z).mean()),
               total_time_ratio=float(E.time_min.sum() / E.time_min_flat.sum()),
               km=float(E.length_meter.sum() / 1000))
    return g, rep


def calibrate(graph, pairs: pd.DataFrame):
    """pairs: колонки name, lon1, lat1, lon2, lat2, ref_min (эталонное время, мин).
    Возвращает таблицу сравнения и медианный коэффициент ref/model."""
    o = gpd.GeoDataFrame(pairs[["name"]], geometry=gpd.points_from_xy(pairs.lon1, pairs.lat1), crs=4326)
    d = gpd.GeoDataFrame(pairs[["name"]], geometry=gpd.points_from_xy(pairs.lon2, pairs.lat2), crs=4326)
    od = graph.od_matrix(gdf_origins=o, gdf_destinations=d, weight="time_min")
    if hasattr(od, "sparse"):
        od = od.sparse.to_dense()
    model = np.array([od.iloc[i, i] for i in range(len(pairs))])
    out = pairs.assign(model_min=model.round(0), ratio=(pairs.ref_min / model).round(2))
    return out, float(np.nanmedian(out.ratio))

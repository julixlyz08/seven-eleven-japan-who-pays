"""Clean the location data for Part 1: stores, population grid, stations.

stores.csv          every OSM convenience store: chain, prefecture, 1 km grid square
population_grid.csv 2020 census population per 1 km grid square (with its centre)
stations.csv        railway stations with daily passengers, latest year in the file

Grid squares use Japan's standard mesh code (8 digits for 1 km), computed from
latitude and longitude, so stores, people and stations can be joined without GIS.
"""
import gzip
import json
import re
import zipfile
import numpy as np
import pandas as pd
from matplotlib.path import Path as Polygon
from scipy.spatial import cKDTree
from config import RAW, PROCESSED

# Chains, checked in this order (e.g. "LAWSON+ポプラ" is a Lawson store)
CHAINS = [
    ("7-Eleven", r"セブン|7.?eleven|seven.?eleven"),
    ("Lawson", r"ローソン|lawson"),
    ("FamilyMart", r"ファミリーマート|family.?mart"),
    ("Ministop", r"ミニストップ|mini.?stop"),
    ("Daily Yamazaki", r"ヤマザキ|yamazaki"),
    ("Seicomart", r"セイコーマート|seico.?mart"),
    ("NewDays", r"newdays|ニューデイズ"),
    ("Poplar", r"ポプラ|poplar|生活彩家"),
    # Chains that no longer exist: their stores became FamilyMart or Lawson (2016-2019),
    # so these are out-of-date map entries
    ("Stale (closed chain)", r"サークル.?k|circle.?k|サンクス|sunkus|セーブオン|save.?on|am.?pm|ココストア|coco.?store"),
]


def mesh_1km(lat, lon):
    lat15, lon100 = np.asarray(lat) * 1.5, np.asarray(lon) - 100
    p, u = np.floor(lat15).astype(int), np.floor(lon100).astype(int)
    q, v = np.floor((lat15 - p) * 8).astype(int), np.floor((lon100 - u) * 8).astype(int)
    r = np.floor(((lat15 - p) * 8 - q) * 10).astype(int)
    w = np.floor(((lon100 - u) * 8 - v) * 10).astype(int)
    return p * 1_000_000 + u * 10_000 + q * 1_000 + v * 100 + r * 10 + w


def mesh_centre(code):
    code = np.asarray(code)
    p, u = code // 1_000_000, code // 10_000 % 100
    q, v, r, w = code // 1_000 % 10, code // 100 % 10, code // 10 % 10, code % 10
    return (p + (q + (r + 0.5) / 10) / 8) / 1.5, 100 + u + (v + (w + 0.5) / 10) / 8


# Prefecture boundaries: point-in-polygon, with the nearest boundary point as a
# fallback for points just off the simplified coastline
geo = json.load(open(RAW / "boundaries" / "japan_prefectures.geojson", encoding="utf-8"))
POLYGONS, VERTICES, VERTEX_PREF = [], [], []
for f in geo["features"]:
    name = re.sub(r"[都府県]$", "", f["properties"]["nam_ja"])
    parts = f["geometry"]["coordinates"]
    parts = parts if f["geometry"]["type"] == "MultiPolygon" else [parts]
    for poly in parts:
        ring = np.array(poly[0])
        POLYGONS.append((name, Polygon(ring), ring.min(axis=0), ring.max(axis=0)))
        VERTICES.append(ring)
        VERTEX_PREF += [name] * len(ring)
VERTEX_TREE = cKDTree(np.vstack(VERTICES))
VERTEX_PREF = np.array(VERTEX_PREF)
assert len({p[0] for p in POLYGONS}) == 47


def prefecture_of(lat, lon):
    pts = np.column_stack([lon, lat])
    out = np.full(len(pts), None, dtype=object)
    for name, poly, lo, hi in POLYGONS:
        box = (pts[:, 0] >= lo[0]) & (pts[:, 0] <= hi[0]) & (pts[:, 1] >= lo[1]) & (pts[:, 1] <= hi[1])
        idx = np.where(box & (out == None))[0]  # noqa: E711
        if len(idx):
            out[idx[poly.contains_points(pts[idx])]] = name
    missing = out == None  # noqa: E711
    out[missing] = VERTEX_PREF[VERTEX_TREE.query(pts[missing])[1]]
    return out, missing.sum()


# 1. Stores ---------------------------------------------------------------------------
elements = json.load(gzip.open(next((RAW / "osm").glob("convenience_stores_*.json.gz")), "rt"))
rows = []
for e in elements:
    t = e.get("tags", {})
    text = " ".join(t.get(k, "") for k in ("brand", "name", "name:ja", "name:en", "operator")).lower()
    chain = next((c for c, pattern in CHAINS if re.search(pattern, text)), "Other / unnamed")
    rows.append({"osm_type": e["type"], "osm_id": e["id"],
                 "lat": e.get("lat", e.get("center", {}).get("lat")),
                 "lon": e.get("lon", e.get("center", {}).get("lon")), "chain": chain})
stores = pd.DataFrame(rows)
stores["mesh"] = mesh_1km(stores["lat"], stores["lon"])

stores["prefecture"], fallback = prefecture_of(stores["lat"].values, stores["lon"].values)
print(f"Stores: {len(stores):,}; placed by nearest boundary (just off the simplified coast): {fallback}")
print(stores["chain"].value_counts().to_string())
stores.to_csv(PROCESSED / "stores.csv", index=False)

# 2. Population grid ------------------------------------------------------------------
frames = []
for path in sorted((RAW / "population_grid").glob("pop1km_*.txt")):
    df = pd.read_csv(path, encoding="shift_jis", skiprows=[1], dtype=str)
    df = df.rename(columns={"KEY_CODE": "mesh", "T001140001": "pop", "T001140010": "pop_15_64",
                            "T001140019": "pop_65_plus", "T001140034": "households",
                            "T001140036": "one_person_households"})
    frames.append(df[["mesh", "pop", "pop_15_64", "pop_65_plus", "households", "one_person_households"]])
grid = pd.concat(frames)
grid["mesh"] = grid["mesh"].astype(int)
# "*" = suppressed for privacy (tiny populations; the count is added to a neighbour)
for col in grid.columns[1:]:
    grid[col] = pd.to_numeric(grid[col], errors="coerce").fillna(0).astype(int)
grid = grid.groupby("mesh", as_index=False).sum()
grid["lat"], grid["lon"] = mesh_centre(grid["mesh"])
grid["prefecture"], _ = prefecture_of(grid["lat"].values, grid["lon"].values)
print(f"\nPopulation grid: {len(grid):,} squares, {grid['pop'].sum() / 1e6:.1f} million people "
      f"(2020 census total: 126.1 million)")
grid.to_csv(PROCESSED / "population_grid.csv", index=False)

# 3. Stations -------------------------------------------------------------------------
with zipfile.ZipFile(next((RAW / "stations").glob("S12-*_GML.zip"))) as z:
    name = next(n for n in z.namelist() if "UTF-8" in n and n.endswith(".geojson"))
    features = json.loads(z.read(name))["features"]
st = []
for f in features:
    props = f["properties"]
    counts = [k for k in props if re.fullmatch(r"S12_\d{3}", k) and int(k[4:]) >= 9 and (int(k[4:]) - 9) % 4 == 0]
    latest = props[max(counts)]
    coords = np.array(f["geometry"]["coordinates"])
    st.append({"station": props["S12_001"], "operator": props["S12_002"], "line": props["S12_003"],
               "lon": coords[:, 0].mean(), "lat": coords[:, 1].mean(), "passengers": latest})
stations = pd.DataFrame(st)
# One operator may list the same station once per line with the same count: keep one
stations = (stations.sort_values("passengers", ascending=False)
            .drop_duplicates(["station", "operator"]).reset_index(drop=True))
stations["passengers"] = stations["passengers"].fillna(0)
stations["mesh"] = mesh_1km(stations["lat"], stations["lon"])
stations["prefecture"], _ = prefecture_of(stations["lat"].values, stations["lon"].values)
print(f"\nStations: {len(stations):,} (station x operator); busiest:")
print(stations.nlargest(5, "passengers")[["station", "operator", "passengers"]].to_string(index=False))
stations.to_csv(PROCESSED / "stations.csv", index=False)

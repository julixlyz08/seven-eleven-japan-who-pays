"""Download 2020 census population on a 1 km grid (e-Stat, statsId T001140).

The grid is Japan's standard mesh system: a "first-level" tile is 2/3 degree of
latitude by 1 degree of longitude, split into 1 km squares. Only tiles that
contain at least one convenience store in OpenStreetMap are downloaded.
"""
import gzip
import io
import json
import time
import zipfile
import requests
from config import RAW, HEADERS

OUT = RAW / "population_grid"
OUT.mkdir(parents=True, exist_ok=True)

stores = json.load(gzip.open(next((RAW / "osm").glob("convenience_stores_*.json.gz")), "rt"))
tiles = set()
for s in stores:
    lat = s["lat"] if "lat" in s else s["center"]["lat"]
    lon = s["lon"] if "lon" in s else s["center"]["lon"]
    tiles.add(f"{int(lat * 1.5):02d}{int(lon - 100):02d}")
print(f"{len(tiles)} first-level tiles contain stores")

for code in sorted(tiles):
    path = OUT / f"pop1km_{code}.txt"
    if path.exists():
        continue
    url = f"https://www.e-stat.go.jp/gis/statmap-search/data?statsId=T001140&code={code}&downloadType=2"
    resp = requests.get(url, headers=HEADERS, timeout=120)
    if resp.status_code != 200 or not resp.content.startswith(b"PK"):
        print(f"  {code}: no data")
        continue
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        name = next(n for n in z.namelist() if n.endswith(".txt"))
        path.write_bytes(z.read(name))
    time.sleep(1)
print(f"Done: {len(list(OUT.glob('pop1km_*.txt')))} tiles saved")

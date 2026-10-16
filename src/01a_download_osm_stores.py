"""Download every convenience store mapped in OpenStreetMap for Japan (Overpass API).

Buildings mapped as outlines are reduced to their centre point.
OSM covers roughly 80% of real stores; Part 1 checks coverage by prefecture.
"""
import gzip
import json
from datetime import date
import requests
from config import RAW, OVERPASS_HEADERS

OUT = RAW / "osm"
OUT.mkdir(parents=True, exist_ok=True)

QUERY = """
[out:json][timeout:600];
area["ISO3166-1"="JP"][admin_level=2]->.jp;
nwr["shop"="convenience"](area.jp);
out center tags;
"""

# Public Overpass servers are often busy, so try a mirror before giving up
SERVERS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.private.coffee/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter"]

for server in SERVERS:
    try:
        resp = requests.post(server, data={"data": QUERY}, headers=OVERPASS_HEADERS, timeout=900)
        resp.raise_for_status()
        elements = resp.json()["elements"]
        print(f"Downloaded from {server}")
        break
    except (requests.RequestException, ValueError) as err:
        print(f"{server} failed: {err}")
else:
    raise SystemExit("All Overpass servers failed; try again later")

path = OUT / f"convenience_stores_{date.today():%Y-%m-%d}.json.gz"
with gzip.open(path, "wt", encoding="utf-8") as f:
    json.dump(elements, f, ensure_ascii=False)
print(f"{len(elements):,} stores saved to {path.name}")

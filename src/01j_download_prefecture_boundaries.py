"""Download simplified prefecture boundaries (GeoJSON, 47 prefectures).

Source: Global Map Japan (GSI, 地球地図日本), as converted by the dataofjapan/land
project. Free for non-commercial use with credit to Global Map Japan.
Simplified coastlines mean some seaside stores fall just outside every polygon;
the cleaning script gives those the nearest prefecture.
"""
import requests
from config import RAW, HEADERS

URL = "https://raw.githubusercontent.com/dataofjapan/land/master/japan.geojson"
OUT = RAW / "boundaries"
OUT.mkdir(parents=True, exist_ok=True)

data = requests.get(URL, headers=HEADERS, timeout=120).content
assert data.lstrip().startswith(b"{")
(OUT / "japan_prefectures.geojson").write_bytes(data)
print(f"Prefecture boundaries: {len(data) / 1024 / 1024:.1f} MB")

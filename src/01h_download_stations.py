"""Download railway stations with daily passenger counts (MLIT National Land Numerical Info, S12).

Station footfall is a stronger demand signal than residents alone for a
convenience store, especially in Tokyo and Osaka.
"""
import zipfile
import requests
from config import RAW, HEADERS

URL = "https://nlftp.mlit.go.jp/ksj/gml/data/S12/S12-25/S12-25_GML.zip"
OUT = RAW / "stations"
OUT.mkdir(parents=True, exist_ok=True)

path = OUT / URL.rsplit("/", 1)[-1]
data = requests.get(URL, headers=HEADERS, timeout=300).content
path.write_bytes(data)
print(f"{path.name}: {len(data) / 1024 / 1024:.1f} MB")

with zipfile.ZipFile(path) as z:
    for name in z.namelist():
        if name.endswith(".geojson"):
            print("  contains", name)

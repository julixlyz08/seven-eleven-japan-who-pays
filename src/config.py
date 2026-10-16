from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANUAL = ROOT / "data" / "manual"
PROCESSED = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "seven_eleven.db"
FIGURES = ROOT / "reports" / "figures"

# JFA refuses requests that don't look like a browser
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"}

# Overpass (OpenStreetMap) does the opposite: it wants a named, non-browser client
OVERPASS_HEADERS = {"User-Agent": "seven-eleven-japan-who-pays/1.0 (student data project)"}

for folder in (RAW, MANUAL, PROCESSED, FIGURES):
    folder.mkdir(parents=True, exist_ok=True)

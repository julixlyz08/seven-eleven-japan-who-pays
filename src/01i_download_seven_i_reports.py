"""Download Seven & i's latest Corporate Outline (yearly data for FY2015-FY2025)
and its segment Excel files (revenue, operating income, depreciation by business)."""
import requests
from config import RAW, HEADERS

URL = "https://www.7andi.com/en/ir/file/library/co/pdf/2026_all_b_en.pdf"
OUT = RAW / "seven_i_reports"
OUT.mkdir(parents=True, exist_ok=True)

data = requests.get(URL, headers=HEADERS, timeout=120).content
assert data.startswith(b"%PDF")
(OUT / "corporate_outline_fy2025.pdf").write_bytes(data)
print(f"Corporate Outline FY2025: {len(data) / 1024 / 1024:.1f} MB")

SEGMENTS = ["Segment_Information_2026_en.xlsx", "Segment_Information_2026_02_en.xlsx"]
for name in SEGMENTS:
    data = requests.get(f"https://www.7andi.com/en/ir/file/financial/si/{name}", headers=HEADERS, timeout=120).content
    assert data.startswith(b"PK")
    (OUT / name).write_bytes(data)
    print(f"{name}: {len(data) / 1024:.0f} KB")

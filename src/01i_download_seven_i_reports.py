"""Download Seven & i's latest Corporate Outline (yearly data for FY2015-FY2025)."""
import requests
from config import RAW, HEADERS

URL = "https://www.7andi.com/en/ir/file/library/co/pdf/2026_all_b_en.pdf"
OUT = RAW / "seven_i_reports"
OUT.mkdir(parents=True, exist_ok=True)

data = requests.get(URL, headers=HEADERS, timeout=120).content
assert data.startswith(b"%PDF")
(OUT / "corporate_outline_fy2025.pdf").write_bytes(data)
print(f"Corporate Outline FY2025: {len(data) / 1024 / 1024:.1f} MB")

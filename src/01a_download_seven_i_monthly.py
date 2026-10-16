"""Download Seven & i's monthly business performance Excel files (one per fiscal year)."""
import re
import requests
from config import RAW, HEADERS

BASE = "https://www.7andi.com"
PAGE = BASE + "/en/ir/financial/monthly_highlight.html"
OUT = RAW / "seven_i_monthly"
OUT.mkdir(parents=True, exist_ok=True)

html = requests.get(PAGE, headers=HEADERS, timeout=60).text
links = sorted(set(re.findall(r'href="([^"]+\.xlsx)"', html)))
print(f"{len(links)} Excel files found")

for link in links:
    name = link.rsplit("/", 1)[-1]
    data = requests.get(BASE + link, headers=HEADERS, timeout=60).content
    (OUT / name).write_bytes(data)
    print(f"  {name}: {len(data) / 1024:.0f} KB")

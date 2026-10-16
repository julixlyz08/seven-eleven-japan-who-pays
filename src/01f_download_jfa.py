"""Download the Japan Franchise Association's convenience-store statistics (PDF only).

Keeps the two long time-series files (2005-2025) and the 2026 monthly reports.
The yearly summaries repeat the time series, so they are skipped.
"""
import re
import requests
from bs4 import BeautifulSoup
from config import RAW, HEADERS

PAGE = "https://www.jfa-fc.or.jp/particle/320.html"
OUT = RAW / "jfa"
OUT.mkdir(parents=True, exist_ok=True)

soup = BeautifulSoup(requests.get(PAGE, headers=HEADERS, timeout=60).content, "html.parser")
for a in soup.find_all("a", href=True):
    label = a.get_text(" ", strip=True)
    if not a["href"].endswith(".pdf"):
        continue
    series = re.search(r"時系列データ（(\d{4})年～(\d{4})年）", label)
    month = re.search(r"(\d{4})年(\d{1,2})月度", label)
    if series:
        name = f"timeseries_{series[1]}_{series[2]}.pdf"
    elif month:
        name = f"monthly_{month[1]}_{int(month[2]):02d}.pdf"
    else:
        continue
    url = requests.compat.urljoin(PAGE, a["href"])
    # Without the page as referer, the site returns a redirect instead of the PDF
    data = requests.get(url, headers=HEADERS | {"Referer": PAGE}, timeout=60).content
    assert data.startswith(b"%PDF"), f"{name}: not a PDF"
    (OUT / name).write_bytes(data)
    print(f"  {name} <- {label}")

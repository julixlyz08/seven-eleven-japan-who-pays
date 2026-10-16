"""Download minimum wages by prefecture (MHLW) and 7-Eleven's new-contract press release.

The franchise terms themselves are typed into data/manual/franchise_terms.csv,
because they come from web pages and a two-page PDF, not a data file.
"""
import requests
from bs4 import BeautifulSoup
from config import RAW, HEADERS

# 1. Minimum wage by prefecture, FY2002 to latest (one Excel file on MHLW's page)
PAGE = ("https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/"
        "roudoukijun/minimumichiran/")
out = RAW / "minimum_wage"
out.mkdir(parents=True, exist_ok=True)
soup = BeautifulSoup(requests.get(PAGE, headers=HEADERS, timeout=60).content, "html.parser")
link = next(a["href"] for a in soup.find_all("a", href=True)
            if a["href"].endswith(".xlsx") and "改定状況" in a.get_text())
data = requests.get(requests.compat.urljoin(PAGE, link), headers=HEADERS, timeout=60).content
(out / "minimum_wage_by_prefecture.xlsx").write_bytes(data)
print(f"Minimum wages: {len(data) / 1024:.0f} KB")

# 2. Press release announcing the new franchise contract (June 19, 2026)
RELEASE = "https://www.sej.co.jp/company/news_release/news/2026/202606191500.html"
out = RAW / "franchise"
out.mkdir(parents=True, exist_ok=True)
soup = BeautifulSoup(requests.get(RELEASE, headers=HEADERS, timeout=60).content, "html.parser")
link = next(a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith(".pdf"))
data = requests.get(requests.compat.urljoin(RELEASE, link), headers=HEADERS, timeout=60).content
assert data.startswith(b"%PDF")
(out / "sej_new_contract_2026-06-19.pdf").write_bytes(data)
print(f"Franchise release: {len(data) / 1024:.0f} KB")

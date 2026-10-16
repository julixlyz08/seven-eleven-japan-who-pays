"""Download consumer prices (CPI) and population by prefecture from e-Stat.

CPI: 2020-base long series, by category and by item (onigiri, cigarettes, ...).
Their file IDs change every month, so they are looked up by title.
Population: Oct 1, 2024 estimates by prefecture (latest yearly release).
"""
import requests
from bs4 import BeautifulSoup
from config import RAW, HEADERS

BASE = "https://www.e-stat.go.jp"
CPI_LIST = (BASE + "/stat-search/files?page=1&toukei=00200573&tstat=000001150147&cycle=0"
            "&tclass1=000001150151&tclass2=000001150152&tclass3=000001150153"
            "&tclass4=000001150156&layout=datalist&tclass5val=0")
CPI_WANTED = {
    "中分類指数（1970年1月～最新月）": "cpi_by_category.csv",
    "品目別価格指数（1970年1月～最新月）": "cpi_by_item.csv",
}
POPULATION = {
    "000040268859": "population_by_prefecture_2024.xlsx",           # total, by year
    "000040268919": "population_by_prefecture_age_groups_2024.xlsx",  # 0-14, 15-64, 65+
}


def download(url, path):
    data = requests.get(url, headers=HEADERS, timeout=120).content
    path.write_bytes(data)
    print(f"  {path.name}: {len(data) / 1024:.0f} KB")


out = RAW / "cpi"
out.mkdir(parents=True, exist_ok=True)
soup = BeautifulSoup(requests.get(CPI_LIST, headers=HEADERS, timeout=60).content, "html.parser")
for a in soup.find_all("a", href=True):
    if "file-download" not in a["href"]:
        continue
    title = a.find_parent("li").get_text(" ", strip=True)
    for prefix, name in CPI_WANTED.items():
        if title.startswith(prefix):
            download(BASE + a["href"], out / name)

out = RAW / "population"
out.mkdir(parents=True, exist_ok=True)
for stat_id, name in POPULATION.items():
    download(f"{BASE}/stat-search/file-download?statInfId={stat_id}&fileKind=0", out / name)

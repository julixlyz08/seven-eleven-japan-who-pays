"""Download METI's retail survey (商業動態統計) time series from e-Stat.

METI's own site refuses scripts, so the same Excel files come from e-Stat.
File IDs change with every monthly update, so they are looked up by title.
"""
import requests
from bs4 import BeautifulSoup
from config import RAW, HEADERS

BASE = "https://www.e-stat.go.jp"
LIST = (BASE + "/stat-search/files?page=1&toukei=00550030&tstat=000001081875"
        "&cycle=0&tclass1=000001081879&layout=datalist&tclass2val=0")
OUT = RAW / "meti_retail"
OUT.mkdir(parents=True, exist_ok=True)

# Title prefix on e-Stat -> local file name
WANTED = {
    "コンビニエンスストア商品別販売額等及び前年": "convenience_stores.xlsx",
    "ドラッグストア商品別販売額等及び前年": "drugstores.xlsx",
    "百貨店・スーパー商品別販売額及び前年": "department_supermarkets.xlsx",
    "業種別商業販売額及び前年": "retail_by_industry.xlsx",
}

soup = BeautifulSoup(requests.get(LIST, headers=HEADERS, timeout=60).content, "html.parser")
found = set()
for a in soup.find_all("a", href=True):
    if "file-download" not in a["href"]:
        continue
    title = a.find_parent("li").get_text(" ", strip=True)
    for prefix, name in WANTED.items():
        if title.startswith(prefix) and name not in found:
            data = requests.get(BASE + a["href"], headers=HEADERS, timeout=120).content
            (OUT / name).write_bytes(data)
            found.add(name)
            print(f"  {name}: {len(data) / 1024:.0f} KB  ({title[:60]})")

missing = set(WANTED.values()) - found
assert not missing, f"not found on e-Stat: {missing}"

"""Turn MHLW's minimum-wage table into one row per prefecture and fiscal year.

The table has one column pair per fiscal year (new hourly rate, date it takes
effect), FY2002 to FY2026, and a weighted national average as its last row.
New rates take effect between October and the following spring.
"""
import re
import openpyxl
import pandas as pd
from config import RAW, PROCESSED

ws = openpyxl.load_workbook(RAW / "minimum_wage" / "minimum_wage_by_prefecture.xlsx", data_only=True).active
rows = list(ws.iter_rows(values_only=True))


def fiscal_year(label):
    m = re.match(r"(平成|令和)(\d+|元)年度", str(label or ""))  # 元 = first year of an era
    if not m:
        return None
    return (1988 if m[1] == "平成" else 2018) + (1 if m[2] == "元" else int(m[2]))


years = {c: fiscal_year(v) for c, v in enumerate(rows[0]) if fiscal_year(v)}
records = []
for r in rows[2:]:
    name = str(r[0] or "").replace("　", "").strip()
    if not name:
        continue
    name = "national_weighted_average" if name.startswith("全国") else re.sub(r"[都府県]$", "", name)
    for c, fy in years.items():
        if isinstance(r[c], (int, float)):
            eff = r[c + 1]
            eff = pd.Timestamp("1899-12-30") + pd.Timedelta(days=eff) if isinstance(eff, (int, float)) else eff
            records.append({"prefecture": name, "fiscal_year": fy, "hourly_wage_yen": float(r[c]),
                            "effective": pd.to_datetime(eff, errors="coerce")})
mw = pd.DataFrame(records)
assert mw["prefecture"].nunique() == 48, mw["prefecture"].nunique()
assert len(mw) == 48 * 25, len(mw)  # FY2002-FY2026
mw.to_csv(PROCESSED / "minimum_wage.csv", index=False)

nat = mw[mw["prefecture"] == "national_weighted_average"].set_index("fiscal_year")["hourly_wage_yen"]
print(f"{len(mw):,} rows, FY{mw['fiscal_year'].min()}-FY{mw['fiscal_year'].max()}")
print("National weighted average: " + ", ".join(f"FY{y} {nat[y]:,.0f}" for y in [2015, 2019, 2022, 2025, 2026]))
latest = mw[(mw["fiscal_year"] == 2026) & (mw["prefecture"] != "national_weighted_average")]
print(f"FY2026 range: {latest['hourly_wage_yen'].min():,.0f} to {latest['hourly_wage_yen'].max():,.0f} yen "
      f"({latest.loc[latest['hourly_wage_yen'].idxmax(), 'prefecture']})")

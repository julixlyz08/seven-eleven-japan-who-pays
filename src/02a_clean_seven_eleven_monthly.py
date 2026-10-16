"""Turn Seven & i's yearly Excel files into one monthly table for 7-Eleven Japan.

Each file holds two 7-Eleven Japan blocks (Mar-Aug, then Sep-Feb), five rows each:
same-store sales, customers, spend per customer, total-store sales, store count.
The first four are published as % of the same month last year (100 = flat);
they are saved as % change (0 = flat) to match the JFA table.

Traps handled here:
- File names changed convention: "FY2016" ends Feb 2016, but "FY2025" ends Feb 2026.
  The fiscal year is read from the sheet's own date range instead.
- Column positions move between years, so months are read from each block's header row.
- In FY2021-22 the first header is shared with the US business (Jan-Dec year),
  so 7-Eleven Japan's row also repeats last Jan-Feb before March.
- Two files cover Mar 2024 - Feb 2025; they must agree where they overlap.
"""
import re
import openpyxl
import pandas as pd
from config import RAW, PROCESSED

MONTHS = {"Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
          "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12, "Jan": 1, "Feb": 2}
ROWS = [  # (column name, text that must appear on that row)
    ("same_store_sales_yoy_pct", "Sales"),
    ("same_store_customers_yoy_pct", "customers"),
    ("same_store_spend_yoy_pct", "spending"),
    ("total_store_sales_yoy_pct", "Sales"),
    ("stores", "Number of stores"),
]


def month_of(text):
    return MONTHS.get(str(text).strip()[:3]) if isinstance(text, str) else None


def parse(path):
    ws = openpyxl.load_workbook(path, data_only=True).active
    grid = [[c.value for c in row] for row in ws.iter_rows()]
    flat = " ".join(str(v) for row in grid for v in row if isinstance(v, str))
    start_year = int(re.search(r"March 1, (\d{4})", flat)[1])

    records = []
    for r, row in enumerate(grid):
        if not any(isinstance(v, str) and v.strip() == "Seven-Eleven Japan" for v in row):
            continue
        # Nearest header row above: maps column -> calendar month
        header = next(grid[h] for h in range(r - 1, -1, -1)
                      if sum(month_of(v) is not None for v in grid[h]) >= 3)
        cols = {c: month_of(v) for c, v in enumerate(header) if month_of(v)}
        # In some years the header is shared with the US business (calendar year), so
        # Jan-Feb sit left of Mar and hold the *previous* year's figures: skip them
        march = next((c for c, m in cols.items() if m == 3), None)
        if march is not None:
            cols = {c: m for c, m in cols.items() if c >= march}
        for offset, (name, label) in enumerate(ROWS):
            line = grid[r + offset]
            text = " ".join(str(v) for v in line if isinstance(v, str))
            assert label in text, f"{path.name} row {r + offset + 1}: expected '{label}', got '{text}'"
            for c, m in cols.items():
                v = line[c]
                if isinstance(v, (int, float)):
                    year = start_year if m >= 3 else start_year + 1
                    records.append({"month": f"{year}-{m:02d}", "measure": name,
                                    "value": float(v), "file": path.name})
    return records


records = []
for path in sorted((RAW / "seven_i_monthly").glob("*.xlsx")):
    recs = parse(path)
    records += recs
    print(f"  {path.name}: {len({r['month'] for r in recs})} months")
long = pd.DataFrame(records)

# Overlapping files must report the same number for the same month
spread = long.groupby(["month", "measure"])["value"].agg(["min", "max", "count"])
clash = spread[(spread["count"] > 1) & (spread["max"] != spread["min"])]
print(f"\nMonths reported in more than one file: {spread[spread['count'] > 1].index.get_level_values(0).nunique()}")
print(f"Disagreements between files: {len(clash)}")
if len(clash):
    print(clash)

monthly = (long.groupby(["month", "measure"])["value"].last()
           .unstack()[[name for name, _ in ROWS]].reset_index())
monthly["stores"] = monthly["stores"].astype("Int64")
pct = [c for c in monthly.columns if c.endswith("_yoy_pct")]
monthly[pct] = (monthly[pct] - 100).round(2)

# Check the identity: sales growth = customer growth x spend growth (to rounding)
implied = ((1 + monthly["same_store_customers_yoy_pct"] / 100)
           * (1 + monthly["same_store_spend_yoy_pct"] / 100) - 1) * 100
monthly["identity_gap"] = (monthly["same_store_sales_yoy_pct"] - implied).round(2)
print(f"Largest gap between sales and customers x spend: {monthly['identity_gap'].abs().max():.2f} points")

monthly.to_csv(PROCESSED / "seven_eleven_japan_monthly.csv", index=False)
print(f"\nSaved {len(monthly)} months: {monthly['month'].min()} to {monthly['month'].max()}")

"""Turn the JFA convenience-store PDFs into one monthly table (all member chains combined).

Sources:
- Two time-series PDFs, Jan 2005 - Dec 2025: one line per month with 14 numbers.
- One report per month for 2026: seven labelled blocks, current month vs. last year.

Traps handled here:
- Some 2026 reports store characters in a scrambled order, so figures are read by
  their position on the page (three fixed columns) instead of as text.
- Each report's "last year" column is checked against the time series as a test.
- "Same stores" growth compares stores open in both years, so it can't be computed
  from the levels; it is kept as published.
- JFA membership changed over time (13 chains in the 2010s, 7 in 2026), so levels
  include a few small chains joining and leaving.
"""
import re
import pdfplumber
import pandas as pd
from config import RAW, PROCESSED

COLUMNS = [
    "sales_all_myen", "sales_all_yoy_pct", "sales_same_myen", "sales_same_yoy_pct",
    "stores", "stores_yoy_pct",
    "customers_all_k", "customers_all_yoy_pct", "customers_same_k", "customers_same_yoy_pct",
    "spend_all_yen", "spend_all_yoy_pct", "spend_same_yen", "spend_same_yoy_pct",
]


def number(token):
    token = token.replace(",", "").replace("%", "")
    return None if token in ("―", "-", "") else float(token)


def read_text(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


# 1. Time series, 2005-2025: track the year by counting months in order
rows = []
for path, first_year in [(RAW / "jfa" / "timeseries_2005_2016.pdf", 2005),
                         (RAW / "jfa" / "timeseries_2017_2025.pdf", 2017)]:
    year, last_month = first_year, 0
    for line in read_text(path).splitlines():
        m = re.search(r"(?<![\d～])(\d{1,2})月 (.+)$", line)
        if not m or "～" in line:
            continue
        month, tokens = int(m[1]), m[2].split()
        if len(tokens) != 14:
            continue
        if month < last_month:
            year += 1
        last_month = month
        rows.append({"month": f"{year}-{month:02d}", "source": path.name,
                     **dict(zip(COLUMNS, map(number, tokens)))})
series = pd.DataFrame(rows)
print(f"Time series: {len(series)} months, {series['month'].min()} to {series['month'].max()}")

# 2. Monthly reports, 2026: seven data rows in a fixed order
BLOCKS = [("sales_all", "myen"), ("sales_same", "myen"), ("stores", ""),
          ("customers_all", "k"), ("customers_same", "k"),
          ("spend_all", "yen"), ("spend_same", "yen")]


def data_rows(path):
    """Read the seven data rows of a report by position on the page.

    Some reports store characters in a scrambled order, so text extraction breaks,
    but every figure sits in one of three fixed columns: this year, last year, and
    % change. Rows are clusters of characters at about the same height.
    """
    with pdfplumber.open(path) as pdf:
        chars = [c for c in pdf.pages[0].chars
                 if c["text"] in "0123456789,.-%" and c["x0"] > 240]
    chars.sort(key=lambda c: c["top"])
    clusters, current = [], [chars[0]]
    for c in chars[1:]:
        if c["top"] - current[-1]["top"] > 3:
            clusters.append(current)
            current = []
        current.append(c)
    clusters.append(current)

    rows = []
    for cluster in clusters:
        cols = ["", "", ""]
        for c in sorted(cluster, key=lambda c: c["x0"]):
            cols[0 if c["x0"] < 380 else 1 if c["x0"] < 490 else 2] += c["text"]
        # Data rows have two figures and a % change; product-mix rows don't
        if cols[0] and cols[1] and cols[2].endswith("%") and "%" not in cols[0] + cols[1]:
            rows.append((number(cols[0]), number(cols[1]), number(cols[2])))
    return rows


reports, checks = [], []
for path in sorted((RAW / "jfa").glob("monthly_*.pdf")):
    year, month = map(int, re.findall(r"\d+", path.stem))
    rows_found = data_rows(path)
    assert len(rows_found) == len(BLOCKS), f"{path.name}: found {len(rows_found)} data rows"
    row = {"month": f"{year}-{month:02d}", "source": path.name}
    for (name, unit), (current, previous, yoy) in zip(BLOCKS, rows_found):
        col = f"{name}_{unit}" if unit else name
        row[col], row[f"{name}_yoy_pct"] = current, yoy
        checks.append({"month": f"{year - 1}-{month:02d}", "column": col, "report_says": previous})
    reports.append(row)
reports = pd.DataFrame(reports)
print(f"Monthly reports: {len(reports)} months, {reports['month'].min()} to {reports['month'].max()}")

# Test the 2026 parsing: each report's "last year" all-store figures should match the
# 2025 time series, allowing for small revisions. Same-store figures are left out:
# "last year" then covers a different set of stores, so they differ by design.
checks = pd.DataFrame(checks)
checks = checks[~checks["column"].str.contains("same")]
series_long = series.melt(id_vars="month", var_name="column", value_name="series_says")
checks = checks.merge(series_long, on=["month", "column"], how="left")
checks["diff_pct"] = (checks["report_says"] / checks["series_says"] - 1) * 100
print(f"2026 reports vs. 2025 time series (all stores): largest difference "
      f"{checks['diff_pct'].abs().max():.3f}% across {len(checks)} figures")
assert checks["diff_pct"].abs().max() < 0.1, checks.sort_values("diff_pct").to_string()

jfa = pd.concat([series, reports], ignore_index=True)[["month", *COLUMNS, "source"]]
assert jfa["month"].is_unique

# Check the identity: sales = customers x spend (all stores, levels)
implied = jfa["customers_all_k"] * 1000 * jfa["spend_all_yen"] / 1e6
gap = (jfa["sales_all_myen"] / implied - 1) * 100
print(f"Sales vs. customers x spend: largest gap {gap.abs().max():.2f}%")
assert gap.abs().max() < 0.5, jfa.loc[gap.abs() >= 0.5, ["month", "source"]]

jfa.to_csv(PROCESSED / "jfa_convenience_monthly.csv", index=False)
print(f"\nSaved {len(jfa)} months: {jfa['month'].min()} to {jfa['month'].max()}")

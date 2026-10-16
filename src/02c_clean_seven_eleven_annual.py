"""Extract 7-Eleven Japan's yearly figures from Seven & i's Corporate Outline.

Page 16 (PDF page 18): FY2015-FY2025 chain sales by product, margins, store counts.
Page 18 (PDF page 20): store counts of the major chains, FY2020-FY2025.

Seven & i's fiscal year runs March to February: FY2025 = Mar 2025 - Feb 2026.
"""
import re
import pdfplumber
import pandas as pd
from config import RAW, PROCESSED

PDF = RAW / "seven_i_reports" / "corporate_outline_fy2025.pdf"
with pdfplumber.open(PDF) as pdf:
    sej_page = pdf.pages[17].extract_text()
    chains_page = pdf.pages[19].extract_text()


def value(token):
    if token in ("–", "-"):
        return None
    negative = token.startswith("(")
    v = float(token.strip("()").replace(",", ""))
    return -v if negative else v


NUMBER = r"\(?-?[\d,]+(?:\.\d+)?\)?|–"

# 1. 7-Eleven Japan: one line per measure, label then 11 yearly values
header = next(l for l in sej_page.splitlines() if l.startswith("FY2015"))
years = [int(y) for y in re.findall(r"FY(\d{4})", header)]
assert years == list(range(2015, 2026)), years
WANTED = {
    "Total store sales": "total_store_sales_myen",
    "Gross total store sales": "gross_total_store_sales_myen",
    "Processed food": "sales_processed_food_myen",
    "Fast food": "sales_fast_food_myen",
    "Daily food": "sales_daily_food_myen",
    "Nonfood": "sales_nonfood_myen",
    "Existing store sales increase (%)*": "same_store_sales_yoy_pct",
    "Number of customers (%)": "same_store_customers_yoy_pct",
    "Average spending per customer (%)": "same_store_spend_yoy_pct",
    "Average daily sales per store of all stores (Thousands of yen)": "daily_sales_per_store_kyen",
    "Average daily sales per store of newly opened stores (Thousands of yen)": "daily_sales_new_store_kyen",
    "Merchandise gross profit margin (%)": "gross_margin_pct",
    "Processed food (%)": "margin_processed_food_pct",
    "Fast food (%)": "margin_fast_food_pct",
    "Daily food (%)": "margin_daily_food_pct",
    "Nonfood (%)": "margin_nonfood_pct",
    "Number of stores": "stores",
    "Openings": "openings",
    "Closures": "closures",
    "Type A": "stores_type_a",
    "Type C": "stores_type_c",
    "Directly operated stores": "stores_company_run",
    "Operating income": "operating_income_myen",
    "Revenues from operations": "revenue_myen",
}
table = {}
for line in sej_page.splitlines():
    tokens = re.findall(NUMBER, line)
    label = re.split(rf"\s(?:{NUMBER})(?:\s|$)", line, maxsplit=1)[0].strip()
    if label in WANTED and WANTED[label] not in table and len(tokens) >= 11:
        table[WANTED[label]] = [value(t) for t in tokens[-11:]]
missing = set(WANTED.values()) - set(table)
assert not missing, missing
annual = pd.DataFrame(table, index=pd.Index(years, name="fiscal_year")).reset_index()
annual.insert(1, "period", [f"{y}-03 to {y + 1}-02" for y in years])

# Sales by product must add up to total store sales (old basis until FY2021, gross after)
total = annual["gross_total_store_sales_myen"].fillna(annual["total_store_sales_myen"])
parts = annual.filter(like="sales_").filter(like="_myen").drop(
    columns=["total_store_sales_myen", "gross_total_store_sales_myen"]).sum(axis=1)
print(f"Products vs. total store sales: largest gap {((parts / total - 1) * 100).abs().max():.2f}%")
annual.to_csv(PROCESSED / "seven_eleven_japan_annual.csv", index=False)
print(f"Saved 7-Eleven Japan yearly table: {len(annual)} years, {annual.shape[1] - 2} measures")

# 2. Major chains' store counts at fiscal year-end (7-Eleven includes Okinawa here)
rows = []
for line in chains_page.splitlines():
    # Chart labels share some of these text lines, so take the first six numbers only
    m = re.match(r"(Seven-Eleven\*?|Lawson|FamilyMart|Other CVS|Nationwide) ((?:\d{1,2},\d{3} ){5}\d{1,2},\d{3})", line.strip())
    if m:
        counts = [int(v.replace(",", "")) for v in m[2].split()]
        rows += [{"chain": m[1].rstrip("*"), "fiscal_year": fy, "stores": n}
                 for fy, n in zip(range(2020, 2026), counts)]
chains = pd.DataFrame(rows)
assert chains["chain"].nunique() == 5, chains["chain"].unique()
check = chains.pivot(index="fiscal_year", columns="chain", values="stores")
assert (check.drop(columns="Nationwide").sum(axis=1) == check["Nationwide"]).all()
chains.to_csv(PROCESSED / "chain_store_counts.csv", index=False)
print(f"Saved chain store counts: {chains['chain'].nunique()} chains, FY2020-FY2025 (chains add up to nationwide)")

"""Turn METI's retail survey Excel files into two tidy monthly tables.

national: convenience stores, drugstores and supermarkets, by product group
regional: convenience stores and drugstores by METI regional bureau

Growth rates are taken as METI publishes them (% of the same month last year),
not computed from sales levels: METI re-draws its sample from time to time
(2012, 2017, 2021 for convenience stores), which makes levels jump, and its
published growth rates are adjusted for that. Levels are kept for shares only.
"""
import re
import openpyxl
import pandas as pd
from config import RAW, PROCESSED

FILES = RAW / "meti_retail"


def read_sheet(file, sheet, label_rows=1):
    """Return {column label: Series by month}. Labels join `label_rows` header rows."""
    ws = openpyxl.load_workbook(FILES / file, read_only=True, data_only=True)[sheet]
    rows = list(ws.iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if "時間軸コード" in [str(c) for c in r])
    date_col = [str(c) for c in rows[h]].index("時間軸コード") + 1
    labels = []
    for c in range(len(rows[h])):
        parts = [str(rows[h - k][c]) for k in range(label_rows - 1, -1, -1) if rows[h - k][c] is not None]
        labels.append(" | ".join(parts))
    records = {}
    for r in rows[h + 1:]:
        m = re.fullmatch(r"(\d{4})年(\d{1,2})月", str(r[date_col] or ""))
        if m:
            records[f"{m[1]}-{int(m[2]):02d}"] = r
    out = {}
    for c, label in enumerate(labels):
        if c <= date_col or not label:
            continue
        values = pd.to_numeric(pd.Series({k: v[c] for k, v in records.items()}), errors="coerce")
        if values.notna().any():
            out[label] = values
    return out


def pick(series, label, scale=1.0, shift=0.0):
    matches = [k for k in series if k == label]
    assert matches, f"'{label}' not in {list(series)[:12]}"
    return series[matches[0]] * scale + shift


# National ---------------------------------------------------------------------
cvs_v = read_sheet("convenience_stores.xlsx", "販売額(value)月次(Monthly)")
cvs_g = read_sheet("convenience_stores.xlsx", "前年同月比(change) (Monthly)")
drug_v = read_sheet("drugstores.xlsx", "販売額(value)月次(Monthly)")
drug_g = read_sheet("drugstores.xlsx", "前年同月比(change) (Monthly)")
sup_v = read_sheet("department_supermarkets.xlsx", "スーパー　販売額　月次")
sup_g = read_sheet("department_supermarkets.xlsx", "スーパー　伸び率　月次")
sup_s = read_sheet("department_supermarkets.xlsx", "スーパー　既存店　月次")

national = pd.DataFrame({
    "cvs_sales_myen": pick(cvs_v, "Total"),
    "cvs_sales_yoy_pct": pick(cvs_g, "Total", shift=-100),
    "cvs_ff_daily_yoy_pct": pick(cvs_g, "Fast foods & Dailyfoods", shift=-100),
    "cvs_processed_yoy_pct": pick(cvs_g, "Processed Foods", shift=-100),
    "cvs_nonfood_yoy_pct": pick(cvs_g, "Non-Foods", shift=-100),
    "cvs_stores_yoy_pct": pick(cvs_g, "Number of Establishments", shift=-100),
    "drug_sales_myen": pick(drug_v, "Sales of goods"),
    "drug_food_myen": pick(drug_v, "Food"),
    "drug_sales_yoy_pct": pick(drug_g, "Sales of goods", shift=-100),
    "drug_food_yoy_pct": pick(drug_g, "Food", shift=-100),
    "drug_stores_yoy_pct": pick(drug_g, "Number of establishments", shift=-100),
    "super_food_myen": pick(sup_v, "Food and Beverages"),
    "super_food_yoy_pct": pick(sup_g, "Food and Beverages", shift=-100),
    "super_food_same_store_yoy_pct": pick(sup_s, "Food and Beverages", shift=-100),
})
national.index.name = "month"
national = national.loc["2014-01":].round(2)
national.to_csv(PROCESSED / "meti_national_monthly.csv")
print(f"National: {len(national)} months, {national.index.min()} to {national.index.max()}")
print(national[["cvs_sales_yoy_pct", "drug_food_yoy_pct", "super_food_same_store_yoy_pct"]].describe().round(1).to_string())

# Regional ---------------------------------------------------------------------
cvs_r = read_sheet("convenience_stores.xlsx", "局別前年同月比", label_rows=2)
drug_r = read_sheet("drugstores.xlsx", "局別前年同月比", label_rows=2)
drug_rv = read_sheet("drugstores.xlsx", "局別販売額(月次)", label_rows=2)
cvs_rv = read_sheet("convenience_stores.xlsx", "局別販売額(月次)", label_rows=2)

rows = []
for label, s in cvs_r.items():
    if " | " not in label:
        continue
    region, measure = label.split(" | ")
    if measure == "Total":
        rows.append(pd.DataFrame({"month": s.index, "region": region, "measure": "cvs_sales_yoy_pct", "value": s.values - 100}))
for source, measure_map in [(drug_r, {"Sales value": "drug_sales_yoy_pct", "Establishments": "drug_stores_yoy_pct"}),
                            (drug_rv, {"Sales value": "drug_sales_myen", "Establishments": "drug_stores"}),
                            (cvs_rv, {"Sales value": "cvs_sales_myen", "Number of Establishments": "cvs_stores"})]:
    for label, s in source.items():
        if " | " not in label:
            continue
        region, measure = label.split(" | ")
        if measure in measure_map:
            v = s.values - 100 if measure_map[measure].endswith("yoy_pct") else s.values
            rows.append(pd.DataFrame({"month": s.index, "region": region, "measure": measure_map[measure], "value": v}))
regional = (pd.concat(rows).pivot_table(index=["month", "region"], columns="measure", values="value")
            .reset_index())
regional = regional[regional["month"] >= "2014-01"].round(2)
regional.to_csv(PROCESSED / "meti_regional_monthly.csv", index=False)
print(f"\nRegional: regions {sorted(regional['region'].unique())}")
print(regional.groupby("region")[["cvs_sales_yoy_pct", "drug_sales_yoy_pct"]].count().to_string())

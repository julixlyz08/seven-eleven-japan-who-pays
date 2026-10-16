"""Part 2, step 3: are drugstores taking convenience-store shoppers?

1. National picture: food sales at drugstores, supermarkets and convenience stores,
   each chained from METI's published growth rates (2015 = 100).
2. Regional test: in regions where drugstores opened faster, did convenience-store
   sales grow more slowly? Region-by-month panel, 8 regions:
       cvs sales growth = region effect + month effect
                          + b x drugstore count growth + c x convenience-store count growth
   Month effects absorb anything national (COVID, inflation, tax changes); region
   effects absorb fixed regional differences. Standard errors allow for correlation
   across regions in the same month and over time (Driscoll-Kraay, 12 lags).
   Drugstore chains choose where to open, likely where demand is growing, which
   would bias b upward (toward zero or positive): a negative b is conservative.
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import PROCESSED, FIGURES
import style

nat = pd.read_csv(PROCESSED / "meti_national_monthly.csv", index_col="month")
reg = pd.read_csv(PROCESSED / "meti_regional_monthly.csv")

# 1. National indexes, 2015 = 100, chained from published growth -------------------
def chain(growth, base_levels):
    """Level path from % changes vs. a year earlier, starting from 12 base months."""
    out = list(base_levels)
    for g in growth.iloc[12:]:
        out.append(out[-12] * (1 + g / 100))
    return pd.Series(out, index=growth.index)


idx = pd.DataFrame(index=nat.index)
for name, level, growth in [("drugstore_food", "drug_food_myen", "drug_food_yoy_pct"),
                            ("supermarket_food", "super_food_myen", "super_food_yoy_pct"),
                            ("convenience_stores", "cvs_sales_myen", "cvs_sales_yoy_pct")]:
    idx[name] = chain(nat[growth], nat[level].iloc[:12])
idx = idx / idx.loc["2015-01":"2015-12"].mean() * 100
idx.index = pd.to_datetime(idx.index)
yearly = idx.groupby(idx.index.year).mean()
print("Sales index by year (2015 = 100), chained from METI's published growth")
print(yearly.round(0).to_string())

share = nat["drug_food_myen"] / nat["cvs_sales_myen"] * 100
print(f"\nDrugstore food sales as % of convenience-store sales: "
      f"{share.loc['2014-01':'2014-12'].mean():.0f}% in 2014, {share.iloc[-12:].mean():.0f}% in the last 12 months "
      "(raw levels; affected by survey redraws, so indicative only)")

# 2. Regional panel -----------------------------------------------------------------
# Drugstores report Kyushu and Okinawa separately; combine them (weighted by last
# year's sales or store count) to match convenience stores' "Kyushu + Okinawa".
reg = reg.set_index(["month", "region"])
for growth, level in [("drug_sales_yoy_pct", "drug_sales_myen"), ("drug_stores_yoy_pct", "drug_stores")]:
    k, o = reg.xs("Kyushu", level="region"), reg.xs("Okinawa", level="region")
    lk = k[level] / (1 + k[growth] / 100)  # last year's level implied by this year's growth
    lo = o[level] / (1 + o[growth] / 100)
    combined = (k[growth] * lk + o[growth] * lo) / (lk + lo)
    for m, v in combined.items():
        reg.loc[(m, "Kyushu＋Okinawa"), growth] = v
reg = reg.reset_index()
reg = reg[~reg["region"].isin(["Kyushu", "Okinawa"])]

# Convenience-store count growth from levels, skipping the 12 months after each
# survey redraw (Jan 2017, Mar 2021), when levels jump for reasons other than openings
reg = reg.sort_values(["region", "month"])
reg["cvs_stores_yoy_pct"] = reg.groupby("region")["cvs_stores"].pct_change(12) * 100
date = pd.to_datetime(reg["month"])
redraw = date.between("2017-01-01", "2017-12-01") | date.between("2021-03-01", "2022-02-01")
reg.loc[redraw, "cvs_stores_yoy_pct"] = np.nan

panel = reg.dropna(subset=["cvs_sales_yoy_pct", "drug_stores_yoy_pct", "cvs_stores_yoy_pct"]).copy()
panel["t"] = pd.factorize(panel["month"], sort=True)[0]
print(f"\nPanel: {panel['region'].nunique()} regions x {panel['month'].nunique()} months = {len(panel)} rows "
      f"({panel['month'].min()} to {panel['month'].max()})")


def fit(formula, data):
    return smf.ols(formula, data).fit(cov_type="hac-groupsum",
                                      cov_kwds={"time": data["t"].values, "maxlags": 12})


models = {
    "Drugstore count growth": "cvs_sales_yoy_pct ~ drug_stores_yoy_pct + cvs_stores_yoy_pct + C(region) + C(month)",
    "Drugstore sales growth": "cvs_sales_yoy_pct ~ drug_sales_yoy_pct + cvs_stores_yoy_pct + C(region) + C(month)",
    "Count growth, excl. 2020-21": "cvs_sales_yoy_pct ~ drug_stores_yoy_pct + cvs_stores_yoy_pct + C(region) + C(month)",
}
rows = []
for name, formula in models.items():
    data = panel[~panel["month"].between("2020-01", "2021-12")] if "excl" in name else panel
    data = data.assign(t=pd.factorize(data["month"], sort=True)[0])
    res = fit(formula, data)
    var = "drug_sales_yoy_pct" if "sales growth" in name else "drug_stores_yoy_pct"
    lo, hi = res.conf_int().loc[var]
    rows.append({"model": name, "effect": res.params[var], "low_95": lo, "high_95": hi,
                 "p_value": res.pvalues[var], "rows": int(res.nobs)})
results = pd.DataFrame(rows).set_index("model")
print("\nEffect on convenience-store sales growth (points) of +1 point faster drugstore growth")
print(results.round(3).to_string())
results.round(4).to_csv(PROCESSED / "part2_drugstore_panel.csv")

# Long view per region: 2015 -> latest 12 months
long = reg.copy()
long["date"] = pd.to_datetime(long["month"])
summary = []
for region, g in long.groupby("region"):
    g = g.set_index("date").sort_index()
    cvs = chain(g["cvs_sales_yoy_pct"], [100.0] * 12)
    drug = chain(g["drug_stores_yoy_pct"].fillna(0), [100.0] * 12)
    summary.append({"region": region,
                    "drugstores_change_pct": drug.iloc[-12:].mean() / drug.loc["2015"].mean() * 100 - 100,
                    "cvs_sales_change_pct": cvs.iloc[-12:].mean() / cvs.loc["2015"].mean() * 100 - 100})
summary = pd.DataFrame(summary).set_index("region").sort_values("drugstores_change_pct")
print("\nChange from 2015 to the latest 12 months, by region (%)")
print(summary.round(1).to_string())

# Figure: national indexes ------------------------------------------------------------
plot = idx.rolling(12).mean().dropna()
lines = [("drugstore_food", "Drugstores: food", style.REST),
         ("supermarket_food", "Supermarkets: food", style.THIRD),
         ("convenience_stores", "Convenience stores: all sales", style.SEVEN_ELEVEN)]
fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(100, color=style.TEXT_MUTED, linewidth=0.8)
for col, label, color in lines:
    ax.plot(plot.index, plot[col], color=color, label=label)
last = plot.index[-1]
for col, label, color in lines:
    y = plot[col].iloc[-1]
    ax.plot([last], [y], "o", color=color, markersize=6, markeredgecolor=style.SURFACE, markeredgewidth=1.5)
    ax.annotate(f"{y:.0f}", (last, y), xytext=(8, 0), textcoords="offset points",
                va="center", color=style.TEXT, fontsize=10)
ax.set_title("Drugstores have more than doubled their food sales since 2015")
ax.set_ylabel("Sales, 2015 = 100 (12-month average)")
ax.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(2016, last.year + 1)]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_xlim(plot.index[0], last + pd.Timedelta(days=200))
ax.legend(loc="upper left")
fig.text(0.01, 0.01, "Chained from METI's published growth rates, which adjust for changes in the survey sample. "
         "Nominal yen.\nSource: METI Current Survey of Commerce.",
         color=style.TEXT_MUTED, fontsize=8)
plt.tight_layout(rect=(0, 0.05, 1, 1))
plt.savefig(FIGURES / "part2_drugstore_food.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part2_drugstore_food.png'}")

# Is the regional pattern just population? (2020-2024 change, METI bureau regions) ------
BUREAU = {
    "Hokkaido": ["北海道"],
    "Tohoku": ["青森", "岩手", "宮城", "秋田", "山形", "福島"],
    "Kanto": ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "山梨", "長野", "静岡"],
    "Chubu": ["富山", "石川", "岐阜", "愛知", "三重"],
    "Kansai": ["福井", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"],
    "Chugoku": ["鳥取", "島根", "岡山", "広島", "山口"],
    "Shikoku": ["徳島", "香川", "愛媛", "高知"],
    "Kyushu＋Okinawa": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"],
}
from config import RAW
pop = pd.read_excel(RAW / "population" / "population_by_prefecture_2024.xlsx", header=None)
pop = pop[(pop[7] == "総人口") & (pop[8] == "男女計")]
pop["pref"] = pop[10].astype(str).str.replace("　", "").str.replace(r"[都道府県]$", "", regex=True)
pop.loc[pop["pref"] == "北海", "pref"] = "北海道"
pop = pop.set_index("pref")[[13, 17]].astype(float)
pop.columns = ["pop_2020", "pop_2024"]
by_region = {r: pop.loc[prefs].sum() for r, prefs in BUREAU.items()}
by_region = pd.DataFrame(by_region).T
assert len(pop.loc[sum(BUREAU.values(), [])]) == 47
summary["population_change_2020_24_pct"] = (by_region["pop_2024"] / by_region["pop_2020"] - 1) * 100
print("\nWith population change (2020-2024, %)")
print(summary.round(1).to_string())
c = summary.corr()
print(f"\nAcross the 8 regions: correlation of convenience-store growth with drugstore growth "
      f"{c.loc['cvs_sales_change_pct', 'drugstores_change_pct']:.2f}, with population change "
      f"{c.loc['cvs_sales_change_pct', 'population_change_2020_24_pct']:.2f}; "
      f"drugstore growth with population change {c.loc['drugstores_change_pct', 'population_change_2020_24_pct']:.2f}")
x = smf.ols("cvs_sales_change_pct ~ drugstores_change_pct + population_change_2020_24_pct", summary).fit()
print(f"Holding population change fixed: {x.params['drugstores_change_pct']:.2f} points of convenience-store growth "
      f"per point of drugstore growth (8 regions, p = {x.pvalues['drugstores_change_pct']:.2f}; descriptive only)")
summary.round(2).to_csv(PROCESSED / "part2_drugstore_regions.csv")

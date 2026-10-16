"""Part 2, step 1: 7-Eleven Japan vs. the rest of the convenience-store industry.

The JFA industry figures include 7-Eleven (about 45% of sales), so comparing
7-Eleven with "the industry" understates any gap. This script removes 7-Eleven.

1. Monthly 7-Eleven sales in yen: Seven & i only publishes % changes by month,
   so a monthly path is built by chaining those changes, then scaled so each
   fiscal year adds up to the yearly total in the Corporate Outline.
2. Rest of industry, same stores: for growth g, industry = w x 7-Eleven + (1 - w) x rest,
   where w is 7-Eleven's share of industry sales a year earlier. So
   rest = (industry - w x 7-Eleven) / (1 - w).
   Customer weights are not published; using the sales share assumes 7-Eleven's
   spend per customer is close to the industry's. A +/-10% range on w is reported.
3. Customer index: growth vs. a year earlier flatters whoever fell further in
   2020-21, so same-store growth is also chained into a level (2019 = 100).
   Chaining same-store growth is approximate: the set of stores changes each year.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import PROCESSED, FIGURES
import style

sej = pd.read_csv(PROCESSED / "seven_eleven_japan_monthly.csv")
jfa = pd.read_csv(PROCESSED / "jfa_convenience_monthly.csv")
annual = pd.read_csv(PROCESSED / "seven_eleven_japan_annual.csv")

df = sej.merge(jfa, on="month", how="left")
df["date"] = pd.to_datetime(df["month"])
df["fiscal_year"] = df["date"].dt.year - (df["date"].dt.month < 3)

# 1. Monthly 7-Eleven sales level -------------------------------------------------
# Gross total store sales keeps one accounting basis across FY2015-FY2025
annual["sales_myen"] = annual["gross_total_store_sales_myen"].fillna(annual["total_store_sales_myen"])

# First fiscal year: borrow the industry's monthly shape. Later: chain 7-Eleven's own changes.
df["path"] = float("nan")
first = df["fiscal_year"] == 2015
df.loc[first, "path"] = df.loc[first, "sales_all_myen"]
for i in df.index[~first]:
    df.loc[i, "path"] = df.loc[i - 12, "path"] * (1 + df.loc[i, "total_store_sales_yoy_pct"] / 100)

# How well do the chained monthly changes reproduce the published yearly growth?
by_fy = df.groupby("fiscal_year")["path"].sum().to_frame("chained")
by_fy = by_fy.join(annual.set_index("fiscal_year")["sales_myen"])
by_fy["chained_growth"] = by_fy["chained"].pct_change() * 100
by_fy["published_growth"] = by_fy["sales_myen"].pct_change() * 100
print("Yearly growth: chained monthly changes vs. published yearly totals (%)")
print(by_fy[["chained_growth", "published_growth"]].round(2).dropna().to_string())

# Scale each fiscal year to the published total (latest year: carry the last scale forward)
scale = (by_fy["sales_myen"] / by_fy["chained"]).ffill()
df["sej_sales_myen"] = df["path"] * df["fiscal_year"].map(scale).fillna(scale.iloc[-1])

# 2. Share of industry sales and the rest of the industry ---------------------------
df["sej_share"] = df["sej_sales_myen"] / df["sales_all_myen"]
df["w"] = df["sej_share"].shift(12)  # last year's share weights this year's growth


def rest_growth(industry, seven, w):
    return (industry - w * seven) / (1 - w)


pairs = {"sales": ("sales_same_yoy_pct", "same_store_sales_yoy_pct"),
         "customers": ("customers_same_yoy_pct", "same_store_customers_yoy_pct")}
for name, (ind, sev) in pairs.items():
    df[f"rest_{name}_yoy_pct"] = rest_growth(df[ind], df[sev], df["w"])
for name, (ind, sev) in [("customers", pairs["customers"])]:
    df["rest_customers_low"] = rest_growth(df[ind], df[sev], df["w"] * 0.9)
    df["rest_customers_high"] = rest_growth(df[ind], df[sev], df["w"] * 1.1)
df["rest_spend_yoy_pct"] = ((1 + df["rest_sales_yoy_pct"] / 100)
                            / (1 + df["rest_customers_yoy_pct"] / 100) - 1) * 100

df["gap_customers"] = df["same_store_customers_yoy_pct"] - df["rest_customers_yoy_pct"]
df["gap_sales"] = df["same_store_sales_yoy_pct"] - df["rest_sales_yoy_pct"]

keep = ["month", "sej_sales_myen", "sej_share", "same_store_sales_yoy_pct",
        "rest_sales_yoy_pct", "same_store_customers_yoy_pct", "rest_customers_yoy_pct",
        "rest_customers_low", "rest_customers_high", "same_store_spend_yoy_pct",
        "rest_spend_yoy_pct", "gap_customers", "gap_sales"]
out = df.dropna(subset=["sales_all_myen"])[keep]
out.to_csv(PROCESSED / "part2_rest_of_industry.csv", index=False)

# Calendar-year summary (months with a comparison only)
cmp = df.dropna(subset=["rest_customers_yoy_pct"]).copy()
cmp["year"] = cmp["date"].dt.year
summary = cmp.groupby("year").agg(
    months=("month", "size"),
    share_of_industry_sales=("sej_share", "mean"),
    sej_customers=("same_store_customers_yoy_pct", "mean"),
    rest_customers=("rest_customers_yoy_pct", "mean"),
    rest_customers_low=("rest_customers_low", "mean"),
    rest_customers_high=("rest_customers_high", "mean"),
    sej_spend=("same_store_spend_yoy_pct", "mean"),
    rest_spend=("rest_spend_yoy_pct", "mean"),
    sej_sales=("same_store_sales_yoy_pct", "mean"),
    rest_sales=("rest_sales_yoy_pct", "mean"),
)
summary["share_of_industry_sales"] *= 100
print("\nSame-store growth by calendar year, average of monthly % changes")
print(summary.round(1).to_string())

# Months 7-Eleven beat the rest on customers, before and after 2022
cmp["period"] = pd.cut(cmp["year"], [2015, 2019, 2021, 2026], labels=["2016-19", "2020-21", "2022-26"])
print("\nShare of months 7-Eleven's customer growth beat the rest of the industry")
print((cmp.groupby("period", observed=True)["gap_customers"].apply(lambda g: (g > 0).mean() * 100)).round(0).to_string())
print("\nAverage customer gap, 7-Eleven minus rest (points)")
print(cmp.groupby("period", observed=True)["gap_customers"].mean().round(2).to_string())

# Customer index: chain same-store growth into a level, 2019 = 100 -----------------
# Growth vs. a year earlier exaggerates a rebound after a deep fall (base effect),
# so the comparison that matters is how far each side is from its 2019 level.
idx = cmp.set_index("date")[["same_store_customers_yoy_pct", "rest_customers_yoy_pct",
                             "rest_customers_low", "rest_customers_high"]].copy()
for col in idx.columns:
    level = []
    for i, g in enumerate(idx[col]):
        level.append(100.0 if i < 12 else level[i - 12] * (1 + g / 100))
    idx[col] = level
idx = idx / idx.loc["2019"].mean() * 100
idx.columns = ["sej", "rest", "rest_low", "rest_high"]
idx.round(2).to_csv(PROCESSED / "part2_customer_index.csv")
yearly = idx.groupby(idx.index.year).mean()
print("\nCustomer index by calendar year (2019 = 100)")
print(yearly.round(1).to_string())

# Smooth with a 12-month average so seasonality and month-to-month noise drop out
plot = idx.rolling(12).mean().dropna()
fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(100, color=style.TEXT_MUTED, linewidth=0.8)
ax.fill_between(plot.index, plot["rest_low"], plot["rest_high"], color=style.REST, alpha=0.15, linewidth=0)
ax.plot(plot.index, plot["rest"], color=style.REST, label="Rest of industry")
ax.plot(plot.index, plot["sej"], color=style.SEVEN_ELEVEN, label="7-Eleven Japan")
last = plot.index[-1]
for col, text, color, nudge in [("sej", "7-Eleven", style.SEVEN_ELEVEN, -7), ("rest", "Rest of industry", style.REST, 7)]:
    y = plot[col].iloc[-1]
    ax.plot([last], [y], "o", color=color, markersize=6, markeredgecolor=style.SURFACE, markeredgewidth=1.5)
    ax.annotate(f"{text} {y:.0f}", (last, y), xytext=(8, nudge), textcoords="offset points",
                va="center", color=style.TEXT, fontsize=10)
ax.set_title("7-Eleven lost its pandemic lead: rivals have won back more customers")
ax.set_ylabel("Same-store customers, 2019 = 100\n(12-month average)")
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_xlim(plot.index[0], last + pd.Timedelta(days=420))
ax.legend(loc="lower left")
fig.text(0.01, 0.01, "Built by chaining same-store growth. Shaded band: 7-Eleven's share of customers 10% "
         "below or above its share of sales. Sources: Seven & i, JFA.",
         color=style.TEXT_MUTED, fontsize=8)
plt.tight_layout(rect=(0, 0.03, 1, 1))
plt.savefig(FIGURES / "part2_customers_vs_rest.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part2_customers_vs_rest.png'}")

"""Part 2, step 2: how much of 7-Eleven's higher spend per customer is just higher prices?

1. A convenience-store price index from the official CPI, built on 7-Eleven's own
   four product groups. Inside each group, CPI items are combined with the CPI's
   own weights. The groups are combined with 7-Eleven's sales mix from the
   previous fiscal year (so the mix can't react to the same year's prices).
2. Same-store spend per customer is split into price and "real basket"
   (what people buy, at constant prices): real = (1 + spend) / (1 + prices) - 1.

Assumption: CPI has no clean "convenience-store non-food" item. Cigarettes are the
bulk of it, so non-food = 75% cigarettes + 25% everyday goods (tissue, batteries,
magazines). Results are also shown with 50% and 100% cigarettes.
Caveat: CPI prices include consumption tax; store sales are reported before tax.
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from config import RAW, PROCESSED, FIGURES
import style

GROUPS = {  # 7-Eleven product group -> CPI items (Japanese names as in the CPI file)
    "fast_food": ["弁当Ａ", "弁当Ｂ", "おにぎり", "調理パン", "からあげ", "コロッケ", "コーヒー（外食）Ａ"],
    "daily_food": ["パン", "牛乳・乳製品"],
    "processed_food": ["飲料", "酒類", "菓子類", "カップ麺"],
    "nonfood_other": ["ティシュ・トイレットペーパー", "電池", "雑誌", "週刊誌"],
    "cigarettes": ["たばこ"],
}

raw = pd.read_csv(RAW / "cpi" / "cpi_by_item.csv", encoding="shift_jis", header=None, low_memory=False)
names, weights = raw.iloc[0], pd.to_numeric(raw.iloc[4], errors="coerce")
data = raw.iloc[6:].copy()
data.index = pd.to_datetime(data[0].astype(str), format="%Y%m")


def column_of(name):
    matches = [c for c in raw.columns if names[c] == name]
    return matches[0]  # first match is the group/item itself, not a sub-item


# Group change = weighted average of item changes, using only items priced in both
# years (bento B only enters the CPI in Jan 2015; averaging levels would jump then)
yoy = pd.DataFrame(index=data.index)
for group, items in GROUPS.items():
    cols = [column_of(i) for i in items]
    item_yoy = data[cols].apply(pd.to_numeric, errors="coerce").pct_change(12, fill_method=None) * 100
    w = item_yoy.notna() * weights[cols].values
    yoy[group] = (item_yoy.fillna(0) * w).sum(axis=1) / w.sum(axis=1)
yoy["cpi_all"] = pd.to_numeric(data[column_of("総合")], errors="coerce").pct_change(12) * 100
yoy = yoy.loc["2015-03":]

# 7-Eleven's sales mix, previous fiscal year (FY = March to February)
annual = pd.read_csv(PROCESSED / "seven_eleven_japan_annual.csv").set_index("fiscal_year")
mix = annual[["sales_fast_food_myen", "sales_daily_food_myen", "sales_processed_food_myen", "sales_nonfood_myen"]]
mix = mix.div(mix.sum(axis=1), axis=0)
mix.columns = ["fast_food", "daily_food", "processed_food", "nonfood"]
print("7-Eleven sales mix (% of sales)")
print((mix * 100).round(1).loc[[2015, 2019, 2025]].to_string())


def cvs_price_yoy(cigarette_share):
    fy = yoy.index.year - (yoy.index.month < 3)
    m = mix.reindex(fy - 1).ffill().bfill()  # previous year's mix; edges use nearest year
    m.index = yoy.index
    nonfood = cigarette_share * yoy["cigarettes"] + (1 - cigarette_share) * yoy["nonfood_other"]
    return (m["fast_food"] * yoy["fast_food"] + m["daily_food"] * yoy["daily_food"]
            + m["processed_food"] * yoy["processed_food"] + m["nonfood"] * nonfood)


prices = pd.DataFrame({"cvs_price_yoy_pct": cvs_price_yoy(0.75),
                       "cvs_price_yoy_pct_cig50": cvs_price_yoy(0.50),
                       "cvs_price_yoy_pct_cig100": cvs_price_yoy(1.00),
                       "cpi_all_yoy_pct": yoy["cpi_all"]})
for g in ["fast_food", "daily_food", "processed_food", "cigarettes"]:
    prices[f"{g}_price_yoy_pct"] = yoy[g]
prices.index = prices.index.strftime("%Y-%m")

# Split 7-Eleven's (and the rest of the industry's) spend per customer
rest = pd.read_csv(PROCESSED / "part2_rest_of_industry.csv").set_index("month")
sej = pd.read_csv(PROCESSED / "seven_eleven_japan_monthly.csv").set_index("month")
df = sej[["same_store_sales_yoy_pct", "same_store_customers_yoy_pct", "same_store_spend_yoy_pct"]].join(
    rest[["rest_spend_yoy_pct", "rest_customers_yoy_pct", "rest_sales_yoy_pct"]]).join(prices, how="inner")


def real(nominal, price):
    return ((1 + nominal / 100) / (1 + price / 100) - 1) * 100


for suffix in ["", "_cig50", "_cig100"]:
    df[f"sej_real_basket_yoy_pct{suffix}"] = real(df["same_store_spend_yoy_pct"], df[f"cvs_price_yoy_pct{suffix}"])
df["rest_real_basket_yoy_pct"] = real(df["rest_spend_yoy_pct"], df["cvs_price_yoy_pct"])
df.to_csv(PROCESSED / "part2_prices.csv")

df["year"] = df.index.str[:4].astype(int)
summary = df.groupby("year")[["cpi_all_yoy_pct", "cvs_price_yoy_pct", "fast_food_price_yoy_pct",
                              "cigarettes_price_yoy_pct", "same_store_spend_yoy_pct",
                              "sej_real_basket_yoy_pct", "sej_real_basket_yoy_pct_cig50",
                              "sej_real_basket_yoy_pct_cig100", "rest_real_basket_yoy_pct"]].mean()
print("\nYearly averages of monthly % changes vs. a year earlier")
print(summary.round(1).to_string())

# Cumulative picture since 2019: chain each monthly change into an index, 2019 = 100
levels = df[["same_store_sales_yoy_pct", "same_store_customers_yoy_pct", "cvs_price_yoy_pct",
             "sej_real_basket_yoy_pct"]].copy()
levels.index = pd.to_datetime(levels.index)
for col in levels.columns:
    out = []
    for i, g in enumerate(levels[col]):
        out.append(100.0 if i < 12 else out[i - 12] * (1 + g / 100))
    levels[col] = out
levels = levels / levels.loc["2019"].mean() * 100
levels.columns = ["sales", "customers", "prices", "real_basket"]
yearly = levels.groupby(levels.index.year).mean()
print("\n7-Eleven same-store index by year (2019 = 100)")
print(yearly.round(1).to_string())
latest = levels.rolling(12).mean().iloc[-1]
print(f"\nLatest 12 months vs. 2019: sales {latest['sales']:.1f}, customers {latest['customers']:.1f}, "
      f"prices {latest['prices']:.1f}, real basket per customer {latest['real_basket']:.1f}")
print(f"Check: customers x prices x real basket = {latest['customers'] * latest['prices'] * latest['real_basket'] / 1e4:.1f} "
      f"(sales {latest['sales']:.1f})")

# Figure: the four indexes, 12-month average ----------------------------------------
plot = levels.rolling(12).mean().dropna().loc["2017":]
lines = [("prices", "Convenience-store prices", style.FOURTH),
         ("sales", "Same-store sales", style.SEVEN_ELEVEN),
         ("real_basket", "Real basket per customer", style.THIRD),
         ("customers", "Customers", style.REST)]
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.axhline(100, color=style.TEXT_MUTED, linewidth=0.8)
for col, label, color in lines:
    ax.plot(plot.index, plot[col], color=color, label=label)
last = plot.index[-1]
ends = sorted(((plot[c].iloc[-1], l, color) for c, l, color in lines), reverse=True)
for k, (y, label, color) in enumerate(ends):
    ax.plot([last], [y], "o", color=color, markersize=6, markeredgecolor=style.SURFACE, markeredgewidth=1.5)
    ax.annotate(f"{label} {y:.0f}", (last, y), xytext=(8, 0), textcoords="offset points",
                va="center", color=style.TEXT, fontsize=10)
ax.set_title("7-Eleven's sales growth since 2019 is price, not more shopping")
ax.set_ylabel("Index, 2019 = 100 (12-month average)")
ax.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(2017, last.year + 1)]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_xlim(plot.index[0], last + pd.Timedelta(days=900))
ax.spines["bottom"].set_bounds(mdates.date2num(plot.index[0]), mdates.date2num(last))
ax.legend(loc="upper left")
fig.text(0.01, 0.01, "Same stores. Prices: official CPI items grouped and weighted like 7-Eleven's sales. "
         "Real basket = spend per customer at constant prices.\nSources: Seven & i, Statistics Bureau of Japan.",
         color=style.TEXT_MUTED, fontsize=8)
plt.tight_layout(rect=(0, 0.05, 1, 1))
plt.savefig(FIGURES / "part2_price_vs_volume.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part2_price_vs_volume.png'}")

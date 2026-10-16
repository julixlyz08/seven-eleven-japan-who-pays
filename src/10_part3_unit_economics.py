"""Part 3: who pays when wages and prices rise, head office or the store owner?

Store model: src/franchise_model.py (a Type C, 24-hour, single-store owner).
Cost assumptions: data/manual/store_cost_assumptions.csv (low / central / high).

1. Calibration. 7-Eleven gives a "5-year incentive" and other reductions whose size
   isn't published. Seven & i's accounts show what head office actually collects:
   revenue minus sales at company-run stores ~= charges paid by franchise owners.
   Dividing by franchise stores' gross profit gives the effective charge rate. The
   gap to the published schedule is the undisclosed incentive, by fiscal year.
   (Assumes the same incentive share for Type A and Type C stores.)
2. Check against a leaked internal simulation (Diamond, Oct 2025): with sales and
   margins unchanged, owner profit falls to about a third at a 1,500 yen minimum wage.
3. Where the gross profit goes today, for an established store and for a new store
   under the current and the 2027 contract.
4. History FY2015-FY2025 and projection to FY2030 (minimum wage reaching 1,500 yen).
5. Break-even sales by prefecture: daily sales needed for the owner to earn at least
   the local minimum wage for their own hours.
6. Monte Carlo: 2,000 draws of the uncertain costs and incentive.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import RAW, PROCESSED, FIGURES
import franchise_model as fm
import style

p = fm.load_assumptions("central")
annual = pd.read_csv(PROCESSED / "seven_eleven_japan_annual.csv").set_index("fiscal_year")
mw = pd.read_csv(PROCESSED / "minimum_wage.csv")
nat_mw = mw[mw["prefecture"] == "national_weighted_average"].set_index("fiscal_year")["hourly_wage_yen"]


def store_year_wage(fy, wages=nat_mw):
    """7-Eleven's fiscal year runs Mar-Feb; new minimum wages take effect around October,
    so Mar-Sep uses the previous rate and Oct-Feb the new one."""
    return 7 / 12 * wages[fy - 1] + 5 / 12 * wages[fy]


# 1. Calibration from Seven & i's accounts ------------------------------------------
cal = annual[["revenue_myen", "gross_total_store_sales_myen", "total_store_sales_myen", "gross_margin_pct",
              "daily_sales_per_store_kyen", "stores_type_a", "stores_type_c", "stores_company_run"]].copy()
cal["chain_sales"] = cal["gross_total_store_sales_myen"].fillna(cal["total_store_sales_myen"]) * 1e6
cal["company_store_sales"] = cal["stores_company_run"] * cal["daily_sales_per_store_kyen"] * 1e3 * 365
cal["commission"] = cal["revenue_myen"] * 1e6 - cal["company_store_sales"]
cal["franchise_gp"] = (cal["chain_sales"] - cal["company_store_sales"]) * cal["gross_margin_pct"] / 100
cal["effective_rate"] = cal["commission"] / cal["franchise_gp"]
gp_month = cal["daily_sales_per_store_kyen"] * 1e3 * fm.DAYS_PER_MONTH * cal["gross_margin_pct"] / 100
rate_c = fm.charge(gp_month.values, "current") / gp_month.values
rate_a = (0.45 - 0.03) - 35_000 / gp_month.values  # Type A: 45%, same reductions above 5.5M yen
w_a = cal["stores_type_a"] / (cal["stores_type_a"] + cal["stores_type_c"])
cal["schedule_rate_c"] = rate_c
cal["incentive_pct"] = (w_a * rate_a + (1 - w_a) * rate_c - cal["effective_rate"]).clip(lower=0)
cal[["effective_rate", "schedule_rate_c", "incentive_pct"]].round(4).to_csv(PROCESSED / "part3_calibration.csv")
print("Effective charge rate from the accounts vs. the published Type C schedule (average store)")
print((cal[["effective_rate", "schedule_rate_c", "incentive_pct"]] * 100).round(1).to_string())
INCENTIVE = cal.loc[2025, "incentive_pct"]

# 2. Check against the leaked simulation ---------------------------------------------
sales25, margin25 = annual.loc[2025, "daily_sales_per_store_kyen"] * 1e3, annual.loc[2025, "gross_margin_pct"] / 100
base = fm.store_pnl(sales25, margin25, store_year_wage(2025), p, "current", INCENTIVE)
at1500 = fm.store_pnl(sales25, margin25, 1500, p, "current", INCENTIVE)
ratio = float(at1500["owner_profit"] / base["owner_profit"])
print(f"\nCheck: owner profit at a 1,500 yen minimum wage = {ratio:.2f} x today's "
      f"(leaked 7-Eleven simulation: about 1/3)")

# 3. Where the gross profit goes, FY2026 ---------------------------------------------
wage26 = store_year_wage(2026)
new_store_sales = annual.loc[2025, "daily_sales_new_store_kyen"] * 1e3
cases = {
    "Established store, current contract": (sales25, "current", INCENTIVE),
    "New store, current contract": (new_store_sales, "current", 0.0),
    "New store, 2027 contract": (new_store_sales, "new_2027", 0.0),
}
rows = []
for name, (sales, contract, inc) in cases.items():
    r = fm.store_pnl(sales, margin25, wage26, p, contract, inc)
    gp = float(r["gross_profit"])
    rows.append({"case": name, "daily_sales": sales, "gross_profit_month": gp,
                 "head_office_net": float(r["hq_net"]),
                 "head_office_cost_shares": float(r["charge"] - r["hq_net"]), "staff": float(r["staff"]),
                 "owner_other_costs": float(r["owner_utilities"] + r["owner_waste"] + r["other"]),
                 "owner_profit": float(r["owner_profit"]), "owner_hourly": float(r["owner_hourly"]),
                 "hq_share_of_extra_gp": float(fm.marginal_charge_rate(gp, contract, inc))})
split = pd.DataFrame(rows).set_index("case")
split.round(3).to_csv(PROCESSED / "part3_split.csv")
print(f"\nFY2026 (minimum wage {wage26:,.0f} yen in the store's year), per store per month (yen)")
print(split.drop(columns="hq_share_of_extra_gp").round(0).to_string())
print("Head office's share of one extra yen of gross profit: "
      + ", ".join(f"{k} {v:.0%}" for k, v in split["hq_share_of_extra_gp"].items()))

# 4. History and projection ------------------------------------------------------------
cpi = pd.read_csv(RAW / "cpi" / "cpi_by_category.csv", encoding="shift_jis", header=None, low_memory=False)
cpi_data = cpi.iloc[6:].copy()
cpi_data.index = pd.to_datetime(cpi_data[0].astype(str), format="%Y%m")
cpi_fy = lambda col: pd.to_numeric(cpi_data[col], errors="coerce").groupby(
    cpi_data.index.year - (cpi_data.index.month < 3)).mean()
energy_fy, all_fy = cpi_fy(30), cpi_fy(1)  # fuel, light & water; all items

G_WAGE = (1500 / nat_mw[2026]) ** (1 / 4) - 1  # 1,500 yen by FY2030
G_SALES, G_COSTS = 0.02, 0.02
wages = nat_mw.copy()
for fy in range(2027, 2031):
    wages[fy] = wages[fy - 1] * (1 + G_WAGE)


def year_inputs(fy, sales_growth=G_SALES, cost_growth=G_COSTS, energy=None):
    if fy <= 2025:
        sales = annual.loc[fy, "daily_sales_per_store_kyen"] * 1e3
        margin = annual.loc[fy, "gross_margin_pct"] / 100
        util_scale = energy_fy[fy] / energy_fy[2025]
        other_scale = all_fy[fy] / all_fy[2025]
        inc = cal.loc[fy, "incentive_pct"]
    else:
        k = fy - 2025
        sales, margin = sales25 * (1 + sales_growth) ** k, margin25
        util_scale = other_scale = (1 + cost_growth) ** k
        inc = INCENTIVE
    return sales, margin, store_year_wage(fy, wages), util_scale, other_scale, inc


hist = []
for fy in range(2016, 2031):
    sales, margin, wage, us, os_, inc = year_inputs(fy)
    r = fm.store_pnl(sales, margin, wage, p, "current", inc,
                     utilities=p["utilities_month_fy2025"] * us, other=p["other_month_fy2025"] * os_)
    hist.append({"fiscal_year": fy, "daily_sales": sales, "store_year_min_wage": wage,
                 "hq_net": float(r["hq_net"]), "charge": float(r["charge"]), "staff": float(r["staff"]),
                 "owner_profit": float(r["owner_profit"]), "owner_hourly": float(r["owner_hourly"])})
hist = pd.DataFrame(hist).set_index("fiscal_year")
hist.round(0).to_csv(PROCESSED / "part3_history_projection.csv")
idx = hist[["daily_sales", "store_year_min_wage", "hq_net", "owner_profit"]] / \
      hist.loc[2019, ["daily_sales", "store_year_min_wage", "hq_net", "owner_profit"]] * 100
print("\nEstablished Type C store, FY2019 = 100 (FY2026 onward: projection)")
print(idx.round(0).to_string())
d = hist.loc[2025] - hist.loc[2019]
print(f"\nFY2019 -> FY2025 per store per month: head office {d['hq_net'] / 1e3:+,.0f}k yen, "
      f"staff costs {d['staff'] / 1e3:+,.0f}k yen, owner profit {d['owner_profit'] / 1e3:+,.0f}k yen")

# 5. Break-even sales by prefecture ----------------------------------------------------
def break_even(wage, contract, inc, params=p, lo=300_000, hi=1_200_000):
    """Daily sales at which the owner's profit per own hour equals the minimum wage."""
    lo, hi = np.full_like(wage, lo, dtype=float), np.full_like(wage, hi, dtype=float)
    for _ in range(40):
        mid = (lo + hi) / 2
        r = fm.store_pnl(mid, margin25, wage, params, contract, inc)
        short = r["owner_hourly"] < wage
        lo, hi = np.where(short, mid, lo), np.where(short, hi, mid)
    return (lo + hi) / 2


pref = mw[(mw["prefecture"] != "national_weighted_average")].pivot(index="prefecture", columns="fiscal_year",
                                                                   values="hourly_wage_yen")
pref_wage = (7 / 12 * pref[2025] + 5 / 12 * pref[2026]).values
be = pd.DataFrame({"store_year_min_wage": pref_wage,
                   "established_current": break_even(pref_wage, "current", INCENTIVE),
                   "new_store_current": break_even(pref_wage, "current", 0.0),
                   "new_store_2027": break_even(pref_wage, "new_2027", 0.0)}, index=pref.index)
be = be.sort_values("store_year_min_wage")
be.round(0).to_csv(PROCESSED / "part3_break_even_by_prefecture.csv")
print("\nDaily sales needed for the owner to earn the local minimum wage (FY2026, yen)")
print(pd.concat([be.head(3), be.tail(3)]).round({"store_year_min_wage": 0, "established_current": -3,
                                                  "new_store_current": -3, "new_store_2027": -3}).to_string())
print(f"For reference: average store {sales25:,.0f}; average new store {new_store_sales:,.0f}")

# 6. Monte Carlo -----------------------------------------------------------------------
N = 2000
rng = np.random.default_rng(3)
lowhigh = pd.read_csv(fm.MANUAL / "store_cost_assumptions.csv").set_index("parameter")
draws = {k: rng.triangular(lowhigh.loc[k, "low"], lowhigh.loc[k, "central"], lowhigh.loc[k, "high"], N)
         for k in lowhigh.index}
inc_draw = np.clip(INCENTIVE + rng.uniform(-0.03, 0.03, N), 0, None)
mc = {}
for name, (sales, contract, inc) in cases.items():
    inc_used = inc_draw if inc > 0 else 0.0
    r = fm.store_pnl(sales, margin25, wage26, draws, contract, inc_used)
    mc[name] = r["owner_profit"] * 12
mc = pd.DataFrame(mc)
print("\nOwner profit per year, FY2026, Monte Carlo (million yen): median [5th - 95th percentile]")
for col in mc:
    q = mc[col].quantile([0.05, 0.5, 0.95]) / 1e6
    print(f"  {col}: {q[0.5]:.1f} [{q[0.05]:.1f} to {q[0.95]:.1f}]")
check = (fm.store_pnl(sales25, margin25, 1500, draws, "current", inc_draw)["owner_profit"]
         / fm.store_pnl(sales25, margin25, store_year_wage(2025), draws, "current", inc_draw)["owner_profit"])
check = check[np.isfinite(check)]
print(f"  Owner profit at 1,500 yen vs. FY2025, across draws: median {np.median(check):.2f}, "
      f"middle 90% {np.percentile(check, 5):.2f} to {np.percentile(check, 95):.2f} (leak: about 0.33)")
better = (mc["New store, 2027 contract"] > mc["New store, current contract"]).mean()
print(f"  New store better off under the 2027 contract in {better * 100:.0f}% of draws; "
      f"median gain {(mc['New store, 2027 contract'] - mc['New store, current contract']).median() / 1e6:.1f}M yen a year")

# Projection band: FY2030 owner profit with uncertain costs, sales growth and incentive
g_sales = rng.uniform(0.0, 0.04, N)
proj = []
for fy in range(2026, 2031):
    k = fy - 2025
    sales = sales25 * (1 + g_sales) ** k
    scale = (1 + G_COSTS) ** k
    params = dict(draws, utilities_month_fy2025=draws["utilities_month_fy2025"] * scale,
                  other_month_fy2025=draws["other_month_fy2025"] * scale)
    r = fm.store_pnl(sales, margin25, store_year_wage(fy, wages), params, "current", inc_draw)
    proj.append(np.percentile(r["owner_profit"], [5, 50, 95]))
proj = pd.DataFrame(proj, index=range(2026, 2031), columns=["p5", "p50", "p95"])
proj.round(0).to_csv(PROCESSED / "part3_projection_band.csv")
print("\nEstablished store owner profit per month, projection (yen): 5th / median / 95th percentile")
print(proj.round(-3).to_string())

# Figure 1: where each store's gross profit goes -------------------------------------
parts = [("head_office_net", "Head office keeps", style.SEVEN_ELEVEN),
         ("head_office_cost_shares", "Head office's share of utilities and discarded stock", style.GRID),
         ("staff", "Staff wages", style.REST),
         ("owner_other_costs", "Owner's utilities, discarded stock, other", style.FOURTH),
         ("owner_profit", "Owner's profit (pays the owner's own hours)", style.THIRD)]
shares = split[[k for k, _, _ in parts]].div(split["gross_profit_month"], axis=0) * 100
fig, ax = plt.subplots(figsize=(9, 3.8))
y = np.arange(len(shares))[::-1]
left = np.zeros(len(shares))
for key, label, color in parts:
    vals = shares[key].clip(lower=0).values
    ax.barh(y, vals, left=left, color=color, edgecolor=style.SURFACE, linewidth=2, height=0.6, label=label)
    for yi, l, v in zip(y, left, vals):
        if v >= 6 and color != style.GRID:
            ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center", color="white", fontsize=9.5,
                    fontweight="bold")
    left += vals
# A loss can't be drawn as a segment: say it in words at the end of the bar
for yi, l, v in zip(y, left, shares["owner_profit"].values):
    if v < 0:
        ax.text(l + 1, yi, f"Owner loses {abs(v):.0f}%", va="center", color=style.TEXT, fontsize=9)
ax.set_yticks(y, [f"{c}\n(¥{s / 1e3:,.0f}k a day)" for c, s in zip(shares.index, split["daily_sales"])])
ax.set_xlim(0, 115)
ax.set_xticks(range(0, 101, 20))
ax.set_xlabel("Share of the store's gross profit (%)")
ax.set_title("Where a 7-Eleven store's gross profit goes, FY2026")
ax.grid(axis="y", visible=False)
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.22), ncol=2, fontsize=8.5)
fig.text(0.01, 0.01, "Type C (head office provides the building), 24 hours, single store. Central cost assumptions. "
         "Established store includes the incentives implied by Seven & i's accounts.",
         color=style.TEXT_MUTED, fontsize=7.5)
plt.tight_layout(rect=(0, 0.03, 1, 1))
plt.savefig(FIGURES / "part3_gross_profit_split.png", dpi=200)
plt.close()

# Figure 2: who absorbed the rise in costs --------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(100, color=style.TEXT_MUTED, linewidth=0.8)
band = proj[["p5", "p95"]] / hist.loc[2019, "owner_profit"] * 100
ax.fill_between(band.index, band["p5"], band["p95"], color=style.THIRD, alpha=0.15, linewidth=0)
series = [("store_year_min_wage", "Minimum wage", style.REST),
          ("hq_net", "Head office's take per store", style.SEVEN_ELEVEN),
          ("daily_sales", "Sales per store", style.FOURTH),
          ("owner_profit", "Owner's profit per store", style.THIRD)]
for col, label, color in series:
    hist_part, proj_part = idx[col].loc[:2025], idx[col].loc[2025:]
    ax.plot(hist_part.index, hist_part, color=color, label=label)
    ax.plot(proj_part.index, proj_part, color=color, linestyle="--", linewidth=1.5)
    nudge = {"daily_sales": 5, "hq_net": -5}.get(col, 0)
    ax.annotate(f"{label} {idx[col].iloc[-1]:.0f}", (2030, idx[col].iloc[-1]), xytext=(8, nudge),
                textcoords="offset points", va="center", color=style.TEXT, fontsize=9.5)
ax.axvspan(2025.5, 2030.4, color=style.GRID, alpha=0.35, linewidth=0)
ax.text(2025.7, ax.get_ylim()[1] * 0.98, "Projection", color=style.TEXT_MUTED, fontsize=9, va="top")
ax.set_xlim(2016, 2033.5)
ax.set_xticks(range(2016, 2031, 2))
ax.set_ylabel("FY2019 = 100")
ax.set_title("Rising wages land on the owner, not on head office")
fig.text(0.01, 0.01, "Established Type C store, central assumptions. FY2015-25: actual sales, margins, minimum wages "
         "and incentives implied by the accounts.\nProjection: minimum wage to 1,500 yen by FY2030, sales +2% a year; "
         "shaded: 90% range of owner's profit (Monte Carlo).", color=style.TEXT_MUTED, fontsize=7.5)
plt.tight_layout(rect=(0, 0.06, 1, 1))
plt.savefig(FIGURES / "part3_who_absorbs.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part3_gross_profit_split.png'} and {FIGURES / 'part3_who_absorbs.png'}")

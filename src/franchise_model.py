"""Monthly profit and loss of a 7-Eleven franchise store, under each contract.

All functions take numpy arrays, so one call can run thousands of Monte Carlo draws.

How the money flows (Type C: head office provides land and building):
  sales x gross margin = gross profit (before deducting discarded stock: 7-Eleven's
                         "convenience-store accounting", reviewed by the Supreme Court in 2007)
  - charge to head office (tiered % of gross profit, minus reductions)
  = owner's gross income
  - staff wages, the owner's share of utilities and of discarded stock, other costs
  = owner's profit (pays the owner's and family's own hours)
Head office keeps the charge minus its share of utilities and discarded stock.
Contract terms are read from data/manual/franchise_terms.csv.
"""
import numpy as np
import pandas as pd
from config import MANUAL

DAYS_PER_MONTH = 365 / 12
NIGHT_PREMIUM = 0.25      # legal minimum premium for 22:00-05:00
NIGHT_PREMIUM_HOURS = 7   # of the 8 night hours (05:00-06:00 is not premium time)

terms = pd.read_csv(MANUAL / "franchise_terms.csv")
T = {(r.contract, r.term): r.value for r in terms.itertuples()}

CONTRACTS = {
    # Current Type C (single store, 24 hours). Reductions depend on monthly gross profit:
    # over 5.5M yen: 2% + 1% of gross profit + 35,000 yen; under 5.5M yen: 200,000 yen.
    # 7-Eleven also gives a "5-year incentive" and other reductions whose size is not
    # published; `incentive_pct` (share of gross profit) stands in for them.
    "current": {
        "tiers": [(2_500_000, T["type_c", "charge_tier_0_2.5m"]), (4_000_000, T["type_c", "charge_tier_2.5m_4m"]),
                  (5_500_000, T["type_c", "charge_tier_4m_5.5m"]), (np.inf, T["type_c", "charge_tier_above_5.5m"])],
        "high_gp_pct": (T["type_c", "reduction_24h"] + T["type_c", "reduction_special"]) / 100,
        "high_gp_fixed": T["type_c", "reduction_24h_monthly_high_gp"],
        "low_gp_fixed": T["type_c", "reduction_24h_monthly_low_gp"],
        "hq_utilities": T["type_c", "utilities_hq_share"] / 100,
        "hq_waste": T["type_c", "waste_hq_share"] / 100,
        "guarantee_month": T["type_c", "minimum_guarantee_24h"] / 12,
    },
    # New contract from about autumn 2027 (new stores only): two tiers, a flat
    # 200,000 yen 24-hour reduction, no other reductions listed. Its minimum
    # guarantee is not published; assumed unchanged.
    "new_2027": {
        "tiers": [(4_000_000, T["new_2027", "charge_tier_0_4m"]), (np.inf, T["new_2027", "charge_tier_above_4m"])],
        "high_gp_pct": 0.0,
        "high_gp_fixed": T["new_2027", "reduction_24h"],
        "low_gp_fixed": T["new_2027", "reduction_24h"],
        "hq_utilities": T["new_2027", "utilities_hq_share"] / 100,
        "hq_waste": T["new_2027", "waste_hq_share"] / 100,
        "guarantee_month": T["type_c", "minimum_guarantee_24h"] / 12,
    },
}


def load_assumptions(which="central"):
    a = pd.read_csv(MANUAL / "store_cost_assumptions.csv").set_index("parameter")
    return a[which].to_dict()


def charge(gross_profit, contract, incentive_pct=0.0):
    """Monthly charge for a monthly gross profit (each tier applies to its slice),
    after reductions and the minimum guarantee."""
    c = CONTRACTS[contract]
    gp = np.asarray(gross_profit, dtype=float)
    total, lower = 0.0, 0.0
    for upper, rate in c["tiers"]:
        total = total + np.clip(gp - lower, 0, upper - lower) * rate / 100
        lower = upper
    high = gp > 5_500_000
    total = total - np.where(high, c["high_gp_pct"] * gp + c["high_gp_fixed"], c["low_gp_fixed"])
    total = total - np.asarray(incentive_pct) * gp
    # Minimum guarantee: head office tops the owner's share up to the guaranteed level
    total = np.minimum(total, gp - c["guarantee_month"])
    return total


def marginal_charge_rate(gross_profit, contract, incentive_pct=0.0):
    """Share of one extra yen of gross profit that goes to head office."""
    gp = np.asarray(gross_profit, dtype=float)
    return (charge(gp + 1000, contract, incentive_pct) - charge(gp, contract, incentive_pct)) / 1000


def staff_cost(min_wage, p):
    """Monthly wage bill: paid hours = staffed hours minus the owner's own hours."""
    day_hours, night_hours = 16 * p["staff_day"], 8 * p["staff_night"]
    paid = np.maximum(day_hours + night_hours - p["owner_hours_per_day"], 0)
    # Night hours are paid first by staff (owners mostly cover the day); premium on 7 of 8
    paid_night = np.minimum(night_hours, paid)
    premium_hours = paid_night * NIGHT_PREMIUM_HOURS / 8
    wage = np.asarray(min_wage) * p["wage_premium"]
    daily = (paid + premium_hours * NIGHT_PREMIUM) * wage
    return daily * (1 + p["employer_oncost"]) * DAYS_PER_MONTH


def store_pnl(daily_sales, margin, min_wage, p, contract, incentive_pct=0.0, utilities=None, other=None):
    """Monthly P&L. `utilities` and `other` default to the FY2025-level assumptions."""
    c = CONTRACTS[contract]
    sales = np.asarray(daily_sales, dtype=float) * DAYS_PER_MONTH
    gp = sales * margin
    ch = charge(gp, contract, incentive_pct)
    utilities = p["utilities_month_fy2025"] if utilities is None else utilities
    other = p["other_month_fy2025"] if other is None else other
    waste = sales * p["waste_pct_sales"]
    staff = staff_cost(min_wage, p)
    owner_util, owner_waste = utilities * (1 - c["hq_utilities"]), waste * (1 - c["hq_waste"])
    owner_profit = gp - ch - staff - owner_util - owner_waste - other
    hq_net = ch - utilities * c["hq_utilities"] - waste * c["hq_waste"]
    return {"sales": sales, "gross_profit": gp, "charge": ch, "owner_gross": gp - ch, "staff": staff,
            "owner_utilities": owner_util, "owner_waste": owner_waste, "other": other + 0 * gp,
            "owner_profit": owner_profit, "hq_net": hq_net,
            "owner_hourly": owner_profit / (p["owner_hours_per_day"] * DAYS_PER_MONTH)}

"""Part 4: what is the stock market paying for 7-Eleven's Japanese stores?

Sum of the parts, solved for the one piece with no market price of its own:
    market value of Seven & i (shares + net debt + minority interests)
  - overseas convenience stores (7-Eleven Inc. and Australia) at a peer multiple
  - Seven Bank stake (at its share price) and York Holdings stake (rough)
  - small other businesses
  + head-office costs, capitalised (they reduce what the parts are worth together)
  = implied value of the Japanese convenience-store business

Balance sheet and share count: 28 Feb 2026 (the 2025 buyback was finished by
then, so shares and net debt match). Share price: latest close.
Leases are off balance sheet both for Seven & i (J-GAAP, US GAAP operating leases)
and in EBITDA after rent, so EV/EBITDA is on a like-for-like basis.
"""
import numpy as np
import openpyxl
import pandas as pd
import matplotlib.pyplot as plt
from config import RAW, MANUAL, PROCESSED, FIGURES
import style

v = pd.read_csv(MANUAL / "valuation_inputs.csv").set_index("item")["value"]
annual = pd.read_csv(PROCESSED / "seven_eleven_japan_annual.csv").set_index("fiscal_year")
prices = pd.read_csv(RAW / "prices" / "3382_T.csv", index_col=0, parse_dates=True)


def segment_table(block):
    """FY2025 values by segment from Seven & i's segment Excel (pre-reorganisation layout)."""
    ws = openpyxl.load_workbook(RAW / "seven_i_reports" / "Segment_Information_2026_02_en.xlsx", data_only=True).active
    rows = [[c for c in r if c is not None] for r in ws.iter_rows(values_only=True)]
    start = next(i for i, r in enumerate(rows) if r and r[0] == block)
    out = {}
    for r in rows[start + 2:]:
        if not r or r[0] == "Total":
            break
        out[r[0]] = float(r[-1])
    return pd.Series(out)


oi, da = segment_table("OPERATING INCOME"), segment_table("DEPRECIATION AND AMORTIZATION")
ebitda = (oi + da) / 1e3  # billion yen
print("FY2025 EBITDA by segment (billion yen)")
print(ebitda.round(1).to_string())

YEN_BN = 1e3  # values in the CSV are million yen; work in billion yen
shares = (v["shares_issued_after_cancellation"] - v["treasury_shares_after_cancellation"]) / 1e9
price = prices["Close"].iloc[-1]
price_date = prices.index[-1].date()
net_debt = (v["interest_bearing_debt"] - v["cash"]) / YEN_BN
nci = v["non_controlling_interests"] / YEN_BN
market_cap = price * shares
ev = market_cap + net_debt + nci

seven_bank = v["seven_bank_stake"] * v["seven_bank_market_cap"] / YEN_BN
YORK = {"low": 70.0, "central": 140.0, "high": 210.0}  # ~35% of a post-deal equity of ~400bn, very rough
others = ebitda["Others"] * 8
corporate_ebitda = ebitda["Eliminations / corporate"]  # negative
japan_ebitda, overseas_ebitda = ebitda["Domestic convenience store operations"], ebitda["Overseas convenience store operations"]
japan_net_income = annual.loc[2025, "net_income_myen"] / YEN_BN


def implied_japan(na_multiple, corp_multiple=9.0, york=YORK["central"], equity_value=None):
    equity = market_cap if equity_value is None else equity_value
    total = equity + net_debt + nci
    return total - overseas_ebitda * na_multiple - seven_bank - york - others - corporate_ebitda * corp_multiple


central = implied_japan(11.0)
print(f"\nShare price {price:,.0f} yen ({price_date}) x {shares:.3f}bn shares = market value {market_cap:,.0f}bn yen")
print(f"+ net debt {net_debt:,.0f}bn + minority interests {nci:,.0f}bn = enterprise value {ev:,.0f}bn")
parts = pd.Series({
    "Enterprise value of Seven & i": ev,
    "Overseas stores (11x EBITDA)": -overseas_ebitda * 11,
    "Seven Bank stake (market price)": -seven_bank,
    "York Holdings stake (rough)": -YORK["central"],
    "Other businesses (8x)": -others,
    "Head-office costs (9x, added back)": -corporate_ebitda * 9,
    "Implied value of Japanese stores": central,
})
print(parts.round(0).to_string())
print(f"\nJapanese stores: {central / japan_ebitda:.1f}x FY2025 EBITDA ({japan_ebitda:,.0f}bn), "
      f"{central / japan_net_income:.1f}x 7-Eleven Japan's net income ({japan_net_income:,.0f}bn)")
print(f"For comparison: KDDI paid {v['lawson_tender_offer_per_share'] / v['lawson_eps_fy2023']:.1f}x earnings for Lawson "
      "(IFRS, includes Lawson Bank)")

# Sensitivity: North American multiple x head-office multiple
na_grid, corp_grid = [9, 10, 11, 12, 13], [6, 9, 12]
sens = pd.DataFrame({f"head office {c}x": [implied_japan(m, c) / japan_ebitda for m in na_grid] for c in corp_grid},
                    index=[f"overseas {m}x" for m in na_grid])
print("\nImplied EV/EBITDA of the Japanese stores")
print(sens.round(1).to_string())
york_range = [implied_japan(11, 9, YORK[k]) / japan_ebitda for k in ("high", "low")]
print(f"York stake from {YORK['low']:.0f} to {YORK['high']:.0f}bn moves it between {york_range[0]:.1f}x and {york_range[1]:.1f}x")

# What would the Japanese stores be worth at other share prices?
rows = []
for label, px in [("Latest close", price), ("Couche-Tard's offer (2,600 yen)", v["couche_tard_offer_per_share"]),
                  ("Day after the withdrawal (Jul 17, 2025)", prices.loc["2025-07-17", "Close"])]:
    japan = implied_japan(11.0, equity_value=px * shares)
    rows.append({"share_price": px, "japan_value_bn": japan, "japan_ev_ebitda": japan / japan_ebitda,
                 "japan_pe": japan / japan_net_income})
at_prices = pd.DataFrame(rows, index=[r[0] for r in [("Latest close",), ("Couche-Tard",), ("Withdrawal",)]])
at_prices.index = ["Latest close", "Couche-Tard's offer", "Day after the withdrawal"]
print("\nImplied value of the Japanese stores at different share prices (today's balance sheet)")
print(at_prices.round(1).to_string())

# What multiple for Japan would make Japan "worth" a Lawson-style 20x earnings?
lawson_pe = v["lawson_tender_offer_per_share"] / v["lawson_eps_fy2023"]
japan_at_lawson = japan_net_income * lawson_pe
gap_per_share = (japan_at_lawson - central) / shares
print(f"\nValued like Lawson ({lawson_pe:.0f}x earnings), the Japanese stores would be worth {japan_at_lawson:,.0f}bn yen, "
      f"{gap_per_share:,.0f} yen per Seven & i share more than the market implies")

out = pd.concat([parts.rename("billion_yen"), pd.Series({"japan_ev_ebitda": central / japan_ebitda,
                                                         "japan_pe": central / japan_net_income})])
out.round(2).to_csv(PROCESSED / "part4_sum_of_parts.csv")
sens.round(2).to_csv(PROCESSED / "part4_sensitivity.csv")
at_prices.round(2).to_csv(PROCESSED / "part4_at_prices.csv")

# Figure: the bridge from Seven & i's value to the Japanese stores ---------------------
steps = list(parts.items())
fig, ax = plt.subplots(figsize=(9, 4.8))
y = np.arange(len(steps))[::-1]
running = 0.0
for yi, (label, val) in zip(y, steps):
    if label.startswith("Enterprise") or label.startswith("Implied"):
        left, width = 0, val
        color = style.SEVEN_ELEVEN if label.startswith("Implied") else style.TEXT_MUTED
        running = val if label.startswith("Enterprise") else running
    else:
        left, width = (running + val, -val) if val < 0 else (running, val)
        color = style.REST if val < 0 else style.THIRD
        running += val
    ax.barh(yi, width, left=left, color=color, height=0.6, edgecolor=style.SURFACE, linewidth=1.5)
    ax.text(left + width + 60, yi, f"{val:+,.0f}" if not label.startswith(("Enterprise", "Implied")) else f"{val:,.0f}",
            va="center", color=style.TEXT, fontsize=9.5)
ax.set_yticks(y, [s[0] for s in steps])
ax.set_xlabel("Billion yen")
ax.set_xlim(0, ev * 1.15)
ax.set_title(f"The share price implies ~{central / japan_ebitda:.0f}x EBITDA for the Japanese stores", x=-0.35)
ax.set_axisbelow(True)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
fig.text(0.01, 0.01, f"Share price {price:,.0f} yen on {price_date}; balance sheet and shares at 28 Feb 2026; "
         "FY2025 EBITDA. Overseas multiple: analysts' estimate for the\nNorth American business in Couche-Tard's bid "
         "(peers trade at 10-17x). Sources: Seven & i, Yahoo Finance, press reports.",
         color=style.TEXT_MUTED, fontsize=7.5)
plt.tight_layout(rect=(0, 0.06, 1, 1))
plt.savefig(FIGURES / "part4_sum_of_parts.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part4_sum_of_parts.png'}")

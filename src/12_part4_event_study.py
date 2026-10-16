"""Part 4, step 2: how did Seven & i's shares react to the takeover saga?

Market model: Seven & i's daily return = a + b x Japanese market return (TOPIX
ETF, 1306.T) + abnormal return, fitted over trading days 260 to 30 before each
event. Cumulative abnormal return (CAR) over the day before to two days after
the event day covers news released before, during or after trading hours.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from config import RAW, PROCESSED, FIGURES
import style

EVENTS = {
    "2024-08-19": "Couche-Tard's approach disclosed",
    "2024-10-09": "Raised offer (2,600 yen) reported",
    "2025-03-06": "Own plan: York sale, new CEO, US listing",
    "2025-07-17": "Couche-Tard withdraws",
    "2026-04-09": "Results; US listing postponed",
}
WINDOW = (-1, 2)

px = pd.concat({t: pd.read_csv(RAW / "prices" / f"{t}.csv", index_col=0, parse_dates=True)["Adj Close"]
                for t in ["3382_T", "1306_T"]}, axis=1).dropna()
ret = px.pct_change().dropna()
ret.columns = ["stock", "market"]
dates = ret.index

rows = []
for day, label in EVENTS.items():
    t0 = dates.searchsorted(pd.Timestamp(day))
    est = ret.iloc[t0 - 260:t0 - 30]
    fit = sm.OLS(est["stock"], sm.add_constant(est["market"])).fit()
    win = ret.iloc[t0 + WINDOW[0]:t0 + WINDOW[1] + 1]
    abnormal = win["stock"] - fit.predict(sm.add_constant(win["market"], has_constant="add"))
    car = abnormal.sum()
    se = np.sqrt(fit.mse_resid * len(win))
    cap_before = px["3382_T"].iloc[t0 - 2]
    rows.append({"date": dates[t0].date(), "event": label, "car_pct": car * 100, "low_95": (car - 1.96 * se) * 100,
                 "high_95": (car + 1.96 * se) * 100, "t_stat": car / se, "beta": fit.params["market"],
                 "raw_return_pct": ((1 + win["stock"]).prod() - 1) * 100,
                 "market_return_pct": ((1 + win["market"]).prod() - 1) * 100,
                 "price_before": cap_before})
res = pd.DataFrame(rows)
res.round(3).to_csv(PROCESSED / "part4_event_study.csv", index=False)
print(f"Cumulative abnormal return, trading days {WINDOW[0]} to +{WINDOW[1]} around each event (%)")
print(res[["date", "event", "car_pct", "low_95", "high_95", "t_stat", "raw_return_pct", "market_return_pct"]]
      .round(1).to_string(index=False))

# Figure: abnormal return per event, with 95% ranges -------------------------------------
fig, ax = plt.subplots(figsize=(9, 4.2))
y = np.arange(len(res))[::-1]
colors = [style.THIRD if v > 0 else style.REST for v in res["car_pct"]]
ax.barh(y, res["car_pct"], color=colors, height=0.55)
ax.errorbar(res["car_pct"], y, xerr=[res["car_pct"] - res["low_95"], res["high_95"] - res["car_pct"]],
            fmt="none", ecolor=style.TEXT, elinewidth=1, capsize=3)
for yi, v in zip(y, res["car_pct"]):
    ax.annotate(f"{v:+.1f}%", (v, yi), xytext=(10 if v > 0 else -10, 9), textcoords="offset points",
                ha="left" if v > 0 else "right", color=style.TEXT, fontsize=9.5)
ax.axvline(0, color=style.TEXT_MUTED, linewidth=0.8)
ax.set_yticks(y, [f"{e}\n({d:%d %b %Y})" for e, d in zip(res["event"], res["date"])], fontsize=9)
ax.set_xlabel("Seven & i's return beyond the Japanese market, day before to two days after (%)")
fig.suptitle("Bid news moved the shares far more than the company's own plan", x=0.01, ha="left",
             fontsize=13, fontweight="bold", color=style.TEXT)
ax.grid(axis="y", visible=False)
ax.grid(axis="x", visible=True)
ax.set_axisbelow(True)
fig.text(0.01, 0.01, "Market model on TOPIX (ETF 1306.T), fitted on trading days -260 to -30; bars: cumulative "
         "abnormal return with 95% range. Source: Yahoo Finance.", color=style.TEXT_MUTED, fontsize=7.5)
plt.tight_layout(rect=(0, 0.04, 1, 1))
plt.savefig(FIGURES / "part4_event_study.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part4_event_study.png'}")

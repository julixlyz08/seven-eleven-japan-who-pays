"""Part 2, step 4: how much shopping has 7-Eleven lost compared with its pre-2020 path?

Real volume = same-store sales at constant prices (customers x real basket).
Model: monthly volume growth (vs. a year earlier) before COVID, Mar 2016 - Feb 2020,
as an ARIMA process with a constant. The forecast runs from Mar 2020 to the latest
month, and is chained into a level so it can be compared with what happened.
Uncertainty: 2,000 simulated paths from the fitted model give a 95% range
(fixed random seed, so reruns give identical results).

The same is done for the rest of the industry, so the two gaps can be compared.
This is a "what if trends had continued" baseline, not a causal estimate: it
cannot separate COVID, inflation and competition from each other.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from statsmodels.tsa.arima.model import ARIMA
from config import PROCESSED, FIGURES
import style

prices = pd.read_csv(PROCESSED / "part2_prices.csv", index_col=0)
prices.index = pd.to_datetime(prices.index)
prices = prices.asfreq("MS")


def real_growth(nominal):
    return ((1 + nominal / 100) / (1 + prices["cvs_price_yoy_pct"] / 100) - 1) * 100


series = {"7-Eleven": real_growth(prices["same_store_sales_yoy_pct"]),
          "Rest of industry": real_growth(prices["rest_sales_yoy_pct"])}

TRAIN = ("2016-03-01", "2020-02-01")
SIMS = 2000
rng = np.random.default_rng(42)  # one generator, so simulations are reproducible


def rolling12(matrix):
    """12-month average down the rows of a (months x paths) array."""
    c = np.cumsum(np.vstack([np.zeros((1, matrix.shape[1])), matrix]), axis=0)
    return (c[12:] - c[:-12]) / 12


results, paths = {}, {}
for name, growth in series.items():
    growth = growth.loc[TRAIN[0]:].dropna()
    train = growth.loc[:TRAIN[1]]
    model = ARIMA(train, order=(1, 0, 0), trend="c").fit()
    n_train, horizon = len(train), len(growth) - len(train)
    sims = model.simulate(nsimulations=horizon, repetitions=SIMS,
                          anchor="end", rng=rng).to_numpy().reshape(horizon, SIMS)

    # Actual level: chain growth from a flat first year, then set Mar 2019 - Feb 2020 = 100
    level = np.ones(len(growth)) * 100.0
    for i in range(12, len(growth)):
        level[i] = level[i - 12] * (1 + growth.iloc[i] / 100)
    level = level / level[(growth.index >= "2019-03-01") & (growth.index <= "2020-02-01")].mean() * 100

    # Simulated levels continue from the last 12 actual months before COVID
    sim_level = np.vstack([np.tile(level[n_train - 12:n_train, None], (1, SIMS)), np.zeros((horizon, SIMS))])
    for i in range(horizon):
        sim_level[12 + i] = sim_level[i] * (1 + sims[i] / 100)
    sim_smooth = rolling12(np.vstack([sim_level[1:12], sim_level[12:]]))  # one row per future month

    actual_smooth = pd.Series(level, index=growth.index).rolling(12).mean()
    future = growth.index[n_train:]
    paths[name] = pd.DataFrame({"actual": actual_smooth}).join(pd.DataFrame({
        "baseline": np.median(sim_smooth, axis=1),
        "low": np.percentile(sim_smooth, 2.5, axis=1),
        "high": np.percentile(sim_smooth, 97.5, axis=1)}, index=future))
    gap = actual_smooth.iloc[-1] / sim_smooth[-1] * 100 - 100
    results[name] = {"pre_2020_trend_pct_per_year": model.params["const"],
                     "actual_vs_mar2019_feb2020_pct": actual_smooth.iloc[-1] - 100,
                     "baseline_vs_mar2019_feb2020_pct": np.median(sim_smooth[-1]) - 100,
                     "gap_pct": np.median(gap), "gap_low": np.percentile(gap, 2.5),
                     "gap_high": np.percentile(gap, 97.5)}
    print(f"{name}: fitted on {n_train} months; AR(1) = {model.params['ar.L1']:.2f}, "
          f"trend {model.params['const']:+.2f}% a year")

results = pd.DataFrame(results).T
print("\nReal same-store volume, latest 12 months, vs. Mar 2019 - Feb 2020 (%)")
print(results.round(1).to_string())
results.round(2).to_csv(PROCESSED / "part2_forecast.csv")

# Figure: 7-Eleven actual vs. baseline, rest of industry for reference ------------------
fig, ax = plt.subplots(figsize=(9, 5))
ax.axhline(100, color=style.TEXT_MUTED, linewidth=0.8)
s = paths["7-Eleven"].dropna(subset=["actual"])
r = paths["Rest of industry"].dropna(subset=["actual"])
ax.fill_between(s.index, s["low"], s["high"], color=style.SEVEN_ELEVEN, alpha=0.12, linewidth=0)
ax.plot(s.index, s["baseline"], color=style.SEVEN_ELEVEN, linestyle="--", linewidth=1.5,
        label="7-Eleven if pre-2020 trend had continued")
ax.plot(s.index, s["actual"], color=style.SEVEN_ELEVEN, label="7-Eleven, actual")
ax.plot(r.index, r["actual"], color=style.REST, label="Rest of industry, actual")
last = s.index[-1]
for y, text, nudge in [(s["baseline"].iloc[-1], "Pre-2020 trend", 0), (s["actual"].iloc[-1], "7-Eleven", 6),
                       (r["actual"].iloc[-1], "Rest of industry", -6)]:
    ax.annotate(f"{text} {y:.0f}", (last, y), xytext=(8, nudge), textcoords="offset points",
                va="center", color=style.TEXT, fontsize=10)
ax.set_title("7-Eleven held up better in 2020, then kept sliding until it met its rivals")
ax.set_ylabel("Same-store sales at constant prices\n(Mar 2019 - Feb 2020 = 100, 12-month average)")
ax.axvline(pd.Timestamp("2020-03-01"), color=style.GRID, linewidth=1)
ax.annotate("COVID", (pd.Timestamp("2020-03-01"), ax.get_ylim()[1]), xytext=(4, -12),
            textcoords="offset points", color=style.TEXT_MUTED, fontsize=9)
ax.set_xticks(pd.to_datetime([f"{y}-01-01" for y in range(2018, last.year + 1)]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_xlim(s.index[0], last + pd.Timedelta(days=520))
ax.spines["bottom"].set_bounds(mdates.date2num(s.index[0]), mdates.date2num(last))
ax.legend(loc="lower left")
fig.text(0.01, 0.01, "Baseline: ARIMA on monthly real growth, Mar 2016 - Feb 2020; shaded 95% range from "
         "2,000 simulations.\nDeflated with the convenience-store price index (step 2). "
         "Sources: Seven & i, JFA, Statistics Bureau of Japan.",
         color=style.TEXT_MUTED, fontsize=8)
plt.tight_layout(rect=(0, 0.05, 1, 1))
plt.savefig(FIGURES / "part2_volume_vs_trend.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part2_volume_vs_trend.png'}")

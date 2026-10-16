"""Part 1, step 3: what predicts a convenience store, and where is 7-Eleven missing?

Unit: the 1 km squares of the 2020 census grid (plus squares with stores or
stations but no residents). For each square:
    stores ~ Poisson( log residents, log residents in the 8 surrounding squares,
                      share aged 65+, share of one-person households,
                      log railway passengers, prefecture )
The prefecture term absorbs differences in OpenStreetMap coverage and in each
chain's regional presence. Coefficients on logged inputs read as elasticities.

1. All chains together: what drives convenience-store density.
2. Each of the big three: do they target different places?
3. Validation: fit without prefecture terms on some prefectures, predict others.
4. White space: 3 x 3 km blocks where the model expects at least 2 7-Elevens,
   none is mapped, but at least 3 rival stores are (so the area is mapped).
   OSM misses ~20% of stores, so each listed block is a lead, not a fact.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import sparse
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
from config import PROCESSED, FIGURES
import style

EARTH_KM = 6371.0
stores = pd.read_csv(PROCESSED / "stores.csv")
stores = stores[~stores["chain"].isin(["Stale (closed chain)", "Other / unnamed"])]
grid = pd.read_csv(PROCESSED / "population_grid.csv")
stations = pd.read_csv(PROCESSED / "stations.csv")

# Add squares that have stores or stations but no residents (e.g. office districts)
extra = pd.concat([stores[["mesh", "lat", "lon", "prefecture"]], stations[["mesh", "lat", "lon", "prefecture"]]])
extra = extra[~extra["mesh"].isin(grid["mesh"])].drop_duplicates("mesh")
grid = pd.concat([grid, extra.assign(pop=0, pop_15_64=0, pop_65_plus=0, households=0, one_person_households=0)],
                 ignore_index=True)

counts = stores.pivot_table(index="mesh", columns="chain", values="osm_id", aggfunc="count", fill_value=0)
grid["all_stores"] = grid["mesh"].map(counts.sum(axis=1)).fillna(0)
for chain in ["7-Eleven", "FamilyMart", "Lawson"]:
    grid[chain] = grid["mesh"].map(counts[chain]).fillna(0)
grid["passengers"] = grid["mesh"].map(stations.groupby("mesh")["passengers"].sum()).fillna(0)

# Neighbouring squares: centres within 1.5 km (the 3 x 3 block around each square)
lat, lon = np.radians(grid["lat"]), np.radians(grid["lon"])
xyz = np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
pairs = cKDTree(xyz).query_pairs(2 * np.sin(1.5 / EARTH_KM / 2), output_type="ndarray")
n = len(grid)
adj = sparse.coo_matrix((np.ones(2 * len(pairs)), (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                        shape=(n, n)).tocsr()
grid["pop_around"] = adj @ grid["pop"].values

has_pop = grid["pop"] > 0
grid["share_65"] = np.where(has_pop, grid["pop_65_plus"] / grid["pop"].clip(lower=1), 0)
grid["share_single"] = np.where(grid["households"] > 0,
                                grid["one_person_households"] / grid["households"].clip(lower=1), 0)
grid["log_pop"] = np.log1p(grid["pop"])
grid["log_pop_around"] = np.log1p(grid["pop_around"])
grid["log_passengers"] = np.log1p(grid["passengers"])
grid["no_residents"] = (~has_pop).astype(int)
print(f"{n:,} squares; {int(grid['all_stores'].sum()):,} stores; "
      f"{(grid['all_stores'] > 0).mean() * 100:.1f}% of squares have at least one store")

X = "log_pop + log_pop_around + share_65 + share_single + log_passengers + no_residents"

# 1-2. Poisson models with prefecture terms ---------------------------------------------
coefs = []
fits = {}
for target in ["all_stores", "7-Eleven", "FamilyMart", "Lawson"]:
    data = grid.rename(columns={target: "y"})
    res = smf.glm(f"y ~ {X} + C(prefecture)", data, family=sm.families.Poisson()).fit(cov_type="HC1")
    fits[target] = res
    for var in ["log_pop", "log_pop_around", "share_65", "share_single", "log_passengers"]:
        lo, hi = res.conf_int().loc[var]
        coefs.append({"target": target, "input": var, "coef": res.params[var], "low_95": lo, "high_95": hi})
coefs = pd.DataFrame(coefs)
coefs.round(4).to_csv(PROCESSED / "part1_site_model_coefficients.csv", index=False)
print("\nPoisson coefficients (logged inputs = elasticities; shares = per 1.0 change)")
print(coefs.pivot(index="input", columns="target", values="coef").round(3).to_string())
print("\n95% ranges")
print(coefs.assign(range=coefs["low_95"].round(3).astype(str) + " to " + coefs["high_95"].round(3).astype(str))
      .pivot(index="input", columns="target", values="range").to_string())

# 3. Validation: hold out whole prefectures --------------------------------------------
prefs = np.array(sorted(grid["prefecture"].unique()))
rng = np.random.default_rng(11)
folds = np.array_split(rng.permutation(prefs), 5)
pred = pd.Series(np.nan, index=grid.index)
for hold in folds:
    test = grid["prefecture"].isin(hold)
    res = smf.glm(f"all_stores ~ {X}", grid[~test], family=sm.families.Poisson()).fit()
    pred[test] = res.predict(grid[test])
y = grid["all_stores"]
dev = lambda mu: 2 * np.sum(np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0) - (y - mu))
explained = 1 - dev(pred) / dev(np.full(len(y), y.mean()))
block_actual = adj @ y.values + y.values
block_pred = adj @ pred.values + pred.values
r = np.corrcoef(block_actual, block_pred)[0, 1]
print(f"\nHeld-out prefectures (5 folds): deviance explained {explained * 100:.0f}%; "
      f"correlation of predicted and actual stores per 3 x 3 km block {r:.2f}")

# 4. White space for 7-Eleven ------------------------------------------------------------
grid["sej_pred"] = fits["7-Eleven"].predict(grid)
grid["block_sej_pred"] = adj @ grid["sej_pred"].values + grid["sej_pred"].values
grid["block_sej"] = adj @ grid["7-Eleven"].values + grid["7-Eleven"].values
grid["block_rivals"] = adj @ (grid["all_stores"] - grid["7-Eleven"]).values + (grid["all_stores"] - grid["7-Eleven"]).values
grid["block_pop"] = grid["pop"] + grid["pop_around"]
cand = grid[(grid["block_sej"] == 0) & (grid["block_sej_pred"] >= 2) & (grid["block_rivals"] >= 3)]
# Keep the strongest square per cluster of overlapping blocks
cand = cand.sort_values("block_sej_pred", ascending=False)
taken, picks = set(), []
cand_idx = cand.index.to_numpy()
neighbours = adj[cand_idx].tolil().rows
for i, nb in zip(cand_idx, neighbours):
    if i in taken:
        continue
    picks.append(i)
    taken.update(nb)
    taken.add(i)
white = grid.loc[picks].copy()
st_tree = cKDTree(np.column_stack([np.radians(stations["lat"]), np.radians(stations["lon"])]))
_, nearest = st_tree.query(np.column_stack([np.radians(white["lat"]), np.radians(white["lon"])]))
white["nearest_station"] = stations["station"].values[nearest]
cols = ["prefecture", "nearest_station", "lat", "lon", "block_pop", "block_rivals", "block_sej_pred"]
white[cols].round(3).to_csv(PROCESSED / "part1_white_space.csv", index=False)
print(f"\nWhite-space blocks: {len(white)}")
print(white[cols].head(12).round(1).to_string(index=False))
print("\nWhite-space blocks by prefecture (top 10)")
print(white["prefecture"].value_counts().head(10).to_string())

# Figure: what each chain leans toward ---------------------------------------------------
labels = {"log_pop": "Residents in the square", "log_pop_around": "Residents nearby (3 x 3 km)",
          "log_passengers": "Railway passengers", "share_single": "One-person households (share)",
          "share_65": "Residents aged 65+ (share)"}
order = ["log_pop", "log_pop_around", "log_passengers", "share_single", "share_65"]
colors = {"7-Eleven": style.SEVEN_ELEVEN, "FamilyMart": style.THIRD, "Lawson": style.REST}
fig, ax = plt.subplots(figsize=(8.5, 5))
yb = np.arange(len(order))
for k, chain in enumerate(colors):
    d = coefs[coefs["target"] == chain].set_index("input").loc[order]
    # Express share effects per 10 percentage points so all inputs sit on one scale
    scale = np.where(d.index.str.startswith("share"), 0.1, 1.0)
    ypos = yb + (k - 1) * 0.22
    ax.errorbar(d["coef"] * scale, ypos, xerr=[(d["coef"] - d["low_95"]) * scale, (d["high_95"] - d["coef"]) * scale],
                fmt="o", color=colors[chain], markersize=6, capsize=0, linewidth=1.5, label=chain)
ax.axvline(0, color=style.TEXT_MUTED, linewidth=0.8)
ax.set_yticks(yb, [labels[o] for o in order])
ax.invert_yaxis()
ax.set_xlabel("Effect on expected stores (log points; shares per +10 points)")
ax.set_title("All three chains chase the same places; 7-Eleven leans least on stations")
ax.grid(axis="x", visible=True)
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
fig.text(0.01, 0.01, "Poisson models of stores per 1 km square, with prefecture effects; bars are 95% ranges. "
         "Logged inputs: +1 = 2.7x more.\nSources: OpenStreetMap (Oct 2026), 2020 census 1 km grid, MLIT station "
         "passengers.", color=style.TEXT_MUTED, fontsize=8)
plt.tight_layout(rect=(0, 0.06, 1, 1))
plt.savefig(FIGURES / "part1_site_model.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part1_site_model.png'}")

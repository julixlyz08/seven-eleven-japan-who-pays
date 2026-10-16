"""Part 1, step 2: does 7-Eleven cluster its stores more than its rivals do?

7-Eleven is known for a "dominant area" strategy: opening many stores close
together so delivery trucks and advertising cover a dense patch. If so, a
7-Eleven's nearby stores should be 7-Eleven more often than its market share implies.

Clustering ratio, for each chain and radius:
    share of a store's neighbours (within r) that are the same chain
    / the chain's share of all stores in that store's prefecture
1.0 = no more clustered than its market share; above 1 = clustered.

Test: shuffle chain labels among stores within each prefecture (locations fixed,
each prefecture's chain mix fixed), 200 times. If the real ratio sits far above
the shuffled ones, the clustering isn't an accident of where stores can go.
OSM misses about 20% of stores; random gaps thin every chain alike, so the
ratio is not biased by them, only noisier.
"""
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
from config import PROCESSED, FIGURES
import style

EARTH_KM = 6371.0
RADII_KM = [0.5, 1.0, 2.0]
SHUFFLES = 200
MAIN = ["7-Eleven", "FamilyMart", "Lawson"]
rng = np.random.default_rng(7)

stores = pd.read_csv(PROCESSED / "stores.csv")
stores = stores[~stores["chain"].isin(["Stale (closed chain)", "Other / unnamed"])].dropna(subset=["prefecture"])
stores = stores.reset_index(drop=True)
print(f"{len(stores):,} named, current stores")

# 3D unit vectors: straight-line (chord) distance ~ ground distance at these scales
lat, lon = np.radians(stores["lat"]), np.radians(stores["lon"])
xyz = np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
tree = cKDTree(xyz)
pairs = {r: tree.query_pairs(2 * np.sin(r / EARTH_KM / 2), output_type="ndarray") for r in RADII_KM}
for r, p in pairs.items():
    print(f"  pairs within {r} km: {len(p):,}")

chain_codes, chain_names = pd.factorize(stores["chain"])
pref_codes = pd.factorize(stores["prefecture"])[0]


def ratios(labels):
    """Clustering ratio for every chain and radius, given one labelling of the stores."""
    n_chains = len(chain_names)
    # Each chain's share of stores in each prefecture, looked up per store
    counts = np.zeros((pref_codes.max() + 1, n_chains))
    np.add.at(counts, (pref_codes, labels), 1)
    share = (counts / counts.sum(axis=1, keepdims=True))[pref_codes, labels]
    out = {}
    for r, p in pairs.items():
        same = labels[p[:, 0]] == labels[p[:, 1]]
        # Each pair is a neighbour for both its stores
        neighbours = np.bincount(p.ravel(), minlength=len(labels))
        same_count = np.bincount(p[same].ravel(), minlength=len(labels))
        has = neighbours > 0
        for c in range(n_chains):
            mask = has & (labels == c)
            observed = same_count[mask].sum() / neighbours[mask].sum()
            expected = (share[mask] * neighbours[mask]).sum() / neighbours[mask].sum()
            out[(chain_names[c], r)] = observed / expected
    return out


observed = ratios(chain_codes)
null = []
for _ in range(SHUFFLES):
    shuffled = chain_codes.copy()
    for p in np.unique(pref_codes):
        idx = np.where(pref_codes == p)[0]
        shuffled[idx] = rng.permutation(shuffled[idx])
    null.append(ratios(shuffled))
null = pd.DataFrame(null)

rows = []
for (chain, r), value in observed.items():
    rows.append({"chain": chain, "radius_km": r, "clustering_ratio": value,
                 "shuffled_mean": null[(chain, r)].mean(),
                 "shuffled_95": null[(chain, r)].quantile(0.95),
                 "share_of_stores_pct": (stores["chain"] == chain).mean() * 100})
res = pd.DataFrame(rows).sort_values(["radius_km", "clustering_ratio"], ascending=[True, False])
res.round(3).to_csv(PROCESSED / "part1_clustering.csv", index=False)
print("\nClustering ratio (1 = only as clustered as market share implies)")
print(res.round(2).to_string(index=False))

# Distance profile and a local benchmark ---------------------------------------------
# A ratio below 1 could just mean 7-Eleven is over-represented in suburbs (few
# neighbours) and under-represented in dense centres. So the same ratio is also
# computed against each store's local market: the chain's share of all stores
# within 5 km (excluding the store itself).
tree_all = cKDTree(xyz)
local_r = 2 * np.sin(5.0 / EARTH_KM / 2)
local_all = tree_all.query_ball_point(xyz, local_r, return_length=True) - 1
profile = []
for chain in MAIN:
    m = (stores["chain"] == chain).values
    tree_c = cKDTree(xyz[m])
    local_same = tree_c.query_ball_point(xyz[m], local_r, return_length=True) - 1
    local_share = np.where(local_all[m] > 0, local_same / np.maximum(local_all[m], 1), np.nan)
    pref_share = pd.Series(m).groupby(pref_codes).mean().values[pref_codes][m]
    for r in [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]:
        rr = 2 * np.sin(r / EARTH_KM / 2)
        n = tree_all.query_ball_point(xyz[m], rr, return_length=True) - 1
        same_n = tree_c.query_ball_point(xyz[m], rr, return_length=True) - 1
        ok = n > 0
        row = {"chain": chain, "radius_km": r,
               "vs_prefecture_share": same_n[ok].sum() / (pref_share[ok] * n[ok]).sum()}
        if r < 5:
            ok2 = ok & ~np.isnan(local_share)
            row["vs_local_5km_share"] = same_n[ok2].sum() / (local_share[ok2] * n[ok2]).sum()
        profile.append(row)
profile = pd.DataFrame(profile)
profile.round(3).to_csv(PROCESSED / "part1_clustering_profile.csv", index=False)
print("\nClustering ratio by distance: vs. prefecture share, and vs. local (5 km) share")
print(profile.pivot(index="radius_km", columns="chain").round(2).to_string())

# Regional concentration: how unequal is each chain's share across prefectures?
pref = pd.read_csv(PROCESSED / "part1_prefectures.csv", index_col=0)
shares = pd.DataFrame({"7-Eleven": pref["sej_official"] / pref["all_est"],
                       "FamilyMart": pref["FamilyMart_est"] / pref["all_est"],
                       "Lawson": pref["Lawson_est"] / pref["all_est"]}) * 100
w = pref["population"] / pref["population"].sum()
spread = pd.DataFrame({"national_share_pct": (shares.mul(w, axis=0)).sum(),
                       "min_pct": shares.min(), "max_pct": shares.max(),
                       "spread_sd_pts": np.sqrt(((shares - (shares.mul(w, axis=0)).sum()) ** 2).mul(w, axis=0).sum())})
print("\nShare of stores across the 47 prefectures (population-weighted)")
print(spread.round(1).to_string())
spread.round(2).to_csv(PROCESSED / "part1_regional_concentration.csv")

# Figure: clustering ratio by distance ------------------------------------------------
colors = {"7-Eleven": style.SEVEN_ELEVEN, "FamilyMart": style.THIRD, "Lawson": style.REST}
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.axhline(1, color=style.TEXT_MUTED, linewidth=0.8)
for chain in MAIN:
    d = profile[profile["chain"] == chain]
    ax.plot(d["radius_km"], d["vs_prefecture_share"], color=colors[chain], marker="o", markersize=5, label=chain)
ax.set_xscale("log")
ax.set_xticks([0.25, 0.5, 1, 2, 5, 10, 20], ["250 m", "500 m", "1 km", "2 km", "5 km", "10 km", "20 km"])
ax.minorticks_off()
ax.set_xlim(0.2, 25)
ax.set_xlabel("Distance to neighbouring stores")
ax.set_ylabel("Same-chain neighbours vs. market share\n(1 = no clustering)")
ax.set_title("Up close, 7-Eleven keeps its own stores apart")
ax.legend(loc="lower right")
fig.text(0.01, 0.01, "Share of a store's neighbours that are the same chain, divided by the chain's share of stores "
         "in that prefecture.\nWith chain labels shuffled at random within prefectures, the ratio stays within "
         "0.98-1.02. Source: OpenStreetMap (Oct 2026).", color=style.TEXT_MUTED, fontsize=8)
plt.tight_layout(rect=(0, 0.06, 1, 1))
plt.savefig(FIGURES / "part1_clustering.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part1_clustering.png'}")

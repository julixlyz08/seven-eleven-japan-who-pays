"""Part 1, step 1: how complete is OpenStreetMap, and how dense is 7-Eleven by prefecture?

Coverage = OSM 7-Eleven stores / 7-Eleven's official count (end of Sep 2026).
Rivals have no official prefecture counts here, so their counts are estimated as
OSM count / 7-Eleven's coverage in the same prefecture (mappers tend to map
every store on a street, whatever the chain), shrunk toward the national rate
where 7-Eleven has few stores. The national totals of these
estimates are checked against the chains' official store counts.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import PROCESSED, MANUAL, FIGURES
import style

stores = pd.read_csv(PROCESSED / "stores.csv")
grid = pd.read_csv(PROCESSED / "population_grid.csv")
official = pd.read_csv(MANUAL / "sej_stores_by_prefecture_2026-09.csv").set_index("prefecture")["stores"]
chains_official = pd.read_csv(PROCESSED / "chain_store_counts.csv")
chains_official = chains_official[chains_official["fiscal_year"] == 2025].set_index("chain")["stores"]

osm = stores.pivot_table(index="prefecture", columns="chain", values="osm_id", aggfunc="count", fill_value=0)
pop = grid.groupby("prefecture")["pop"].sum()
df = pd.DataFrame({"population": pop, "sej_official": official, "sej_osm": osm["7-Eleven"]})
df["coverage"] = df["sej_osm"] / df["sej_official"]
# Where 7-Eleven has few stores (or arrived recently and is less mapped), its coverage
# ratio is a noisy guide for rivals. Shrink it toward the national rate, more strongly
# the fewer stores it rests on (equivalent to adding K stores at the national rate).
K = 200
national = df["sej_osm"].sum() / df["sej_official"].sum()
df["coverage_used"] = (df["sej_osm"] + K * national) / (df["sej_official"] + K)
for chain in ["FamilyMart", "Lawson"]:
    df[f"{chain}_est"] = osm[chain] / df["coverage_used"]
# Named chains only: unnamed shops are mostly independents the official totals leave out
current = [c for c in osm.columns if c not in ("Stale (closed chain)", "Other / unnamed")]
df["all_est"] = osm[current].drop(columns="7-Eleven").sum(axis=1) / df["coverage_used"] + df["sej_official"]
df["sej_share_pct"] = df["sej_official"] / df["all_est"] * 100
df["sej_per_10k"] = df["sej_official"] / df["population"] * 1e4
df["all_per_10k"] = df["all_est"] / df["population"] * 1e4
df["stale_pct"] = osm["Stale (closed chain)"] / osm.sum(axis=1) * 100
df = df.sort_values("sej_per_10k", ascending=False)
df.round(3).to_csv(PROCESSED / "part1_prefectures.csv")

print(f"OSM coverage of 7-Eleven: {df['sej_osm'].sum() / df['sej_official'].sum() * 100:.0f}% nationally; "
      f"by prefecture median {df['coverage'].median() * 100:.0f}%, range "
      f"{df['coverage'].min() * 100:.0f}% ({df['coverage'].idxmin()}) to {df['coverage'].max() * 100:.0f}% "
      f"({df['coverage'].idxmax()})")
print("\nCheck: estimated rival totals vs. official store counts (FY2025)")
for chain in ["FamilyMart", "Lawson"]:
    est = df[f"{chain}_est"].sum()
    print(f"  {chain}: estimated {est:,.0f}, official {chains_official[chain]:,} "
          f"({(est / chains_official[chain] - 1) * 100:+.1f}%)")
print(f"  All chains: estimated {df['all_est'].sum():,.0f}, JFA/official nationwide {chains_official['Nationwide']:,}")

cols = ["population", "sej_official", "coverage", "sej_per_10k", "all_per_10k", "sej_share_pct"]
print("\nTop and bottom prefectures by 7-Eleven stores per 10,000 residents")
print(pd.concat([df[cols].head(6), df[cols].tail(6)]).round(2).to_string())
r = np.corrcoef(np.log(df["population"] / 1e6), df["sej_share_pct"])[0, 1]
print(f"\n7-Eleven's share of stores: national {df['sej_official'].sum() / df['all_est'].sum() * 100:.0f}%, "
      f"highest {df['sej_share_pct'].max():.0f}% ({df['sej_share_pct'].idxmax()}), lowest "
      f"{df['sej_share_pct'].min():.0f}% ({df['sej_share_pct'].idxmin()})")

# Figure: 7-Eleven vs. all convenience stores per 10,000 residents, by prefecture ------
d = df.sort_values("all_per_10k")
fig, ax = plt.subplots(figsize=(8, 10))
y = np.arange(len(d))
ax.hlines(y, d["sej_per_10k"], d["all_per_10k"], color=style.GRID, linewidth=2)
ax.scatter(d["all_per_10k"], y, color=style.REST, s=36, label="All convenience stores (estimated)", zorder=3)
ax.scatter(d["sej_per_10k"], y, color=style.SEVEN_ELEVEN, s=36, label="7-Eleven (official)", zorder=3)
english = {"北海道": "Hokkaido", "青森": "Aomori", "岩手": "Iwate", "宮城": "Miyagi", "秋田": "Akita",
           "山形": "Yamagata", "福島": "Fukushima", "茨城": "Ibaraki", "栃木": "Tochigi", "群馬": "Gunma",
           "埼玉": "Saitama", "千葉": "Chiba", "東京": "Tokyo", "神奈川": "Kanagawa", "新潟": "Niigata",
           "富山": "Toyama", "石川": "Ishikawa", "福井": "Fukui", "山梨": "Yamanashi", "長野": "Nagano",
           "岐阜": "Gifu", "静岡": "Shizuoka", "愛知": "Aichi", "三重": "Mie", "滋賀": "Shiga", "京都": "Kyoto",
           "大阪": "Osaka", "兵庫": "Hyogo", "奈良": "Nara", "和歌山": "Wakayama", "鳥取": "Tottori",
           "島根": "Shimane", "岡山": "Okayama", "広島": "Hiroshima", "山口": "Yamaguchi", "徳島": "Tokushima",
           "香川": "Kagawa", "愛媛": "Ehime", "高知": "Kochi", "福岡": "Fukuoka", "佐賀": "Saga",
           "長崎": "Nagasaki", "熊本": "Kumamoto", "大分": "Oita", "宮崎": "Miyazaki", "鹿児島": "Kagoshima",
           "沖縄": "Okinawa"}
ax.set_yticks(y, [f"{english[p]}  ({s:.0f}%)" for p, s in zip(d.index, d["sej_share_pct"])], fontsize=8.5)
ax.set_xlabel("Stores per 10,000 residents")
ax.set_title("7-Eleven's share of stores varies from region to region")
ax.grid(axis="x", visible=True)
ax.grid(axis="y", visible=False)
ax.set_ylim(-1, len(d))
ax.legend(loc="lower right")
fig.text(0.01, 0.01, "In brackets: 7-Eleven's estimated share of convenience stores. 7-Eleven: official counts, Sep 2026.\n"
         "Other chains: OpenStreetMap counts scaled by 7-Eleven's OSM coverage in the same prefecture. "
         "Population: 2020 census.", color=style.TEXT_MUTED, fontsize=8)
plt.tight_layout(rect=(0, 0.04, 1, 1))
plt.savefig(FIGURES / "part1_density_by_prefecture.png", dpi=200)
plt.close()
print(f"\nSaved {FIGURES / 'part1_density_by_prefecture.png'}")

# 7-Eleven Japan: Who Pays?

**7-Eleven is often called the best-run convenience-store chain in the world. Where does its edge come from, who pays for it, and what is it worth?**

The project uses only public data: Seven & i's own filings, industry and government statistics, and OpenStreetMap. Each part uses a different method.

| Part | Question | Main skills | Status |
|---|---|---|---|
| 1. Where the stores are | Does 7-Eleven's habit of clustering stores show in the map, and where are stores "missing"? | Spatial statistics, permutation test, site-selection model | **Done** |
| 2. Where the customers went | Is 7-Eleven still growing once inflation is removed, and are drugstores taking its shoppers? | Time-series decomposition, panel regression, forecasting | **Done** |
| 3. Who pays | When wages and prices rise, does head office or the store owner absorb it? | Franchise unit economics, Monte Carlo | To do |
| 4. What it's worth | What is the market paying for the Japanese stores alone? | Sum-of-the-parts valuation | To do |

## Key findings so far

**Part 1: where the stores are**

- **7-Eleven's famous clustering doesn't show up at street level. If anything, the opposite.** Within 250 m of a 7-Eleven, other convenience stores are 7-Elevens only 0.75 times as often as its market share would predict; FamilyMart's ratio is 1.09. When chain labels are shuffled at random, 95% of results fall between 0.97 and 1.03. 7-Eleven keeps its own stores apart, and leaves the closest sites to rivals.
- **Its dominance is regional, not local.** 7-Eleven has 53-60% of convenience stores in its strongholds (Saga, Yamaguchi, Kumamoto, Tochigi, Gunma) and about 20% in the last prefectures it entered (Aomori, Kochi and Tottori in 2015, Okinawa in 2019).
- **All three big chains go to the same kind of place:** more residents, more one-person households, fewer elderly. A 10-point higher share of residents aged 65+ means about 9% fewer stores. 7-Eleven depends least on railway stations.
- **The model finds 153 "white-space" areas** where it expects at least two 7-Elevens, none is mapped, and rivals are trading. They are mostly in Aichi and Hyogo, where 7-Eleven's share is below average.

**Part 2: where the customers went**

- **Sales growth since 2019 is all price.** Same-store sales are up 7%, but convenience-store prices are up 28%, more than twice the 13% rise in overall consumer prices. In real terms, 7-Eleven's stores sell about 16% less than before COVID: 11% fewer customers, each buying 6% less.
- **7-Eleven has lost its edge over its rivals.** Before 2020 it beat the rest of the industry on customer growth in 70% of months; since 2022, in 12%. It held up better in the 2020-21 slump, but rivals have since won back more customers.
- **Against its own pre-2020 path, 7-Eleven has lost about twice as much as its rivals.** Before COVID its real sales were almost flat (-0.4% a year) while rivals' were shrinking (-1.6% a year). Today both are about 16-17% below their 2019 level, so 7-Eleven is 14% below its own trend, against 8% for rivals.
- **Drugstores are the competitor people overlook.** Their food sales have grown 2.4 times since 2015, from about an eighth to a quarter of convenience-store sales. Regions where drugstores expanded fastest (Tohoku, Chubu) had the weakest convenience-store growth, and this holds when comparing regions in the same month.

---

## Part 1: Where the stores are

### Data

Store locations come from OpenStreetMap (48,973 convenience stores, October 2026). Each store is classified by chain from its name and brand tags; 353 entries belong to chains that no longer exist (Circle K Sunkus and others, converted to FamilyMart or Lawson by 2019) and are dropped as out of date. Stores, the 2020 census population on a 1 km grid (176,605 squares, 126.1 million people) and railway stations with daily passengers are placed in prefectures using the official boundary map.

**How complete is OpenStreetMap?** 7-Eleven publishes its store count by prefecture, which gives a direct test: OSM has 81% of 7-Eleven stores nationally, from 45% (Shimane) to 99% (Wakayama). Rival counts by prefecture are estimated by scaling their OSM counts by 7-Eleven's coverage in the same prefecture (pulled toward the national rate where 7-Eleven has few stores, since a new entrant is less well mapped). The estimates add up to within 3% of FamilyMart's and Lawson's official national totals.

![Stores per 10,000 residents by prefecture](reports/figures/part1_density_by_prefecture.png)

- **7-Eleven has 38% of Japan's convenience stores**, but from 18% in Aomori to 60% in Saga. Its strongholds are northern Kanto (Tochigi, Gunma, Fukushima) and western Japan (Saga, Yamaguchi, Kumamoto); it is weakest in the last prefectures it entered: Aomori, Kochi and Tottori (2015) and Okinawa (2019).
- **Store density varies less than chain share.** Most prefectures have 4-5 convenience stores per 10,000 residents, whoever runs them.

### Does 7-Eleven cluster its stores?

7-Eleven is known for a "dominant area" strategy: opening many stores close together so delivery routes and advertising cover a dense patch. The test: for each store, what share of its neighbours within a given distance belong to the same chain, compared with that chain's share of stores in the prefecture? 1.0 means no more clustered than market share implies.

![Clustering ratio by distance](reports/figures/part1_clustering.png)

| Same-chain neighbours vs. market share | 250 m | 500 m | 1 km | 2 km | 20 km |
|---|---|---|---|---|---|
| 7-Eleven | **0.75** | **0.83** | 0.92 | 0.96 | 0.99 |
| FamilyMart | 1.09 | 1.07 | 1.06 | 1.05 | 1.02 |
| Lawson | 0.95 | 0.97 | 0.99 | 1.01 | 1.00 |
| *Random labels (200 shuffles within prefectures), 95% range* | | *0.97-1.03* | *0.98-1.02* | *0.98-1.02* | |

- **7-Eleven avoids itself at short range.** A 7-Eleven's nearest neighbours are rivals more often than its market share predicts. This isn't an artefact of 7-Eleven being stronger in suburbs: measured against its share of stores within 5 km of each store, the 250 m ratio is still 0.77.
- **Lawson is within the random range** from 500 m to 2 km (0.97-1.01): no clustering either way.
- **FamilyMart is the one that clusters,** probably a legacy of its mergers: Circle K Sunkus and am/pm stores were converted where those chains had dense networks.
- **So "dominance" works at the scale of a region, not a street.** A plausible reading is that 7-Eleven spaces stores to limit cannibalisation between franchise owners, while still saturating whole regions (see the shares above). The data can't show intent.

### What predicts a convenience store, and where is 7-Eleven missing?

A Poisson model predicts the number of stores in each 1 km square from: residents in the square, residents in the 8 squares around it, share aged 65+, share of one-person households, railway passengers, and a prefecture effect (which also absorbs differences in map coverage). It is fitted for all chains together and for each of the big three.

![What each chain's stores follow](reports/figures/part1_site_model.png)

| Effect on expected stores | All chains | 7-Eleven | FamilyMart | Lawson |
|---|---|---|---|---|
| 2.7x more residents in the square | +0.69 log points | +0.72 | +0.67 | +0.65 |
| 2.7x more residents nearby | +0.25 | +0.26 | +0.30 | +0.29 |
| 2.7x more railway passengers | +0.06 | **+0.05** | +0.07 | +0.06 |
| +10 points one-person households | +8% | +8% | +9% | +9% |
| +10 points aged 65+ | -9% | -9% | -9% | -9% |

- **The three chains look for the same things.** The only clear difference: 7-Eleven depends less on railway stations than FamilyMart (95% ranges don't overlap) and slightly more on residents.
- **Ageing is a headwind for everyone.** Areas with more elderly residents have fewer stores, even with the same population. Japan's population is ageing fastest outside the big cities.
- **Validation:** fitted without prefecture effects on four-fifths of prefectures, the model explains 69% of the variation (deviance) in store counts in the held-out fifth. At the level of 3 x 3 km blocks, predicted and actual store counts correlate at 0.42, so it captures broad demand, not exact sites.

**White space.** Blocks of 3 x 3 km where the model expects at least two 7-Elevens, none is mapped, and at least three rival stores are (so the area is mapped and has demand): 153 blocks, most in Aichi (17) and Hyogo (13). The largest are around Ayaragi (Shimonoseki, Yamaguchi), Kuki (Saitama), Kongo and Sayama (south Osaka) and Nomachi (Kanazawa). With OSM missing about a fifth of stores, each is a lead to check on a map, not a confirmed gap. The full list is in [data/processed/part1_white_space.csv](data/processed/part1_white_space.csv).

---

## Part 2: Where the customers went

### 1. 7-Eleven vs. the rest of the industry

Industry figures from the Japan Franchise Association (JFA) include 7-Eleven, which is about 46% of industry sales, so a 7-Eleven-vs-industry comparison understates any gap. 7-Eleven is removed here. Its monthly sales in yen are rebuilt by chaining Seven & i's monthly growth figures and scaling each fiscal year to the yearly total in the Corporate Outline. The chained figures reproduce the published yearly growth to within 0.2 points. The rest of the industry's same-store growth is then (industry - w x 7-Eleven) / (1 - w), where w is 7-Eleven's share of sales a year earlier.

![7-Eleven vs. the rest of the industry, customers](reports/figures/part2_customers_vs_rest.png)

| Same-store customers, 2019 = 100 | 2021 | 2023 | 2024 | 2026 (Jan-Aug) |
|---|---|---|---|---|
| 7-Eleven | 89.2 | 90.6 | 90.6 | 88.8 |
| Rest of industry | 85.9 | 90.2 | 91.8 | 90.6 |

- **Growth vs. a year earlier exaggerates the story.** Rivals lost more customers in 2020-21, so part of their faster growth in 2022-24 is a rebound. A level index (2019 = 100) removes that effect, and the gap remains: 7-Eleven fell less, then was overtaken in 2024.
- 7-Eleven's share of customers isn't published, so its share of sales is used as the weight. Moving that weight 10% up or down barely changes the result (shaded band).

### 2. Price vs. what people actually buy

A convenience-store price index is built from official CPI items (bento, onigiri, sandwiches, fried chicken, bread, dairy, drinks, sweets, alcohol, cigarettes, everyday goods), grouped into 7-Eleven's four product groups and weighted by its sales mix from the previous year. Spend per customer is then split into price and "real basket" (spend at constant prices).

![Sales, customers, prices and real basket, 2019 = 100](reports/figures/part2_price_vs_volume.png)

| Latest 12 months vs. 2019 | Change |
|---|---|
| Same-store sales | +7% |
| Customers | -11% |
| Convenience-store prices | +28% |
| Real basket per customer | -6% |
| *All consumer prices (for reference)* | *+13%* |

- **Customers fell in 2020 and never came back; then the basket started shrinking.** During COVID, fewer visits came with bigger baskets (+6% in 2020-21). From 2023, as prices rose 7% in a year, the real basket fell below its 2019 level and kept falling.
- **Fast food drove the price rise.** Its prices rose 8% in 2023 and 6% in 2025 (onigiri +46% since 2019).
- The split is not sensitive to the main assumption, cigarettes' share of non-food: using 50% or 100% instead of 75% moves the real basket by at most 1 point a year.

### 3. Are drugstores taking convenience-store shoppers?

![Food sales at drugstores, supermarkets and convenience stores](reports/figures/part2_drugstore_food.png)

- **Nationally:** drugstore food sales are 2.4 times their 2015 level, against 1.3 times for supermarket food and 1.2 times for convenience-store sales.
- **Region by month (8 regions, 116 months):** where drugstore numbers grew 1 point faster than usual, convenience-store sales grew 0.06 points slower (95% range -0.11 to -0.004). Month effects remove anything national (COVID, inflation, tax), and region effects remove fixed differences. Standard errors allow for correlation across regions and over time.
  - The effect is small month to month and weakens without 2020-21 (-0.07, p = 0.09).
  - Using drugstore *sales* instead of store numbers gives a positive, non-significant link. That is expected if drugstores and convenience stores both do well where local demand is strong, which is why store openings are the better measure.
  - Drugstores choose where to open, probably where demand is growing. That would push the estimate toward zero, so the negative effect is, if anything, understated.
- **Over ten years, by region:**

| Region | Drugstores, 2015 → now | Convenience-store sales, 2015 → now | Population 2020-24 |
|---|---|---|---|
| Hokkaido | +27% | +23% | -3.5% |
| Kyushu + Okinawa | +37% | +35% | -2.1% |
| Kanto | +45% | +22% | -0.7% |
| Chugoku | +61% | +20% | -3.5% |
| Shikoku | +62% | +17% | -4.4% |
| Kansai | +63% | +29% | -1.8% |
| Chubu | +80% | +12% | -2.1% |
| Tohoku | +86% | +10% | -4.7% |

  The correlation between the two growth columns is -0.73. Population decline explains part of it, but holding population change fixed, the link remains (-0.26 points per point, p = 0.08). With 8 regions, this is a description, not proof.

### 4. Compared with the pre-2020 path

An ARIMA model is fitted to 7-Eleven's monthly real sales growth from March 2016 to February 2020, then projected forward. 2,000 simulated paths give a 95% range. The same is done for the rest of the industry.

![Real sales vs. the pre-2020 trend](reports/figures/part2_volume_vs_trend.png)

| Real same-store sales, latest 12 months | 7-Eleven | Rest of industry |
|---|---|---|
| Trend before 2020 | -0.4% a year | -1.6% a year |
| vs. Mar 2019 - Feb 2020 | -16.4% | -17.0% |
| vs. its own pre-2020 trend | **-13.9%** (range -17.6 to -10.2) | **-7.6%** (range -9.2 to -5.8) |

- The two ranges don't overlap: 7-Eleven has fallen further from its own path than its rivals have from theirs.
- 7-Eleven's pre-2020 advantage was holding volume steady while the rest of the industry shrank. That advantage is gone.
- This is a "what if trends had continued" baseline. It can't separate COVID, inflation and competition from each other.

---

## Data and method notes

Sources, download scripts and the traps found in the raw files are documented in [data/README.md](data/README.md). Scripts run in order from `src/`: `01*` download, `02*` clean, `03-06` are Part 2's analysis, `07-09` Part 1's.

| Term | Definition |
|---|---|
| Same stores | Stores open in both this month and the same month last year |
| Fiscal year | Seven & i's runs March to February; FY2025 = March 2025 - February 2026 |
| Rest of industry | JFA member chains (FamilyMart, Lawson, Ministop, Daily Yamazaki, Seicomart, Poplar) minus 7-Eleven |
| Real basket | Spend per customer divided by the convenience-store price index |

## Limitations (Part 1)

- **OpenStreetMap is incomplete and partly out of date.** It has about 81% of 7-Eleven's stores, unevenly by prefecture; rivals' coverage is assumed similar within a prefecture (checked only against national totals). Random gaps make clustering estimates noisier but not biased; gaps concentrated in particular areas could bias the site model and create false "white space".
- **The census grid is from 2020**; stores are from 2026.
- **Station passengers are by operator**, so a station served by several companies counts each operator's passengers.
- **Simplified prefecture boundaries** (Global Map Japan) put 74 seaside stores just offshore; they are given the nearest prefecture.
- **The site model describes where stores are, not where they would be profitable.** Rival presence is not an input, so "white space" means demand without a 7-Eleven, which could also mean a site 7-Eleven tried and left.

## Limitations (Part 2)

- **7-Eleven's monthly figures are growth rates only.** Its monthly yen sales are rebuilt and scaled to yearly totals; the yearly totals use the pre-2022 accounting basis ("gross total store sales") throughout.
- **Customer weights are not published.** Rest-of-industry customer growth assumes 7-Eleven's share of customers equals its share of sales; a ±10% change moves results little.
- **Chained indexes drift.** Same-store sets change every year, so a long chain of same-store growth is approximate.
- **The price index is national CPI, not 7-Eleven's shelf prices.** 7-Eleven may have raised prices faster or slower than the average. CPI includes consumption tax; store sales are reported before tax (affects October 2019).
- **JFA membership changes over time**, so industry levels include chains joining and leaving; same-store growth is not affected.
- **7-Eleven's monthly figures exclude Okinawa** (a separate subsidiary, about 1% of stores).
- **METI's regional data groups Kyushu with Okinawa** for convenience stores; drugstore figures for the two are combined to match.

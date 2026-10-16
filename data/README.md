# Data sources

`data/raw/` is not committed. Rebuild it by running the download scripts from `src/`:

```bash
cd src && for f in 01*.py; do ../.venv/bin/python "$f"; done
```

`data/manual/` holds small tables typed in by hand from web pages, PDFs and images. Each row cites its source.

All files were downloaded on October 15, 2026.

## Downloaded (`data/raw/`)

| Folder | Script | What it holds | Coverage | Used in |
|---|---|---|---|---|
| `osm/` | `01a` | Every `shop=convenience` in [OpenStreetMap](https://www.openstreetmap.org) for Japan (48,973), with name and brand tags | Snapshot | Part 1 |
| `boundaries/` | `01b` | Simplified prefecture boundaries (GeoJSON) from [Global Map Japan](https://www.gsi.go.jp/kankyochiri/gm_jpn.html) (GSI), via [dataofjapan/land](https://github.com/dataofjapan/land). Free for non-commercial use with credit | 47 prefectures | Part 1 |
| `population_grid/` | `01c` | 2020 census population on the 1 km grid via [e-Stat](https://www.e-stat.go.jp/gis) (T001140): residents by age group, households, one-person households. Only map tiles containing a store (127) | 2020 census | Part 1 |
| `stations/` | `01d` | [MLIT National Land Numerical Info S12](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html): every railway station with daily passenger counts (GeoJSON) | S12-25 release | Part 1 |
| `seven_i_monthly/` | `01e` | [Seven & i monthly business performance](https://www.7andi.com/en/ir/financial/monthly_highlight.html): 7-Eleven Japan same-store sales, customers, average spend, total-store sales (all % vs. same month last year) and store count | Mar 2015 – Sep 2026, one Excel file per fiscal year | Part 2 |
| `jfa/` | `01f` | [Japan Franchise Association](https://www.jfa-fc.or.jp/particle/320.html) convenience-store statistics, all member chains combined: sales (million yen), stores, customers (thousands), average spend (yen), all stores and same stores | Jan 2005 – Aug 2026, PDF | Part 2 |
| `meti_retail/` | `01g` | METI retail survey (商業動態統計) via [e-Stat](https://www.e-stat.go.jp/stat-search/files?toukei=00550030): sales by product for convenience stores, drugstores, supermarkets, and all retail; national and by region | Monthly to Aug 2026, Excel | Part 2 |
| `cpi/` | `01h` | Consumer price index, 2020 base, via [e-Stat](https://www.e-stat.go.jp/stat-search/files?toukei=00200573): by category, and by item (includes bento, onigiri, cigarettes) | Jan 1970 – Aug 2026, CSV (Shift-JIS) | Part 2 |
| `population/` | `01h` | Population estimates by prefecture via [e-Stat](https://www.e-stat.go.jp/stat-search/files?toukei=00200524), total and by age group | Oct 1, 2024 (latest yearly release) | Part 1 |
| `seven_i_reports/` | `01i` | [Seven & i Corporate Outline FY2025](https://www.7andi.com/en/ir/library/co.html): 7-Eleven Japan yearly figures (sales by product group, margins, store types, openings), the major chains' store counts, franchise terms and the consolidated balance sheet; plus [segment Excel files](https://www.7andi.com/en/ir/financial/segment.html) (operating income and depreciation by business) | FY2015 – FY2025 | Parts 2–4 |
| `minimum_wage/` | `01j` | [MHLW](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/roudoukijun/minimumichiran/) minimum wage by prefecture, with effective dates | FY2002 – FY2026, Excel | Part 3 |
| `franchise/` | `01j` | 7-Eleven Japan [press release](https://www.sej.co.jp/company/news_release/news/2026/202606191500.html) comparing the current Type C contract with the new contract | June 19, 2026, PDF | Part 3 |
| `prices/` | `01k` | Daily share prices from Yahoo Finance: Seven & i (3382.T), TOPIX ETF (1306.T), Couche-Tard (ATD.TO), Casey's (CASY), Murphy USA (MUSA). Lawson (2651.T) is no longer available after its 2024 delisting | Jan 2015 – Oct 2026 | Part 4 |
| `sej_prefecture/` | by hand | [7-Eleven store map](https://www.sej.co.jp/company/tenpo.html) image, transcribed into `data/manual/` | End of Sep 2026 | Part 1 |

## Typed in by hand (`data/manual/`)

| File | What it holds | Check |
|---|---|---|
| `sej_stores_by_prefecture_2026-09.csv` | 7-Eleven stores in each of the 47 prefectures, end of September 2026 | Sums to 21,956, the total printed on the map |
| `franchise_terms.csv` | Type A, Type C and new (2027) contract terms: charge rates, reductions (which depend on whether monthly gross profit is above ¥5.5M), utility and waste cost shares, minimum guarantees, contract length | Type C tiers and new terms from the official release PDF; reductions and guarantees from the Corporate Outline FY2025 (p. 21) |
| `store_cost_assumptions.csv` | Low / central / high values for a store's staffing, pay, utilities, discarded stock and other costs (Part 3) | Not published anywhere; each row states its basis |
| `valuation_inputs.csv` | Share count, debt, cash, minority interests, Seven Bank and York stakes, peer multiples, Couche-Tard and KDDI–Lawson offers | Each row links its source; Yahoo Finance values are a snapshot dated 16 Oct 2026 |

## Cleaned tables (`data/processed/`)

| File | Script | What it holds | Checks it passes |
|---|---|---|---|
| `stores.csv` | `02a` | Every OSM convenience store: chain (from name and brand tags), prefecture, 1 km grid square | 74 seaside stores fall just outside the simplified boundaries and get the nearest prefecture |
| `population_grid.csv` | `02a` | 1 km squares with centre coordinates, prefecture, residents, ages, households | Adds up to 126.1 million, the 2020 census total |
| `stations.csv` | `02a` | Railway stations (station x operator) with daily passengers, latest year in the file | Duplicate per-line listings of the same station removed |
| `seven_eleven_japan_monthly.csv` | `02b` | 7-Eleven Japan, Mar 2015 – Sep 2026 (139 months): same-store sales, customers and spend, total-store sales (all % change vs. same month last year), store count | No missing months; overlapping files agree; sales growth = customers × spend to within 0.14 points |
| `jfa_convenience_monthly.csv` | `02c` | All JFA member chains, Jan 2005 – Aug 2026 (260 months): sales, stores, customers, spend per customer (levels and % change), all stores and same stores | 2026 reports' "last year" figures match the time series to within 0.05%; sales = customers × spend to within 0.01% |
| `seven_eleven_japan_annual.csv` | `02d` | 7-Eleven Japan, FY2015 – FY2025: chain sales by product group, gross margins, same-store growth, daily sales per store, store counts by contract type, openings and closures | Product groups add up to total sales; year-end store counts equal the monthly February counts |
| `chain_store_counts.csv` | `02d` | Store counts of 7-Eleven (incl. Okinawa), Lawson, FamilyMart and others, FY2020 – FY2025 | Chains add up to the nationwide total |
| `meti_national_monthly.csv` | `02e` | METI retail survey, Jan 2014 – Aug 2026: convenience stores, drugstores (incl. food) and supermarket food; levels and published growth rates | Growth rates as published (adjusted for sample redraws) |
| `meti_regional_monthly.csv` | `02e` | Same, by METI regional bureau: convenience-store and drugstore sales and store counts | |
| `minimum_wage.csv` | `02f` | Minimum wage by prefecture and fiscal year, FY2002 – FY2026, with effective dates, plus the weighted national average | 48 rows x 25 years; FY2019 is labelled 令和元年度 (era's first year) in the source |

The analysis scripts (`03`–`12`) also write their results to `data/processed/part*.csv`.

## Things to know before using the data

- **Seven & i's monthly store count excludes Okinawa.** The prefecture map totals 21,956, and without Okinawa's 211 stores it is exactly the 21,745 in the September 2026 monthly file. Okinawa is run by a separate subsidiary (7-Eleven Okinawa).
- **Seven & i's monthly figures are % vs. the same month last year, not yen.** Levels must be built by chaining the changes or taken from annual reports.
- **Seven & i's file names changed convention.** "FY2016" ends February 2016, but "FY2025" ends February 2026. The three "FY2024" files are two different years (one ends Feb 2024, two end Feb 2025). The cleaner reads each year from the sheet's own dates.
- **In the FY2021–22 files, 7-Eleven Japan's first row also repeats the previous January–February** (the header is shared with the US business's calendar year). The cleaner skips those columns.
- **JFA same-store figures are as published.** They compare stores open in both years, so "last year" differs from report to report and can't be rebuilt from the levels.
- **Some 2026 JFA reports scramble their text.** The cleaner reads figures by position on the page instead.
- **JFA counts all member chains, 7-Eleven included.** "Everyone except 7-Eleven" has to be derived.
- **OSM includes 353 stores of chains that no longer exist** (Circle K Sunkus, am/pm, Save On, Coco Store); they are flagged as stale and left out.
- **The public Overpass servers can't handle a nationwide per-prefecture query**; prefectures come from the boundary file instead.
- **OSM covers about 80% of real stores** (17,617 name matches for 7-Eleven vs. 21,956 official). Coverage must be checked by prefecture before comparing densities.
- **METI sales levels jump when the survey sample is redrawn** (convenience stores: Jan 2012, Jan 2017, Mar 2021). Use the published growth rates, which are adjusted, rather than growth computed from levels.
- **METI groups Kyushu and Okinawa** for convenience stores but not for drugstores.
- **Scraping notes:** JFA only returns PDFs to browser-like requests with the page as referer; Overpass rejects browser-like requests (406) and wants a named client; METI's own site blocks scripts, so its files come from e-Stat.

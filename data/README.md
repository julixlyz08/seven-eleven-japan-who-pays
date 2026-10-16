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
| `seven_i_monthly/` | `01a` | [Seven & i monthly business performance](https://www.7andi.com/en/ir/financial/monthly_highlight.html): 7-Eleven Japan same-store sales, customers, average spend, total-store sales (all % vs. same month last year) and store count | Mar 2015 – Sep 2026, one Excel file per fiscal year | Part 2 |
| `jfa/` | `01b` | [Japan Franchise Association](https://www.jfa-fc.or.jp/particle/320.html) convenience-store statistics, all member chains combined: sales (million yen), stores, customers (thousands), average spend (yen), all stores and same stores | Jan 2005 – Aug 2026, PDF | Part 2 |
| `meti_retail/` | `01c` | METI retail survey (商業動態統計) via [e-Stat](https://www.e-stat.go.jp/stat-search/files?toukei=00550030): sales by product for convenience stores, drugstores, supermarkets, and all retail; national and by region | Monthly to Aug 2026, Excel | Part 2 |
| `osm/` | `01d` | Every `shop=convenience` in [OpenStreetMap](https://www.openstreetmap.org) for Japan (48,973), with name and brand tags | Snapshot | Part 1 |
| `minimum_wage/` | `01e` | [MHLW](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/koyou_roudou/roudoukijun/minimumichiran/) minimum wage by prefecture, with effective dates | FY2002 – FY2026, Excel | Part 3 |
| `franchise/` | `01e` | 7-Eleven Japan [press release](https://www.sej.co.jp/company/news_release/news/2026/202606191500.html) comparing the current Type C contract with the new contract | June 19, 2026, PDF | Part 3 |
| `prices/` | `01f` | Daily share prices from Yahoo Finance: Seven & i (3382.T), TOPIX ETF (1306.T), Couche-Tard (ATD.TO), Casey's (CASY), Murphy USA (MUSA). Lawson (2651.T) is no longer available after its 2024 delisting | Jan 2015 – Oct 2026 | Part 4 |
| `cpi/` | `01g` | Consumer price index, 2020 base, via [e-Stat](https://www.e-stat.go.jp/stat-search/files?toukei=00200573): by category, and by item (includes bento, onigiri, cigarettes) | Jan 1970 – Aug 2026, CSV (Shift-JIS) | Part 2 |
| `population/` | `01g` | Population estimates by prefecture via [e-Stat](https://www.e-stat.go.jp/stat-search/files?toukei=00200524), total and by age group | Oct 1, 2024 (latest yearly release) | Part 1 |
| `stations/` | `01h` | [MLIT National Land Numerical Info S12](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html): every railway station with daily passenger counts (GeoJSON) | S12-25 release | Part 1 |
| `sej_prefecture/` | by hand | [7-Eleven store map](https://www.sej.co.jp/company/tenpo.html) image, transcribed into `data/manual/` | End of Sep 2026 | Part 1 |

## Typed in by hand (`data/manual/`)

| File | What it holds | Check |
|---|---|---|
| `sej_stores_by_prefecture_2026-09.csv` | 7-Eleven stores in each of the 47 prefectures, end of September 2026 | Sums to 21,956, the total printed on the map |
| `franchise_terms.csv` | Type A, Type C and new (2027) contract terms: charge rates, reductions, utility and waste cost shares, minimum guarantee, contract length | Type C and new terms from the official release PDF |
| `valuation_inputs.csv` | Couche-Tard and KDDI–Lawson offer prices and dates, Seven & i domestic segment results | Each row links its source |

## Cleaned tables (`data/processed/`)

| File | Script | What it holds | Checks it passes |
|---|---|---|---|
| `seven_eleven_japan_monthly.csv` | `02a` | 7-Eleven Japan, Mar 2015 – Sep 2026 (139 months): same-store sales, customers and spend, total-store sales (all % change vs. same month last year), store count | No missing months; overlapping files agree; sales growth = customers × spend to within 0.14 points |
| `jfa_convenience_monthly.csv` | `02b` | All JFA member chains, Jan 2005 – Aug 2026 (260 months): sales, stores, customers, spend per customer (levels and % change), all stores and same stores | 2026 reports' "last year" figures match the time series to within 0.05%; sales = customers × spend to within 0.01% |

## Things to know before using the data

- **Seven & i's monthly store count excludes Okinawa.** The prefecture map totals 21,956, and without Okinawa's 211 stores it is exactly the 21,745 in the September 2026 monthly file. Okinawa is run by a separate subsidiary (7-Eleven Okinawa).
- **Seven & i's monthly figures are % vs. the same month last year, not yen.** Levels must be built by chaining the changes or taken from annual reports.
- **Seven & i's file names changed convention.** "FY2016" ends February 2016, but "FY2025" ends February 2026. The three "FY2024" files are two different years (one ends Feb 2024, two end Feb 2025). The cleaner reads each year from the sheet's own dates.
- **In the FY2021–22 files, 7-Eleven Japan's first row also repeats the previous January–February** (the header is shared with the US business's calendar year). The cleaner skips those columns.
- **JFA same-store figures are as published.** They compare stores open in both years, so "last year" differs from report to report and can't be rebuilt from the levels.
- **Some 2026 JFA reports scramble their text.** The cleaner reads figures by position on the page instead.
- **JFA counts all member chains, 7-Eleven included.** "Everyone except 7-Eleven" has to be derived.
- **OSM covers about 80% of real stores** (17,617 name matches for 7-Eleven vs. 21,956 official). Coverage must be checked by prefecture before comparing densities.
- **Scraping notes:** JFA only returns PDFs to browser-like requests with the page as referer; Overpass rejects browser-like requests (406) and wants a named client; METI's own site blocks scripts, so its files come from e-Stat.

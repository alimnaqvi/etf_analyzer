# ETF Portfolio Analyzer

A Python tool that provides transparency into the underlying holdings of an ETF-based investment portfolio. Since ETFs are composed of hundreds or thousands of individual securities, it can be difficult to understand real exposure at the country, sector, or company level, especially across multiple funds. This project solves that by fetching holdings data from Morningstar, combining it with actual portfolio market values, and producing an interactive dashboard that breaks down aggregate exposures.

## Dashboard Screenshots

### Country Exposure
![Top 20 Country Exposures](img/country-exposures.png)

### Sector Allocation
![Sector Allocation](img/sector-exposures.png)

### Top Company Exposures
![Top 20 Company Exposures](img/company-exposures.png)

## How It Works

The project follows a three-stage pipeline:

1. **Data Extraction** — Pull the latest holdings data for each ETF from Morningstar via the [`mstarpy`](https://github.com/Mael-J/mstarpy) library and cache it locally.
2. **Exposure Calculation** — Combine cached holdings with actual portfolio market values to compute weighted exposure by country, sector, and individual company.
3. **Visualization** — Serve an interactive Dash dashboard that displays the computed exposures with a dropdown to compare across different portfolio snapshots over time.

## Project Structure

```
etf-analyzer/
├── scripts/
│   ├── extract_holdings_data.py   # Stage 1: Fetch & cache holdings from Morningstar
│   ├── holdings_analysis.py       # Stage 2: Calculate weighted exposures
│   ├── dashboard.py               # Stage 3: Interactive Plotly Dash dashboard
│   └── util_funcs.py              # Shared helpers (slugify, rate-limiting, etc.)
├── portfolio-data/
│   ├── funds_list.csv             # Master list of ETFs with ISINs, tickers, slugs
│   └── <YYYY-MM>/                 # Grouped by mstar cache extraction period
│       └── <YYYY-MM-DD>/          # Portfolio snapshot ("tag") date
│           └── <date>_portfolio.csv
├── mstar-data-cache/
│   └── <YYYY-MM>/                 # Cached holdings CSVs from Morningstar
├── processed_data/
│   └── <YYYY-MM-DD>/              # Computed exposure CSVs per snapshot
│       ├── exposure_country.csv
│       ├── exposure_sector.csv
│       └── exposure_company.csv
├── notebooks/
│   └── quick_query.ipynb          # Ad-hoc data exploration notebook
├── img/                           # Dashboard screenshots
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Key dependencies: `mstarpy`, `pandas`, `dash`, `plotly`

## Usage

### 1. Define the portfolio

List the ETFs in `portfolio-data/funds_list.csv` with their ISINs, tickers, slugs, and any alternative search terms used for Morningstar lookups:

| Column | Purpose |
|---|---|
| Fund name | Display name |
| Slug | Filename-safe identifier (used for caching) |
| ISIN | Primary identifier for Morningstar search |
| Ticker | Fallback search term |
| Tracked index | Another fallback search term |
| Alternative ISINs | Comma-separated additional ISINs to try |
| Additional terms | Pipe-separated extra search terms |

Place portfolio market-value snapshots as CSV files under `portfolio-data/<YYYY-MM>/<YYYY-MM-DD>/`. The CSV must contain an `ISIN` column and a column with "Market Value in Account" in its header.

### 2. Extract holdings data

```bash
python scripts/extract_holdings_data.py
```

This fetches holdings for each fund from Morningstar (trying ISIN, ticker, and alternative terms in order) and caches the results in `mstar-data-cache/<YYYY-MM>/`. Previously cached funds are skipped automatically. A staleness warning is printed if the extraction period is more than 3 months old.

### 3. Calculate exposures

```bash
python scripts/holdings_analysis.py
```

For each portfolio snapshot, the script:
- Loads market values and merges with the funds metadata to resolve slugs
- Reads cached holdings for each fund, filtering to equity positions only
- Weights each underlying security by the fund's share of total portfolio value
- Aggregates by country, sector, and company and writes sorted CSVs to `processed_data/<YYYY-MM-DD>/`

### 4. Launch the dashboard

```bash
python scripts/dashboard.py
```

Opens an interactive Dash app at `http://127.0.0.1:8050/` featuring:
- **Dropdown selector** to switch between portfolio snapshot dates
- **Bar chart** of top 20 country exposures
- **Donut chart** of sector allocation
- **Horizontal bar chart** of top 20 company exposures

All charts update dynamically when a different snapshot is selected.

## Tech Stack

| Component | Technology |
|---|---|
| Data extraction | `mstarpy` (Morningstar API wrapper) |
| Data processing | `pandas` |
| Dashboard | `Dash` + `Plotly` |
| Ad-hoc analysis | Jupyter Notebook |

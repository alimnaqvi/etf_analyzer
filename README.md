# ETF Portfolio Analyzer

A comprehensive Python-based analytics pipeline and interactive dashboard designed to provide deep transparency into ETF-based investment portfolios. 

While ETFs offer great diversification, they often obscure the underlying realities of an investment. It can be difficult to understand true exposure at the country, sector, or company level across multiple funds, or to accurately measure money-weighted returns (XIRR) when dollar-cost averaging over time. 

This project solves these challenges by:
1. **Fetching and caching** underlying holdings data from Morningstar.
2. **Parsing raw broker transactions** to reconstruct historical prices, cash flows, and invested capital.
3. **Computing** aggregate weighted exposures and precise performance metrics (Total Return, XIRR, Yearly Returns).
4. **Visualizing** the insights through a rich, interactive Streamlit dashboard.

## Dashboard Demo

https://github.com/user-attachments/assets/c2c0e1ac-32d0-4f62-8448-a5853c9ff741

## Key Features

- **Deep Exposure Analysis**: See exactly what percentage of your portfolio is allocated to specific countries, sectors, and individual companies (e.g., "How much Apple do I actually own across all my ETFs?").
- **Transaction-Aware Performance**: Calculates true Money-Weighted Return (XIRR) and Total Return by analyzing every historical buy, sell, and savings plan execution.
- **Historical Price Reconstruction**: Derives historical ETF unit prices directly from your transaction history, eliminating the need for external price APIs.
- **Yearly Return Heatmaps**: Visualizes fund-by-fund performance across different calendar years.
- **Interactive Streamlit UI**: A multi-tab dashboard (Exposure, Returns, Investment) with dynamic filtering, sorting, and Vega-Lite charts.

## How It Works

The project follows a four-stage pipeline:

1. **Data Extraction** — Pull the latest holdings data for each ETF from Morningstar via the [`mstarpy`](https://github.com/Mael-J/mstarpy) library and cache it locally.
2. **Exposure Calculation** — Combine cached holdings with actual portfolio market values to compute weighted exposure by country, sector, and individual company.
3. **Transaction Analysis** — Parse raw broker transaction exports to compute net invested capital, current value, XIRR, and yearly returns.
4. **Visualization** — Serve an interactive Streamlit dashboard to explore exposures, returns, and investment outcomes across snapshots.

## Project Structure

```
etf-analyzer/
├── scripts/
│   ├── extract_holdings_data.py   # Stage 1: Fetch & cache holdings from Morningstar
│   ├── holdings_analysis.py       # Stage 2: Calculate weighted exposures
│   ├── transactions_analysis.py   # Stage 3: Analyze returns and invested capital from transactions
│   ├── dashboard.py               # Stage 4: Interactive Streamlit dashboard
│   └── util_funcs.py              # Shared helpers (slugify, rate-limiting, etc.)
├── portfolio-data/
│   ├── funds_list.csv             # Master list of ETFs with ISINs, tickers, slugs
│   └── <YYYY-MM>/                 # Grouped by mstar cache extraction period
│       └── <YYYY-MM-DD>/          # Portfolio snapshot ("tag") date
│           └── <date>_portfolio.csv
├── transactions-data/             # User-provided broker transaction exports (e.g., Scalable Capital)
├── mstar-data-cache/
│   └── <YYYY-MM>/                 # Cached holdings CSVs from Morningstar
├── processed_data/
│   ├── <YYYY-MM-DD>/              # Computed exposure CSVs per snapshot
│   │   ├── exposure_country.csv
│   │   ├── exposure_sector.csv
│   │   └── exposure_company.csv
│   └── transactions/              # Computed performance and investment CSVs
│       └── <YYYY-MM-DD>/
│           ├── fund_price_history.csv
│           ├── fund_yearly_returns.csv
│           ├── portfolio_yearly_returns.csv
│           ├── fund_investment_summary.csv
│           └── portfolio_investment_summary.csv
├── notebooks/
│   └── quick_query.ipynb          # Ad-hoc data exploration notebook
├── img/                           # Dashboard screenshots
├── requirements.txt
└── README.md
```

## Technical Stack

- **Python 3.10+**
- **Pandas**: Core data manipulation, time-series analysis, and financial calculations.
- **Streamlit**: Interactive web application framework for the frontend dashboard.
- **Vega-Lite**: Declarative visualization grammar used within Streamlit for complex, interactive charts (heatmaps, donuts, bar charts).
- **mstarpy**: Unofficial Morningstar API wrapper for fetching ETF holdings.
- **Financial Math**: Custom implementation of the Extended Internal Rate of Return (XIRR) algorithm using `scipy.optimize.newton` to calculate money-weighted returns based on irregular cash flows.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Key dependencies: `mstarpy`, `pandas`, `streamlit`

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

### 4. Analyze returns and investment outcomes

```bash
python scripts/transactions_analysis.py
```

The script automatically picks the latest `transactions-data/scalable_transactions_YYYY-MM-DD.csv` file and writes reports to `processed_data/transactions/<YYYY-MM-DD>/`:
- `fund_price_history.csv`: Transaction-derived unit prices per fund over time.
- `fund_yearly_returns.csv`: Yearly fund returns based on start/end transaction-implied prices.
- `portfolio_yearly_returns.csv`: Yearly portfolio return using opening-year weights.
- `fund_investment_summary.csv`: Net invested, current value, total return, and money-weighted return (XIRR) per fund.
- `portfolio_investment_summary.csv`: Portfolio-level net invested, current value, total return, and money-weighted return (XIRR).

You can also pass a specific file:

```bash
python scripts/transactions_analysis.py --transactions-file transactions-data/scalable_transactions_2026-02-20.csv
```

### 5. Launch the dashboard

```bash
streamlit run scripts/dashboard.py
```

Opens an interactive Streamlit app (typically at `http://localhost:8501/`) featuring three main tabs:

1. **Exposure Tab**: 
   - **Bar chart** of top 20 country exposures.
   - **Donut chart** of sector allocation.
   - **Horizontal bar chart** of top 20 company exposures.
2. **Returns Tab**: 
   - **Portfolio yearly returns** bar chart.
   - **Fund returns heatmap** showing performance across different calendar years.
3. **Investment Tab**: 
   - **Investment KPIs** (net invested, current value, total return, money-weighted return).
   - **Fund-level investment table** detailing XIRR and total returns per asset.
   - **Transaction-implied price history chart** tracking unit prices over time.

All visuals update dynamically when different snapshots, years, and funds are selected.

## Appendix: Extracting Transactions from Scalable Capital

Scalable Capital's CSV export for all transactions is a paid feature. The following browser console script scrapes the transactions page and downloads them as a CSV, which can then be used to produce the portfolio snapshot files consumed by this project.

**Steps:**

1. Open your [Scalable Capital](https://scalable.capital/) transactions page.
2. Scroll down until all the transactions you want to analyze are loaded.
3. Open Developer Tools (`F12` or `Ctrl+Shift+I` / `Cmd+Option+I`) and go to the **Console** tab.
4. Paste the script below and press **Enter**. A CSV file will be downloaded automatically.

<details>
<summary>Browser console script (click to expand)</summary>

```js
(function extractScalableTransactions() {
    const transactions = [];
    const items = document.querySelectorAll('li[class*="-listItem"]');

    // HELPER: Find specific elements but strictly ignore "Container" wrappers
    const findNode = (parent, classNamePart) => {
        return Array.from(parent.querySelectorAll('*')).find(el => 
            el.className && 
            typeof el.className === 'string' && 
            el.className.includes(classNamePart) && 
            !el.className.includes('Container')
        );
    };

    items.forEach(item => {
        const button = item.querySelector('button');
        if (!button) return;

        // 1. Date and Status
        const ariaLabel = button.getAttribute('aria-labelledby') || '';
        const dateString = ariaLabel.split(': ')[0];
        const testId = button.getAttribute('data-testid') || '';
        const status = testId.includes('PENDING') ? 'Pending' : 'Settled';

        // 2. Type (Buy, Savings Plan, Deposit)
        const typeNode = findNode(item, '-type');
        const type = typeNode ? typeNode.innerText.trim() : 'Unknown';

        // 3. Name and ISIN
        let name = '';
        let isin = '';
        const linkNode = item.querySelector('a[href*="isin="]');
        
        if (linkNode) {
            name = linkNode.innerText.trim();
            const urlParams = new URLSearchParams(linkNode.getAttribute('href').split('?')[1]);
            isin = urlParams.get('isin') || '';
        } else {
            const descNode = findNode(item, '-description');
            if (descNode) name = descNode.innerText.trim();
        }

        // 4. Shares
        let shares = '';
        const sharesNode = findNode(item, '-numberOfShares');
        if (sharesNode) {
            const sharesText = sharesNode.innerText.replace(/[^\d.]/g, '');
            shares = parseFloat(sharesText) || 0;
        }

        // 5. Amount
        let amount = '';
        const statusNode = findNode(item, '-currentStatus');
        if (statusNode) {
            const statusText = statusNode.innerText.trim();
            if (statusText !== 'Pending') {
                const cleanAmount = statusText.replace(/[^\d.-]/g, '');
                amount = parseFloat(cleanAmount) || 0;
            }
        }

        transactions.push({
            Date: dateString,
            Status: status,
            Type: type,
            Name: name,
            ISIN: isin,
            Shares: shares,
            Amount: amount
        });
    });

    if (transactions.length === 0) {
        console.warn("No transactions found.");
        return;
    }

    // --- Convert to CSV ---
    const headers = ["Date", "Status", "Type", "Name", "ISIN", "Shares", "Amount"];
    const csvRows = [headers.join(',')];

    transactions.forEach(t => {
        const row = [
            t.Date,
            t.Status,
            t.Type,
            `"${t.Name}"`,
            t.ISIN,
            t.Shares,
            t.Amount
        ];
        csvRows.push(row.join(','));
    });

    const csvString = csvRows.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    
    link.setAttribute("href", url);
    link.setAttribute("download", `scalable_transactions_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log(`Successfully extracted ${transactions.length} transactions!`);
})();
```

</details>

The downloaded CSV contains columns: `Date`, `Status`, `Type`, `Name`, `ISIN`, `Shares`, `Amount`.

## Tech Stack

| Component | Technology |
|---|---|
| Data extraction | `mstarpy` (Morningstar API wrapper) |
| Data processing | `pandas` |
| Dashboard | `Streamlit` |
| Ad-hoc analysis | Jupyter Notebook |

# ETF Analyzer

`extract_holdings_data.py` script uses [`mstarpy`](https://github.com/Mael-J/mstarpy) to extract holdings data of each fund listed in the `portfolio-data/funds_list.csv` file and saves it to `mstar-data-cache` directory.

`holdings_analysis.py` script analyzes the current market values in the portolio (data expected in `downloads` directory) and calculates exposure data including:

- Exposure by country
- Exposure by company
- Exposure by sector

Calculated exposures are saved in `processed_data` directory.

`dashboard.py` creates a dashboard for visualizing the exposures data.

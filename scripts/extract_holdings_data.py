import mstarpy as ms
from pathlib import Path
import csv
import util_funcs
import time

EXTRACTION_PERIOD = "2026-02" # To be updated for future mstar data extraction
SCRIPT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SCRIPT_DIR.parent
MSTAR_DATA_DIR = ROOT_DIR / "mstar-data-cache" / EXTRACTION_PERIOD
FUNDS_LIST_FILE = ROOT_DIR / "portfolio-data" / "funds_list.csv"

def save_holdings_to_csv(term: str, output_csv: Path):
    try:
        fund = ms.Funds(term=term)
        holdings_data = fund.holdings()
        if holdings_data.empty:
            print(f"Received empty holdings DataFrame")
            return None
        holdings_data.to_csv(output_csv, index=False)
        print(f"Successfully saved holdings data to {output_csv.name}")
        return output_csv
    except Exception as e:
        print(f"An error occurred while saving holdings data: {e}")
    return None


def init_mstar_extraction(row):
    fund_name = row['Fund name']
    fund_slug = row['Slug']
    isin = row['ISIN']
    ticker = row['Ticker']
    alt_isins = row['Alternative ISINs'].split(sep=',')
    tracked_index = row['Tracked index']
    additional_terms = row['Additional terms (|-separated)'].split(sep='|')

    MSTAR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_csv = MSTAR_DATA_DIR / fund_slug
    output_csv = output_csv.with_suffix(".csv")
    if output_csv.exists():
        print(f"Skipping data pull for {fund_name} because its data has previously been saved. File: {output_csv.name}")
        return None

    terms = [isin] + [ticker] + alt_isins + [tracked_index] + additional_terms
    terms = [term for term in terms if term] # Remove empty strings

    for term in terms:
        print(f"Using term '{term}' to extract mstar data for {fund_name}")
        last_request_time = time.time()
        saved_csv_path = save_holdings_to_csv(term, output_csv)
        util_funcs.sleep_if_quick(last_request_time, s_thresh=1.5)
        if saved_csv_path:
            break


def main():
    util_funcs.check_months_ago(EXTRACTION_PERIOD)
    with open(FUNDS_LIST_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            init_mstar_extraction(row)
            print("")


if __name__ == "__main__":
    main()

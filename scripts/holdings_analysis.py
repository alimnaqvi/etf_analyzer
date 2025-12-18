import pandas as pd
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTFOLIO_FILE = os.path.join(BASE_DIR, 'downloads', '2025-09-30_MiFID-II.csv')
FUNDS_LIST_FILE = os.path.join(BASE_DIR, 'portfolio-data', 'funds_list.csv')
CACHE_DIR = os.path.join(BASE_DIR, 'mstar-data-cache')
OUTPUT_DIR = os.path.join(BASE_DIR, 'processed_data')

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_portfolio():
    """Loads the portfolio current market values."""
    df = pd.read_csv(PORTFOLIO_FILE)
    # Identify the value column (starts with a date)
    value_col = [c for c in df.columns if 'Market Value in Account' in c][0]
    # Clean up column names for easier access
    df = df.rename(columns={value_col: 'MarketValue', 'ISIN': 'ISIN'})
    return df[['ISIN', 'MarketValue', 'Fund name']]

def load_funds_metadata():
    """Loads the mapping between ISIN and Slug."""
    df = pd.read_csv(FUNDS_LIST_FILE)
    return df[['ISIN', 'Slug']]

def process_holdings():
    portfolio = load_portfolio()
    metadata = load_funds_metadata()
    
    # Merge to get Slugs
    portfolio = pd.merge(portfolio, metadata, on='ISIN', how='left')
    
    total_portfolio_value = portfolio['MarketValue'].sum()
    print(f"Total Portfolio Value: {total_portfolio_value:,.2f} EUR")

    all_holdings = []

    for _, row in portfolio.iterrows():
        fund_name = row['Fund name']
        slug = row['Slug']
        fund_value = row['MarketValue']
        
        cache_file = os.path.join(CACHE_DIR, f"{slug}.csv")
        
        if os.path.exists(cache_file):
            # Load cached holdings
            holdings_df = pd.read_csv(cache_file)
            holdings_df = holdings_df[holdings_df['holdingType'] == 'Equity'] # Ignore non-equity securities
            
            # Ensure weighting is numeric
            holdings_df['weighting'] = pd.to_numeric(holdings_df['weighting'], errors='coerce').fillna(0)
            
            # Calculate absolute value of this holding in the user's portfolio
            # weighting is usually percentage (0-100)
            holdings_df['UserMarketValue'] = (holdings_df['weighting'] / 100.0) * fund_value
            
            # Keep relevant columns
            cols_to_keep = ['securityName', 'country', 'sector', 'UserMarketValue']
            # Handle missing columns if any
            existing_cols = [c for c in cols_to_keep if c in holdings_df.columns]
            fund_holdings = holdings_df[existing_cols].copy()
            
            # Fill missing metadata
            if 'country' not in fund_holdings.columns: fund_holdings['country'] = 'Unknown'
            if 'sector' not in fund_holdings.columns: fund_holdings['sector'] = 'Unknown'
            if 'securityName' not in fund_holdings.columns: fund_holdings['securityName'] = 'Unknown'

            fund_holdings['FundSource'] = fund_name
            all_holdings.append(fund_holdings)
            
        else:
            print(f"Warning: No cache found for {fund_name} ({slug}). Treating as 'Other'.")
            # Create a dummy holding for the missing fund
            dummy_holding = pd.DataFrame([{
                'securityName': 'Other / Data Unavailable',
                'country': 'Other',
                'sector': 'Other',
                'UserMarketValue': fund_value,
                'FundSource': fund_name
            }])
            all_holdings.append(dummy_holding)

    # Combine all
    if not all_holdings:
        print("No holdings data found.")
        return

    full_df = pd.concat(all_holdings, ignore_index=True)
    
    # --- Aggregations ---

    # 1. Country Exposure
    country_exp = full_df.groupby('country')['UserMarketValue'].sum().reset_index()
    country_exp['Weight'] = (country_exp['UserMarketValue'] / total_portfolio_value) * 100
    country_exp = country_exp.sort_values('Weight', ascending=False)
    country_exp.to_csv(os.path.join(OUTPUT_DIR, 'exposure_country.csv'), index=False)
    print("\nTop 5 Countries:")
    print(country_exp.head(5))

    # 2. Sector Exposure
    sector_exp = full_df.groupby('sector')['UserMarketValue'].sum().reset_index()
    sector_exp['Weight'] = (sector_exp['UserMarketValue'] / total_portfolio_value) * 100
    sector_exp = sector_exp.sort_values('Weight', ascending=False)
    sector_exp.to_csv(os.path.join(OUTPUT_DIR, 'exposure_sector.csv'), index=False)
    print("\nTop 5 Sectors:")
    print(sector_exp.head(5))

    # 3. Company Exposure
    company_exp = full_df.groupby('securityName')['UserMarketValue'].sum().reset_index()
    company_exp['Weight'] = (company_exp['UserMarketValue'] / total_portfolio_value) * 100
    company_exp = company_exp.sort_values('Weight', ascending=False)
    company_exp.to_csv(os.path.join(OUTPUT_DIR, 'exposure_company.csv'), index=False)
    print("\nTop 5 Companies:")
    print(company_exp.head(5))

if __name__ == "__main__":
    process_holdings()

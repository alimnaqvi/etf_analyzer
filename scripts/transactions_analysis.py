import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SCRIPT_DIR.parent
TRANSACTIONS_DIR = ROOT_DIR / "transactions-data"
FUNDS_LIST_FILE = ROOT_DIR / "portfolio-data" / "funds_list.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "processed_data" / "transactions"

TRANSACTION_FILE_PATTERN = re.compile(r"scalable_transactions_(\d{4}-\d{2}-\d{2})\.csv$")

INCREASE_POSITION_TYPES = {"buy", "savings plan", "transfer in"}
DECREASE_POSITION_TYPES = {"sell", "transfer out"}


def pick_latest_transactions_file(transactions_dir: Path) -> Path:
    files = []
    for candidate in transactions_dir.glob("scalable_transactions_*.csv"):
        match = TRANSACTION_FILE_PATTERN.search(candidate.name)
        if match:
            files.append((pd.Timestamp(match.group(1)), candidate))

    if not files:
        raise FileNotFoundError(
            f"No transactions file matching scalable_transactions_YYYY-MM-DD.csv in {transactions_dir}"
        )

    files.sort(key=lambda item: item[0])
    return files[-1][1]


def load_transactions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    required_columns = {"Date", "Status", "Type", "Name", "ISIN", "Shares", "Amount"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Transactions file is missing required columns: {sorted(missing)}")

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce").dt.tz_localize(None)
    df["Shares"] = pd.to_numeric(df["Shares"], errors="coerce").fillna(0.0)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    df["Status"] = df["Status"].astype(str)
    df["Type"] = df["Type"].astype(str)
    df["ISIN"] = df["ISIN"].fillna("").astype(str).str.strip()

    df = df[df["Status"].str.lower() == "settled"].copy()
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return df


def build_fund_metadata(path: Path) -> pd.DataFrame:
    funds = pd.read_csv(path)
    expected = {"Fund name", "ISIN"}
    missing = expected - set(funds.columns)
    if missing:
        raise ValueError(f"Funds list file is missing required columns: {sorted(missing)}")

    return funds[["ISIN", "Fund name"]].rename(columns={"Fund name": "FundName"})


def add_position_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    type_lower = out["Type"].str.lower().str.strip()
    direction = np.select(
        [type_lower.isin(INCREASE_POSITION_TYPES), type_lower.isin(DECREASE_POSITION_TYPES)],
        [1.0, -1.0],
        default=0.0,
    )

    out["ShareDirection"] = direction
    out["SignedShares"] = out["Shares"] * out["ShareDirection"]
    return out


def build_price_history(df: pd.DataFrame) -> pd.DataFrame:
    fund_rows = df[(df["ISIN"] != "") & (df["Shares"] > 0) & (df["Amount"] != 0)].copy()
    fund_rows["UnitPrice"] = fund_rows["Amount"].abs() / fund_rows["Shares"]

    price_history = (
        fund_rows[["Date", "ISIN", "Type", "UnitPrice"]]
        .sort_values(["ISIN", "Date"]) 
        .reset_index(drop=True)
    )
    return price_history


def xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float:
    if len(cashflows) < 2:
        return np.nan

    amounts = np.array([cf[1] for cf in cashflows], dtype=float)
    if np.all(amounts >= 0) or np.all(amounts <= 0):
        return np.nan

    t0 = cashflows[0][0]
    years = np.array([(cf[0] - t0).days / 365.25 for cf in cashflows], dtype=float)

    def npv(rate: float) -> float:
        return float(np.sum(amounts / np.power(1.0 + rate, years)))

    low, high = -0.9999, 10.0
    f_low, f_high = npv(low), npv(high)

    for _ in range(10):
        if f_low * f_high <= 0:
            break
        high *= 2
        f_high = npv(high)
    else:
        return np.nan

    for _ in range(200):
        mid = (low + high) / 2
        f_mid = npv(mid)

        if abs(f_mid) < 1e-8:
            return mid

        if f_low * f_mid <= 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid

    return (low + high) / 2


def get_price_at_or_before(price_df: pd.DataFrame, isin: str, date_point: pd.Timestamp) -> float:
    subset = price_df[(price_df["ISIN"] == isin) & (price_df["Date"] <= date_point)]
    if subset.empty:
        return np.nan
    return float(subset.iloc[-1]["UnitPrice"])


def get_opening_price_for_year(price_df: pd.DataFrame, isin: str, year: int) -> float:
    start = pd.Timestamp(year=year, month=1, day=1)
    at_or_before = get_price_at_or_before(price_df, isin, start)
    if not np.isnan(at_or_before):
        return at_or_before

    within_year = price_df[(price_df["ISIN"] == isin) & (price_df["Date"].dt.year == year)]
    if within_year.empty:
        return np.nan
    return float(within_year.iloc[0]["UnitPrice"])


def build_fund_yearly_returns(price_df: pd.DataFrame, fund_info: pd.DataFrame, as_of_date: pd.Timestamp) -> pd.DataFrame:
    if price_df.empty:
        return pd.DataFrame(
            columns=[
                "Year",
                "ISIN",
                "FundName",
                "OpeningPrice",
                "ClosingPrice",
                "YearlyReturnPct",
            ]
        )

    min_year = int(price_df["Date"].dt.year.min())
    max_year = int(as_of_date.year)

    rows = []
    for isin in sorted(price_df["ISIN"].unique()):
        for year in range(min_year, max_year + 1):
            start_price = get_opening_price_for_year(price_df, isin, year)
            if np.isnan(start_price) or start_price <= 0:
                continue

            year_end = pd.Timestamp(year=year, month=12, day=31)
            end_point = min(year_end, as_of_date)
            end_price = get_price_at_or_before(price_df, isin, end_point)
            if np.isnan(end_price):
                continue

            yearly_return = ((end_price / start_price) - 1.0) * 100.0
            rows.append(
                {
                    "Year": year,
                    "ISIN": isin,
                    "OpeningPrice": start_price,
                    "ClosingPrice": end_price,
                    "YearlyReturnPct": yearly_return,
                }
            )

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.merge(fund_info, on="ISIN", how="left")
    out["FundName"] = out["FundName"].fillna(out["ISIN"])
    out = out[["Year", "ISIN", "FundName", "OpeningPrice", "ClosingPrice", "YearlyReturnPct"]]
    return out.sort_values(["Year", "FundName"]).reset_index(drop=True)


def build_shares_history(fund_tx: pd.DataFrame) -> pd.DataFrame:
    history = (
        fund_tx[["Date", "ISIN", "SignedShares"]]
        .groupby(["Date", "ISIN"], as_index=False)["SignedShares"]
        .sum()
        .sort_values(["ISIN", "Date"]) 
    )
    history["CumulativeShares"] = history.groupby("ISIN")["SignedShares"].cumsum()
    return history.reset_index(drop=True)


def shares_as_of(shares_hist: pd.DataFrame, isin: str, date_point: pd.Timestamp) -> float:
    subset = shares_hist[(shares_hist["ISIN"] == isin) & (shares_hist["Date"] <= date_point)]
    if subset.empty:
        return 0.0
    return float(subset.iloc[-1]["CumulativeShares"])


def build_portfolio_yearly_returns(
    fund_yearly: pd.DataFrame,
    shares_hist: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    if fund_yearly.empty:
        return pd.DataFrame(columns=["Year", "PortfolioYearlyReturnPct", "OpeningPortfolioValue", "FundsUsed"])

    rows = []
    for year in sorted(fund_yearly["Year"].unique()):
        start = pd.Timestamp(year=year, month=1, day=1)
        year_df = fund_yearly[fund_yearly["Year"] == year].copy()

        opening_values = []
        weighted_returns = []

        for _, record in year_df.iterrows():
            isin = record["ISIN"]
            opening_price = float(record["OpeningPrice"])
            yearly_return_pct = float(record["YearlyReturnPct"])
            opening_shares = shares_as_of(shares_hist, isin, start)

            opening_value = opening_shares * opening_price
            if opening_value <= 0:
                continue

            opening_values.append(opening_value)
            weighted_returns.append(opening_value * yearly_return_pct)

        if not opening_values:
            continue

        total_opening = float(np.sum(opening_values))
        portfolio_return = float(np.sum(weighted_returns) / total_opening)

        rows.append(
            {
                "Year": year,
                "PortfolioYearlyReturnPct": portfolio_return,
                "OpeningPortfolioValue": total_opening,
                "FundsUsed": len(opening_values),
            }
        )

    out = pd.DataFrame(rows)
    return out.sort_values("Year").reset_index(drop=True)


def build_fund_investment_summary(
    fund_tx: pd.DataFrame,
    shares_hist: pd.DataFrame,
    price_df: pd.DataFrame,
    fund_info: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    latest_prices = (
        price_df.sort_values("Date").groupby("ISIN", as_index=False).tail(1)[["ISIN", "UnitPrice"]]
        .rename(columns={"UnitPrice": "LatestPrice"})
        .reset_index(drop=True)
    )

    cash_by_fund = fund_tx.groupby("ISIN", as_index=False)["Amount"].sum().rename(columns={"Amount": "CashFlowSum"})

    latest_shares = (
        shares_hist.sort_values("Date").groupby("ISIN", as_index=False).tail(1)[["ISIN", "CumulativeShares"]]
        .rename(columns={"CumulativeShares": "CurrentShares"})
        .reset_index(drop=True)
    )

    out = cash_by_fund.merge(latest_shares, on="ISIN", how="outer").merge(latest_prices, on="ISIN", how="left")
    out = out.fillna({"CashFlowSum": 0.0, "CurrentShares": 0.0})

    out["NetInvested"] = -out["CashFlowSum"]
    out["CurrentValue"] = out["CurrentShares"] * out["LatestPrice"]
    out["TotalReturn"] = out["CurrentValue"] - out["NetInvested"]
    out["TotalReturnPct"] = np.where(out["NetInvested"] > 0, (out["TotalReturn"] / out["NetInvested"]) * 100.0, np.nan)

    irr_values = []
    for isin in out["ISIN"]:
        tx_rows = fund_tx[(fund_tx["ISIN"] == isin) & (fund_tx["Amount"] != 0)][["Date", "Amount"]].sort_values("Date")
        cashflows = [(row.Date, float(row.Amount)) for row in tx_rows.itertuples(index=False)]

        current_value = float(out.loc[out["ISIN"] == isin, "CurrentValue"].iloc[0])
        if current_value > 0:
            cashflows.append((as_of_date, current_value))

        irr = xirr(cashflows)
        irr_values.append(irr * 100.0 if not np.isnan(irr) else np.nan)

    out["MoneyWeightedReturnPct"] = irr_values

    out = out.merge(fund_info, on="ISIN", how="left")
    out["FundName"] = out["FundName"].fillna(out["ISIN"])

    out = out[
        [
            "ISIN",
            "FundName",
            "NetInvested",
            "CurrentShares",
            "LatestPrice",
            "CurrentValue",
            "TotalReturn",
            "TotalReturnPct",
            "MoneyWeightedReturnPct",
        ]
    ].sort_values("CurrentValue", ascending=False)

    return out.reset_index(drop=True)


def build_portfolio_investment_summary(
    fund_tx: pd.DataFrame,
    fund_summary: pd.DataFrame,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    net_invested = float(fund_summary["NetInvested"].sum())
    current_value = float(fund_summary["CurrentValue"].sum())
    total_return = current_value - net_invested
    total_return_pct = (total_return / net_invested * 100.0) if net_invested > 0 else np.nan

    tx_flows = fund_tx[fund_tx["Amount"] != 0][["Date", "Amount"]].copy()
    tx_flows = tx_flows.groupby("Date", as_index=False)["Amount"].sum().sort_values("Date")
    cashflows = [(row.Date, float(row.Amount)) for row in tx_flows.itertuples(index=False)]
    if current_value > 0:
        cashflows.append((as_of_date, current_value))

    irr = xirr(cashflows)

    out = pd.DataFrame(
        [
            {
                "AsOfDate": as_of_date.date().isoformat(),
                "NetInvested": net_invested,
                "CurrentValue": current_value,
                "TotalReturn": total_return,
                "TotalReturnPct": total_return_pct,
                "MoneyWeightedReturnPct": (irr * 100.0) if not np.isnan(irr) else np.nan,
            }
        ]
    )
    return out


def analyze_transactions(transactions_file: Path, output_root: Path) -> Path:
    transactions = load_transactions(transactions_file)
    funds_meta = build_fund_metadata(FUNDS_LIST_FILE)

    tx = add_position_signals(transactions)
    fund_tx = tx[tx["ISIN"] != ""].copy()

    price_history = build_price_history(fund_tx)
    shares_history = build_shares_history(fund_tx)

    as_of_date = transactions["Date"].max().normalize()
    file_date_match = TRANSACTION_FILE_PATTERN.search(transactions_file.name)
    file_date = file_date_match.group(1) if file_date_match else as_of_date.date().isoformat()

    fund_yearly = build_fund_yearly_returns(price_history, funds_meta, as_of_date)
    portfolio_yearly = build_portfolio_yearly_returns(fund_yearly, shares_history, as_of_date)
    fund_summary = build_fund_investment_summary(fund_tx, shares_history, price_history, funds_meta, as_of_date)
    portfolio_summary = build_portfolio_investment_summary(fund_tx, fund_summary, as_of_date)

    output_dir = output_root / file_date
    output_dir.mkdir(parents=True, exist_ok=True)

    price_history.to_csv(output_dir / "fund_price_history.csv", index=False)
    fund_yearly.to_csv(output_dir / "fund_yearly_returns.csv", index=False)
    portfolio_yearly.to_csv(output_dir / "portfolio_yearly_returns.csv", index=False)
    fund_summary.to_csv(output_dir / "fund_investment_summary.csv", index=False)
    portfolio_summary.to_csv(output_dir / "portfolio_investment_summary.csv", index=False)

    return output_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze ETF transactions to compute historical returns and investment insights."
    )
    parser.add_argument(
        "--transactions-file",
        type=Path,
        default=None,
        help="Optional explicit transactions CSV. If omitted, latest file in transactions-data is used.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory root for generated CSV reports.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    tx_file = args.transactions_file or pick_latest_transactions_file(TRANSACTIONS_DIR)
    if not tx_file.exists():
        raise FileNotFoundError(f"Transactions file not found: {tx_file}")

    output_dir = analyze_transactions(tx_file, args.output_dir)

    print(f"Using transactions file: {tx_file}")
    print(f"Saved transactions analytics to: {output_dir}")


if __name__ == "__main__":
    main()

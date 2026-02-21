from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "processed_data"
TX_DATA_DIR = DATA_DIR / "transactions"
FUNDS_LIST_FILE = BASE_DIR / "portfolio-data" / "funds_list.csv"


def list_exposure_tags() -> list[str]:
    if not DATA_DIR.exists():
        return []
    tags = []
    for child in DATA_DIR.iterdir():
        if not child.is_dir() or child.name == "transactions":
            continue
        if (child / "exposure_country.csv").exists():
            tags.append(child.name)
    return sorted(tags, reverse=True)


def list_transactions_tags() -> list[str]:
    if not TX_DATA_DIR.exists():
        return []
    tags = []
    for child in TX_DATA_DIR.iterdir():
        if not child.is_dir():
            continue
        if (child / "portfolio_investment_summary.csv").exists():
            tags.append(child.name)
    return sorted(tags, reverse=True)


def load_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def exposure_data(tag: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = DATA_DIR / tag
    return (
        load_csv(base / "exposure_country.csv"),
        load_csv(base / "exposure_sector.csv"),
        load_csv(base / "exposure_company.csv"),
    )


def transactions_data(tag: str) -> dict[str, pd.DataFrame]:
    base = TX_DATA_DIR / tag
    return {
        "fund_yearly": load_csv(base / "fund_yearly_returns.csv"),
        "portfolio_yearly": load_csv(base / "portfolio_yearly_returns.csv"),
        "fund_summary": load_csv(base / "fund_investment_summary.csv"),
        "portfolio_summary": load_csv(base / "portfolio_investment_summary.csv"),
        "price_history": load_csv(base / "fund_price_history.csv"),
    }


def fund_name_map() -> dict[str, str]:
    if not FUNDS_LIST_FILE.exists():
        return {}
    funds = pd.read_csv(FUNDS_LIST_FILE)
    if "ISIN" not in funds.columns or "Fund name" not in funds.columns:
        return {}
    return dict(zip(funds["ISIN"], funds["Fund name"]))


def show_horizontal_bar(
    data: pd.DataFrame,
    y_col: str,
    x_col: str,
    title: str,
    height: int = 350,
    y_sort: str = "-x",
) -> None:
    if data.empty:
        st.info(f"No data available for: {title}")
        return
    chart = {
        "mark": {"type": "bar"},
        "encoding": {
            "x": {
                "field": x_col,
                "type": "quantitative",
                "title": x_col,
                "axis": {"format": ".2f"},
            },
            "y": {"field": y_col, "type": "nominal", "sort": y_sort, "title": y_col},
            "tooltip": [
                {"field": y_col, "type": "nominal", "title": y_col},
                {"field": x_col, "type": "quantitative", "title": x_col, "format": ".2f"},
            ],
        },
        "height": height,
    }
    st.subheader(title)
    st.vega_lite_chart(data, chart, width='stretch')


def show_sector_donut(data: pd.DataFrame) -> None:
    if data.empty:
        st.info("No sector data available")
        return
    chart = {
        "mark": {"type": "arc", "innerRadius": 60},
        "encoding": {
            "theta": {"field": "Weight", "type": "quantitative"},
            "color": {"field": "sector", "type": "nominal"},
            "tooltip": [
                {"field": "sector", "type": "nominal", "title": "Sector"},
                {"field": "Weight", "type": "quantitative", "title": "Weight", "format": ".2f"},
            ],
        },
    }
    st.subheader("Sector Allocation")
    st.vega_lite_chart(data, chart, width='stretch')


def format_pct(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def main() -> None:
    st.set_page_config(page_title="ETF Portfolio Analyzer", layout="wide")
    st.title("ETF Portfolio Analyzer")
    st.caption("Exposure, performance, and invested-capital insights from processed holdings and transactions data")

    exposure_tags = list_exposure_tags()
    tx_tags = list_transactions_tags()

    with st.sidebar:
        st.header("Controls")
        exposure_tag = st.selectbox(
            "Exposure Snapshot",
            options=exposure_tags,
            index=0 if exposure_tags else None,
            help="From processed_data/<tag>/",
        )
        tx_tag = st.selectbox(
            "Transactions Snapshot",
            options=tx_tags,
            index=0 if tx_tags else None,
            help="From processed_data/transactions/<tag>/",
        )
        top_n = st.slider("Top N items", min_value=5, max_value=30, value=20, step=1)

    tab_exposure, tab_returns, tab_investment = st.tabs(["Exposure", "Returns", "Investment"])

    with tab_exposure:
        if not exposure_tag:
            st.warning("No exposure snapshots found in processed_data.")
        else:
            country, sector, company = exposure_data(exposure_tag)
            st.markdown(f"### Exposure Snapshot: {exposure_tag}")

            col_left, col_right = st.columns(2)
            with col_left:
                show_horizontal_bar(
                    country.head(top_n),
                    y_col="country",
                    x_col="Weight",
                    title=f"Top {top_n} Country Exposures",
                    height=450,
                )
            with col_right:
                show_sector_donut(sector)

            show_horizontal_bar(
                company.head(top_n),
                y_col="securityName",
                x_col="Weight",
                title=f"Top {top_n} Company Exposures",
                height=600,
            )

    with tab_returns:
        if not tx_tag:
            st.warning("No transactions analytics found. Run scripts/transactions_analysis.py first.")
        else:
            tx = transactions_data(tx_tag)
            fund_yearly = tx["fund_yearly"].copy()
            portfolio_yearly = tx["portfolio_yearly"].copy()

            st.markdown(f"### Returns Snapshot: {tx_tag}")

            if not portfolio_yearly.empty:
                show_horizontal_bar(
                    portfolio_yearly.sort_values("Year", ascending=True),
                    y_col="Year",
                    x_col="PortfolioYearlyReturnPct",
                    title="Portfolio Yearly Returns (%)",
                    height=220,
                    y_sort="ascending",
                )

            if not fund_yearly.empty:
                available_years = sorted(fund_yearly["Year"].unique().tolist())
                selected_years = st.multiselect(
                    "Years for fund returns",
                    options=available_years,
                    default=available_years,
                )

                filtered = fund_yearly[fund_yearly["Year"].isin(selected_years)].copy()
                filtered = filtered.sort_values(["Year", "YearlyReturnPct"], ascending=[False, False])

                st.subheader("Fund Yearly Returns Table")
                st.dataframe(
                    filtered,
                    hide_index=True,
                    width='stretch',
                    column_config={
                        "YearlyReturnPct": st.column_config.NumberColumn(format="%.2f%%"),
                        "OpeningPrice": st.column_config.NumberColumn(format="%.4f"),
                        "ClosingPrice": st.column_config.NumberColumn(format="%.4f"),
                    },
                )

                heatmap_data = filtered.pivot_table(
                    index="FundName",
                    columns="Year",
                    values="YearlyReturnPct",
                    aggfunc="mean",
                ).reset_index()
                heatmap_long = heatmap_data.melt(id_vars=["FundName"], var_name="Year", value_name="YearlyReturnPct")
                heatmap_chart = {
                    "mark": {"type": "rect", "tooltip": True},
                    "encoding": {
                        "x": {"field": "Year", "type": "ordinal"},
                        "y": {"field": "FundName", "type": "nominal", "sort": "-x"},
                        "color": {
                            "field": "YearlyReturnPct",
                            "type": "quantitative",
                            "scale": {"scheme": "redyellowgreen"},
                        },
                    },
                    "height": 450,
                }
                st.subheader("Fund Returns Heatmap (%)")
                st.vega_lite_chart(heatmap_long, heatmap_chart, width='stretch')

    with tab_investment:
        if not tx_tag:
            st.warning("No transactions analytics found. Run scripts/transactions_analysis.py first.")
        else:
            tx = transactions_data(tx_tag)
            fund_summary = tx["fund_summary"].copy()
            portfolio_summary = tx["portfolio_summary"].copy()
            price_history = tx["price_history"].copy()

            st.markdown(f"### Investment Snapshot: {tx_tag}")

            if not portfolio_summary.empty:
                p = portfolio_summary.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Net Invested", f"€{p['NetInvested']:,.2f}")
                col2.metric("Current Value", f"€{p['CurrentValue']:,.2f}")
                col3.metric("Total Return", f"€{p['TotalReturn']:,.2f}", delta=format_pct(p["TotalReturnPct"]))
                col4.metric("Money-Weighted Return", format_pct(p["MoneyWeightedReturnPct"]))

            if not fund_summary.empty:
                show_horizontal_bar(
                    fund_summary.head(top_n),
                    y_col="FundName",
                    x_col="CurrentValue",
                    title=f"Top {top_n} Funds by Current Value",
                    height=500,
                )
                show_horizontal_bar(
                    fund_summary.sort_values("TotalReturnPct", ascending=False).head(top_n),
                    y_col="FundName",
                    x_col="TotalReturnPct",
                    title=f"Top {top_n} Funds by Total Return (%)",
                    height=500,
                )

                st.subheader("Fund Investment Summary")
                st.dataframe(
                    fund_summary,
                    hide_index=True,
                    width='stretch',
                    column_config={
                        "NetInvested": st.column_config.NumberColumn(format="€%.2f"),
                        "CurrentValue": st.column_config.NumberColumn(format="€%.2f"),
                        "TotalReturn": st.column_config.NumberColumn(format="€%.2f"),
                        "TotalReturnPct": st.column_config.NumberColumn(format="%.2f%%"),
                        "MoneyWeightedReturnPct": st.column_config.NumberColumn(format="%.2f%%"),
                    },
                )

            if not price_history.empty:
                names = fund_name_map()
                price_history["FundName"] = price_history["ISIN"].map(names).fillna(price_history["ISIN"])
                price_history["Date"] = pd.to_datetime(price_history["Date"], errors="coerce")

                all_funds = sorted(price_history["FundName"].dropna().unique().tolist())
                default_funds = all_funds[: min(5, len(all_funds))]
                selected_funds = st.multiselect(
                    "Funds for price history",
                    options=all_funds,
                    default=default_funds,
                )

                if selected_funds:
                    chart_df = price_history[price_history["FundName"].isin(selected_funds)].copy()
                    line_chart = {
                        "mark": {"type": "line", "tooltip": True},
                        "encoding": {
                            "x": {"field": "Date", "type": "temporal"},
                            "y": {"field": "UnitPrice", "type": "quantitative"},
                            "color": {"field": "FundName", "type": "nominal"},
                        },
                        "height": 420,
                    }
                    st.subheader("Transaction-Implied Unit Price History")
                    st.vega_lite_chart(chart_df, line_chart, width='stretch')


if __name__ == "__main__":
    main()

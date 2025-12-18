import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'processed_data')

def get_available_dates():
    if not os.path.exists(DATA_DIR):
        return []
    # List directories in processed_data
    return sorted([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))], reverse=True)

def load_data(date_str, filename):
    path = os.path.join(DATA_DIR, date_str, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

# Initialize App
app = dash.Dash(__name__)
app.title = "ETF Portfolio Analyzer"

available_dates = get_available_dates()
default_date = available_dates[0] if available_dates else None

# --- Layout ---

app.layout = html.Div([
    html.H1("ETF Portfolio Dashboard", style={'textAlign': 'center'}),
    
    html.Div([
        html.Label("Select Portfolio Date:"),
        dcc.Dropdown(
            id='date-dropdown',
            options=[{'label': d, 'value': d} for d in available_dates],
            value=default_date,
            clearable=False
        )
    ], style={'width': '30%', 'margin': 'auto', 'paddingBottom': '20px'}),
    
    html.Div([
        html.Div([
            dcc.Graph(id='graph-country')
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(id='graph-sector')
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ]),
    
    html.Div([
        dcc.Graph(id='graph-company', style={'height': '800px'})
    ], style={'width': '100%', 'marginTop': '20px'})
])

@app.callback(
    [Output('graph-country', 'figure'),
     Output('graph-sector', 'figure'),
     Output('graph-company', 'figure')],
    [Input('date-dropdown', 'value')]
)
def update_graphs(selected_date):
    if not selected_date:
        return {}, {}, {}

    df_country = load_data(selected_date, 'exposure_country.csv')
    df_sector = load_data(selected_date, 'exposure_sector.csv')
    df_company = load_data(selected_date, 'exposure_company.csv')

    # 1. Country Exposure (Top 20)
    if not df_country.empty:
        fig_country = px.bar(
            df_country.head(20), 
            x='country', 
            y='Weight', 
            title=f'Top 20 Country Exposures ({selected_date})',
            labels={'country': 'Country', 'Weight': 'Portfolio Weight (%)'},
            text_auto='.2f'
        )
        fig_country.update_layout(xaxis_tickangle=-45)
    else:
        fig_country = {}

    # 2. Sector Exposure
    if not df_sector.empty:
        fig_sector = px.pie(
            df_sector, 
            values='Weight', 
            names='sector', 
            title=f'Sector Allocation ({selected_date})',
            hole=0.4
        )
        fig_sector.update_traces(textposition='inside', textinfo='percent+label')
    else:
        fig_sector = {}

    # 3. Company Exposure (Top 20)
    if not df_company.empty:
        fig_company = px.bar(
            df_company.head(20), 
            x='Weight', 
            y='securityName', 
            orientation='h',
            title=f'Top 20 Company Exposures ({selected_date})',
            labels={'securityName': 'Company', 'Weight': 'Portfolio Weight (%)'},
            text_auto='.2f'
        )
        fig_company.update_layout(yaxis={'categoryorder':'total ascending'})
    else:
        fig_company = {}
        
    return fig_country, fig_sector, fig_company

if __name__ == '__main__':
    print("Starting dashboard on http://127.0.0.1:8050/")
    app.run(debug=True)

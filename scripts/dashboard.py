import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'processed_data')

def load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

# Load datasets
df_country = load_data('exposure_country.csv')
df_sector = load_data('exposure_sector.csv')
df_company = load_data('exposure_company.csv')

# Initialize App
app = dash.Dash(__name__)
app.title = "ETF Portfolio Analyzer"

# --- Figures ---

# 1. Country Exposure (Top 20)
fig_country = px.bar(
    df_country.head(20), 
    x='country', 
    y='Weight', 
    title='Top 20 Country Exposures',
    labels={'country': 'Country', 'Weight': 'Portfolio Weight (%)'},
    text_auto='.2f'
)
fig_country.update_layout(xaxis_tickangle=-45)

# 2. Sector Exposure
fig_sector = px.pie(
    df_sector, 
    values='Weight', 
    names='sector', 
    title='Sector Allocation',
    hole=0.4
)
fig_sector.update_traces(textposition='inside', textinfo='percent+label')

# 3. Company Exposure (Top 20)
fig_company = px.bar(
    df_company.head(20), 
    x='Weight', 
    y='securityName', 
    orientation='h',
    title='Top 20 Company Exposures',
    labels={'securityName': 'Company', 'Weight': 'Portfolio Weight (%)'},
    text_auto='.2f'
)
fig_company.update_layout(yaxis={'categoryorder':'total ascending'})

# --- Layout ---

app.layout = html.Div([
    html.H1("ETF Portfolio Dashboard", style={'textAlign': 'center'}),
    
    html.Div([
        html.Div([
            dcc.Graph(figure=fig_country)
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            dcc.Graph(figure=fig_sector)
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ]),
    
    html.Div([
        dcc.Graph(figure=fig_company, style={'height': '800px'})
    ], style={'width': '100%', 'marginTop': '20px'})
])

if __name__ == '__main__':
    print("Starting dashboard on http://127.0.0.1:8050/")
    app.run(debug=True)

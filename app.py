from dash import Dash, html, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px

# Load data
file = 'fund_241228.csv'
path = 'pages'
df_prc = pd.read_csv(
    f'{path}/{file}',
    parse_dates=['date'],
    dtype={'ticker': str},
    index_col=['group', 'ticker', 'date']
)

groups = df_prc.index.get_level_values('group').unique()
default_group = groups[-1]
groups = [{'label': f'TDF{x}', 'value': x} for x in groups]

# Prepare the JSON data
df_json = df_prc.reset_index().to_json(date_format='iso', orient='records')

# Initialize the Dash app
app = Dash(__name__)

app.layout = html.Div([
    dcc.Dropdown(
        id='group-dropdown',
        options=groups,
        value=default_group,  # Default value
        clearable=False,
        style={'width': '50%'}
    ),
    dcc.Graph(id='price-plot'),
    # Store DataFrame in JSON format
    dcc.Store(id='price-data', data=df_json)
])

# Define client-side callback
app.clientside_callback(
    """
    function(group, jsonData) {
        // Parse the JSON data
        const data = JSON.parse(jsonData);
        
        // Filter the data for the selected group
        const filteredData = data.filter(row => row.group === group);

        // Organize data by ticker
        const tickerData = {};
        filteredData.forEach(row => {
            if (!tickerData[row.ticker]) {
                tickerData[row.ticker] = { x: [], y: [] };
            }
            tickerData[row.ticker].x.push(row.date);
            tickerData[row.ticker].y.push(row.price);
        });

        // Prepare traces for the plot
        const traces = Object.keys(tickerData).map(ticker => ({
            x: tickerData[ticker].x,
            y: tickerData[ticker].y,
            type: 'scatter',
            mode: 'lines',
            name: ticker
        }));

        // Return the figure object
        return {
            data: traces,
            layout: {
                title: `Price Plot for Group ${group}`,
                xaxis: { title: 'Date' },
                yaxis: { title: 'Price' }
            }
        };
    }
    """,
    Output('price-plot', 'figure'),
    Input('group-dropdown', 'value'),
    Input('price-data', 'data')
)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)

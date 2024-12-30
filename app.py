from dash import Dash, html, dcc, Output, Input
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import dash_daq as daq
import json

# Load data
file = 'fund_241229.csv'
path = '.'
#path = '.'
df_prc = pd.read_csv(
    f'{path}/{file}',
    parse_dates=['date'],
    dtype={'ticker': str},
    index_col=['group', 'ticker', 'date']
)

file = 'fund_name_241230.csv'
fund_name = pd.read_csv(f'{path}/{file}', dtype={'ticker': str}, index_col=[0])
fund_name = fund_name.iloc[:,0].to_dict()

groups = df_prc.index.get_level_values('group').unique()
default_group = 2030
groups = [{'label': f'TDF{x}', 'value': x} for x in groups]

# Initialize the Dash app
external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(__name__, title="달달펀드",
           external_stylesheets=external_stylesheets)

app.layout = dbc.Container([
    html.Br(),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id='group-dropdown',
                options=groups,
                value=default_group,
                clearable=False,
            ),
            width=3
        ),
        dbc.Col(
            daq.BooleanSwitch(
                id='compare-boolean-switch',
                on=False
            ),
            width="auto"),
        dbc.Col(
            daq.BooleanSwitch(
                id='cost-boolean-switch',
                on=False
            ),
            width="auto"),
    ],
        justify="center",
        align="center",
        className="mb-3"
    ),
    dbc.Row(dcc.Graph(id='price-plot')),
    dbc.Row(dcc.Graph(id='return-plot')),
    html.Br(),
    dcc.Store(id='price-data'),
    dbc.Tooltip(
        '상대 비교',
        target='compare-boolean-switch',
        placement='bottom'
    ),
    dbc.Tooltip(
        '수수료 적용',
        target='cost-boolean-switch',
        placement='bottom'
    )
])

# Preprocess data to make it JSON-serializable and store it in a JavaScript variable
preprocessed_data = {}
df_prc.columns = ['수수료 적용 전', '수수료 적용 후']
cols = df_prc.columns
date_format = '%Y-%m-%d'
for group in groups:
    group_value = group['value']
    data = {'columns': list(cols), 'default': {}, 'compare': {}}
    start = None
    for col in cols:
        df_p = df_prc.loc[group_value, col].unstack('ticker').sort_index()
        df_p.columns = [fund_name[x] for x in df_p.columns]
        df_r = df_p.apply(lambda x: x.dropna().iloc[-1]/x.dropna().iloc[0]-1).mul(100).to_frame(col)
        data['default'][col] = {
            'history': df_p.round().to_dict('records'),
            'index': df_p.index.strftime(date_format).tolist(),
            'return': df_r.round(1).to_dict('records'),
            'ticker': df_r.index.tolist()
        }
        if start is None:
            start = df_p.apply(lambda x: x[x.notna()].index.min()).max()
        normalized_df = df_p.apply(lambda x: x / x.loc[start] * 1000).loc[start:]
        df_r_n = normalized_df.apply(lambda x: x.dropna().iloc[-1]/x.dropna().iloc[0]-1).mul(100).to_frame(col)
        data['compare'][col] = {
            'history': normalized_df.round().to_dict('records'),
            'index': normalized_df.index.strftime(date_format).tolist(),
            'return': df_r_n.round(1).to_dict('records'),
            'ticker': df_r.index.tolist()
        }
    preprocessed_data[group_value] = data

# Inject preprocessed data as JSON in the client
preprocessed_data_json = json.dumps(preprocessed_data)
app.index_string = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
        {{%css%}}
    </head>
    <body>
        <script>
            var preprocessedData = {preprocessed_data_json};
        </script>
        {{%app_entry%}}
        {{%config%}}
        {{%scripts%}}
        {{%renderer%}}
    </body>
</html>
"""


# Client-side callback for price data
app.clientside_callback(
    """
    function(group) {
        return preprocessedData[group];
    }
    """,
    Output('price-data', 'data'),
    Input('group-dropdown', 'value')
)


app.clientside_callback(
    """
    function(data, cost, compare) {
        if (!data || !data.columns) {
            return {data: [], layout: {title: 'No Data Available', height: 300}};
        }

        const cols = data.columns; // Columns: ['price', 'price_after_fees']
        const col = cost ? cols[1] : cols[0]; // Select the column based on cost
        const kind = compare ? 'compare' : 'default'; // Default or compare data
        const dat = data[kind][col];

        if (!dat || !dat.history || !dat.index) {
            return {data: [], layout: {title: 'No Data Available', height: 300}};
        }

        // Prepare data for each ticker
        const traces = Object.keys(dat.history[0]).map(ticker => {
            const yValues = dat.history.map(row => row[ticker]);
            return {
                x: dat.index,        // Dates from the index
                y: yValues,          // Price history for each ticker
                type: 'scatter',
                mode: 'lines',
                name: ticker        // Ticker as the legend name
            };
        });

        // Title logic
        const titleBase = '펀드 가격 추이';
        const titleComp = compare ? '상대 가격' : '펀드별 최근 결산 기준가격으로 계산';
        const titleCost = cost ? '수수료 적용' : null;

        let title = `${titleBase} (${titleComp}`;
        title = titleCost ? `${title}, ${titleCost})` : `${title})`;

        return {
            data: traces,
            layout: {
                title: { text: title, x: 0 },
                //xaxis: { title: 'Date' },
                yaxis: { title: '기준가격' },
                height: 600,
                hovermode: 'x'
            }
        };
    }
    """,
    Output('price-plot', 'figure'),
    Input('price-data', 'data'),
    Input('cost-boolean-switch', 'on'),
    Input('compare-boolean-switch', 'on')
)


app.clientside_callback(
    """
    function(data, cost, compare) {
        if (!data || !data.columns) {
            return {data: [], layout: {title: 'No Data Available', height: 300}};
        }

        const cols = data.columns; // Columns: ['price', 'price_after_fees']
        const sel = cost ? cols[1] : cols[0]; // Selected column based on cost
        const kind = compare ? 'compare' : 'default'; // Default or compare data
        const dat = data[kind];

        if (!dat[cols[0]] || !dat[cols[1]] || !dat[cols[0]].return || !dat[cols[0]].ticker) {
            return {data: [], layout: {title: 'No Data Available', height: 300}};
        }

        const tickers = dat[cols[0]].ticker; // Tickers for x-axis
        const returnPrice = dat[cols[0]].return; // Returns for 'price'
        const returnFees = dat[cols[1]].return; // Returns for 'price_after_fees'

        // Generate bar traces for both columns, always in the same order
        const traces = [
            {
                x: tickers,
                y: returnPrice.map(r => r[cols[0]]),
                type: 'bar',
                name: cols[0], // Label for 'price'
                opacity: cost ? 0.3 : 0.6, // Fade when cost is True
                marker: {
                    line: { color: 'black', width: 1 }
                }
            },
            {
                x: tickers,
                y: returnFees.map(r => r[cols[1]]),
                type: 'bar',
                name: cols[1], // Label for 'price_after_fees'
                opacity: cost ? 0.6 : 0.3, // Fade when cost is False
                marker: {
                    line: { color: 'black', width: 1 }
                }
            }
        ];

        // Set title dynamically based on compare switch
        let title;
        if (compare) {
            const dates = dat[sel].index;
            const dt0 = new Date(Math.min(...dates.map(d => new Date(d).getTime()))).toISOString().slice(0, 10);
            const dt1 = new Date(Math.max(...dates.map(d => new Date(d).getTime()))).toISOString().slice(0, 10);
            title = `펀드 수익률 (${dt0} ~ ${dt1})`;
        } else {
            title = '펀드 수익률 (펀드별 설정일 이후)';
        }

        return {
            data: traces,
            layout: {
                title: { text: title, x: 0 }, // Align title to the left
                //xaxis: { title: 'Tickers' },
                yaxis: { title: '수익률(%)' },
                barmode: 'group', // Grouped bar chart
                height: 400,
                hovermode: 'x',
                //hovertemplate='%{y:.0f}%'
            }
        };
    }
    """,
    Output('return-plot', 'figure'),
    Input('price-data', 'data'),
    Input('cost-boolean-switch', 'on'),
    Input('compare-boolean-switch', 'on')
)


if __name__ == '__main__':
    app.run_server(debug=False)
from dash import Dash, html, dcc, Output, Input
import pandas as pd
import dash_bootstrap_components as dbc
import dash_daq as daq
import json

file_prc = 'fund_monthly_241229.csv'
file_name = 'fund_name_241230.csv'
path = '.'

email_info = 'leebaekku209@gmail.com'
default_group = 2030
base_prc = 1000
date_format = '%Y-%m-%d'
months_in_year = 12
cols_prc = ['수수료 적용 전', '수수료 적용 후']


# Load price data
df_prc = pd.read_csv(
    f'{path}/{file_prc}',
    parse_dates=['date'],
    dtype={'ticker': str},
    index_col=['group', 'ticker', 'date']
)

# Load fund names
fund_name = pd.read_csv(f'{path}/{file_name}', dtype={'ticker': str}, index_col=[0])
fund_name = fund_name.iloc[:,0].to_dict()

groups = df_prc.index.get_level_values('group').unique()
groups = [{'label': f'TDF{x}', 'value': x} for x in groups]

# Initialize the Dash app
external_stylesheets = [dbc.themes.CERULEAN, 
                        #dbc.themes.BOOTSTRAP,
                        dbc.icons.FONT_AWESOME,
                        dbc.icons.BOOTSTRAP]
app = Dash(__name__, title="달달펀드",
           external_stylesheets=external_stylesheets)

disclaimer = """
본 사이트는 투자 권유를 제공하지 않으며, 제공되는 정보의 정확성과 완전성을 보장하지 않습니다. 수수료와 세금은 수익률에 영향을 미칠 수 있으며, 투자 결정 및 그에 따른 결과는 전적으로 투자자 본인의 책임입니다.
"""

tab_info = html.Div([
    html.P(),
    dbc.Alert([
        html.I(className="bi bi-info-circle-fill me-2"),
        disclaimer,
        ],
        color="info",
        className="d-flex align-items-center",
    ),
    #html.P(disclaimer),
    html.P([
        #html.Div('문의'),
        html.I(className="fa-solid fa-envelope", style={"margin-right": "10px"}),
        html.A(email_info, href=f"mailto:{email_info}?Subject=달달펀드:문의")
    ])
], style={'fontSize': 14})

tab_topic = '테스트'

tabs_contents = [
    dbc.Tab(dcc.Graph(id='price-plot'), label='가격'),
    dbc.Tab(dcc.Graph(id='return-plot'), label='수익률'),
    dbc.Tab(tab_topic, label='토픽'),
    dbc.Tab(tab_info, label='정보')
]
tabs = dbc.Tabs(tabs_contents)

app.layout = dbc.Container([
    html.Br(),
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id='group-dropdown',
                options=groups,
                value=default_group,
                clearable=False,
                searchable=False
            ),
            #width=3
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
    dbc.Row(tabs),
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
#], fluid=True)  # Full-width container
])


# Preprocess data to make it JSON-serializable and store it in a JavaScript variable
preprocessed_data = {}
df_prc.columns = cols_prc
cols = df_prc.columns
for group in groups:
    group_value = group['value']
    data = {'columns': list(cols), 'default': {}, 'compare': {}}
    start = None
    for col in cols:
        df_p = df_prc.loc[group_value, col].unstack('ticker').sort_index()
        df_p.columns = [fund_name[x] for x in df_p.columns]
        
        sr_n = df_p.apply(lambda x: x.dropna().count()) # num of months for each ticker
        df_r = (df_p.apply(lambda x: x.dropna().iloc[-1]/x.dropna().iloc[0]-1) # total return
                .to_frame('ttr').join(sr_n.rename('n'))
                .apply(lambda x: (1+x['ttr']) ** (months_in_year/x['n']) - 1, axis=1) # CAGR
                .mul(100).to_frame(col))
        
        data['default'][col] = {
            'history': df_p.round().to_dict('records'),
            'index': df_p.index.strftime(date_format).tolist(),
            'return': df_r.round(1).to_dict('records'),
            'ticker': df_r.index.tolist()
        }
        if start is None:
            start = df_p.apply(lambda x: x[x.notna()].index.min()).max()
        normalized_df = df_p.apply(lambda x: x / x.loc[start] * base_prc).loc[start:]
        
        sr_n = normalized_df.apply(lambda x: x.dropna().count()) # num of months for each ticker
        df_r_n = (normalized_df.apply(lambda x: x.dropna().iloc[-1]/x.dropna().iloc[0]-1) # total return
                  .to_frame('ttr').join(sr_n.rename('n'))
                  .apply(lambda x: (1+x['ttr']) ** (months_in_year/x['n']) - 1, axis=1) # CAGR
                  .mul(100).to_frame(col))

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
                name: ticker,        // Ticker as the legend name
                showlegend: true
            };
        });

        // Title logic
        const titleBase = '펀드 가격 추이';
        const titleComp = compare ? '상대 가격' : '펀드별 최근 결산 기준가격';
        const titleCost = cost ? '수수료 적용' : null;

        let title = `${titleBase} (${titleComp}`;
        title = titleCost ? `${title}, ${titleCost})` : `${title})`;

        const layout = {
            title: { text: title, x: 0 },
            hovermode: 'x',
            yaxis: { title: '가격' },
            xaxis: {
                rangeselector: {
                    buttons: [
                        {
                            count: 3,
                            label: "3y",
                            step: "year",
                            stepmode: "backward"
                        },
                        {
                            step: "all",
                            label: "All"
                        }
                    ]
                },
                rangeslider: {
                    visible: true
                },
                type: "date"
            },
            responsive: true
        };

        // Detect the window width (client-side)
        const viewportWidth = window.innerWidth;

        // Disable legend for mobile devices
        if (viewportWidth < 768) {
            layout.legend = {visible: false};
        }

        return {
            data: traces,
            layout: layout
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
            title = `펀드 연평균 수익률 (${dt0} ~ ${dt1})`;
        } else {
            title = '펀드 연평균 수익률 (펀드별 설정일 이후)';
        }

        const layout = {
            title: { text: title, x: 0 }, // Align title to the left
            //xaxis: { title: 'Tickers' },
            yaxis: { title: '연평균 수익률 (%)' },
            barmode: 'group', // Grouped bar chart
            //height: 400,
            hovermode: 'x',
            //hovertemplate='%{y:.0f}%',
            responsive: true
        };

        // Detect the window width (client-side)
        const viewportWidth = window.innerWidth;

        // Disable legend for mobile devices
        if (viewportWidth < 768) {
            layout.legend = {visible: false};
        }

        return {
            data: traces,
            layout: layout
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

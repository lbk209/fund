from dash import Dash, html, dcc, Output, Input
import pandas as pd
import dash_bootstrap_components as dbc
import dash_daq as daq
import json
from contents import contents, break_line, extract_topics

file_prc = 'fund_monthly_241229.csv'
file_name = 'fund_name_241230.csv'
path = '.'

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

# stats for table
calc_cagr = lambda year: (df_prc['price_after_fees']
                          .groupby('ticker', group_keys=False).apply(lambda x: x.pct_change(year*12).dropna())
                          .groupby('group').agg(['mean', 'std'])
                          .mul(100).round(1)
                          .apply(lambda x: f"{x['mean']:.1f} ± {x['std']:.1f}", axis=1)
                          #.apply(lambda x: f"{x['mean']:.1%} ± {x['std']:.1%}", axis=1)
                         )
df_table = (df_prc.groupby('group').apply(lambda x: x.index.get_level_values(1).nunique()).to_frame('n')
              .join(calc_cagr(1).rename('1y')).join(calc_cagr(3).rename('3y')))
df_table.index = [f'TDF{x}' for x in df_table.index]
df_table = df_table.reset_index()
df_table.columns = ['구분', '펀드 개수', '1년 수익률 ± 표준편차 (%)', '3년 수익률 ± 표준편차 (%)']

# Initialize the Dash app
external_stylesheets = [dbc.themes.CERULEAN, 
                        #dbc.themes.BOOTSTRAP,
                        dbc.icons.FONT_AWESOME,
                        dbc.icons.BOOTSTRAP]


app = Dash(__name__, title="달달펀드",
           external_stylesheets=external_stylesheets)

style_heading={'color':'slategray', 'font-weight':'bold'}

# footer
footer = html.Footer(
    html.Small([
    html.I(className="fa-regular fa-copyright"),
    '2025 달달펀드'
]), style={'textAlign': 'right', 'margin-top': '20px'})

# topics
topics = [extract_topics(x, style_heading=style_heading) for x in contents['topics']]

# additional contents
table = dbc.Table.from_dataframe(df_table, size='sm', striped=True, bordered=True,
                                 style={'width':'100%', 'text-align':'center', 'fontSize': 14})
cgi = {'표1: TDF 보유 기간에 따른 과거 수익률':table}
table1 = extract_topics(cgi, item=html.Div, 
                        style_content={'margin-top': '20px', 'line-height': '150%'})

#image = html.Img(src='/assets/contents/favicon.ico') # failed
#image = html.Img(src='/assets/favicon.ico') # success
#image = html.Img(src="/assets/tdf_selected.png")
image = html.Img(src="tdf_selected.png")
cgi = {'그림1: 3년 후 손해 확률 3% 미만 TDF (베이지안 추정 적용)':image}
image1 = extract_topics(cgi, item=html.Div, 
                        style_content={'margin-top': '20px', 'line-height': '150%'})

tab_topic = html.Div(
    [topics[0], topics[1], table1, image1],
)

# info
info = contents['info']
tab_info = html.Div([
    html.P(),
    html.P('다달이 전하는 펀드 투자 정보', style=style_heading),
    html.Div(break_line(info['about'], html.P), style={'line-height': '100%'}),
    html.Div([
        dbc.Alert([
            html.I(className="bi bi-info-circle-fill me-2"),
            info['disclaimer'],
            ],
            color="info",
            className="d-flex align-items-center",
        ),
        html.P([
            html.I(className="fa-regular fa-envelope", title='문의', style={"margin-right": "10px"}),
            html.A(info['email'], href=f"mailto:{info['email']}?Subject=달달펀드:문의")
        ], style={'textAlign': 'right'})
    ], style={'fontSize': 14})
    #])
])

# tabs
tabs_contents = [
    dbc.Tab(dcc.Graph(id='price-plot'), label='가격'),
    dbc.Tab(dcc.Graph(id='return-plot'), label='수익률'),
    dbc.Tab(tab_topic, label='토픽'),
    dbc.Tab(tab_info, label='정보')
]
tabs = dbc.Tabs(tabs_contents)

# layout
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
    dbc.Row(footer),
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

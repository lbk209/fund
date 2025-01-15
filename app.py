from dash import Dash, html, dcc, Output, Input
import pandas as pd
import dash_bootstrap_components as dbc
import dash_daq as daq
import json
from ddf_utils import break_line, extract_topics
from contents_info import info
from contents_topic_250109 import topics, images

file_prc = 'fund_monthly_241229.csv'
file_name = 'fund_name_241230.csv'
file_dst = 'fund_density_ret3y_250113.json'
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
fund_name = fund_name.squeeze().to_dict()

# Load density
with open(f'{path}/{file_dst}', "r") as f:
    data_density_json = f.read()  # Read raw JSON string directly

# create dropdown options of TDF groups
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
topics = [extract_topics(x, style_heading=style_heading) for x in topics]
images = [extract_topics(x, style_heading=style_heading, item=html.P) for x in images]

# table
table = dbc.Table.from_dataframe(df_table, size='sm', striped=True, bordered=True,
                                 style={'width':'100%', 'text-align':'center', 'fontSize': 14})
cgi = {'표1: TDF 보유 기간에 따른 과거 수익률':table}
table1 = extract_topics(cgi, item=html.Div, 
                        style_content={'margin-top': '20px', 'line-height': '150%'})



tab_topic = html.Div(
    [topics[0], topics[1], table1, images[0], images[1]],
)

# notice
tab_notice = html.Div(
    children=[
        dcc.Store(id="load-giscus", data=1),  # Trigger the clientside callback on initial load
        html.Div(className="giscus"),  # Placeholder for Giscus
    ]
    , style={'margin-top': '20px'}
)

# info
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
    dbc.Tab(dcc.Graph(id='density-plot'), label='추정', 
                  # add tab_id & new badge for new tab
                  tab_id='tab_new', label_class_name="tab-label new-badge-label"), 
    dbc.Tab(tab_topic, label='토픽'),
    dbc.Tab(tab_notice, label='알림'),
    dbc.Tab(tab_info, label='정보')
]
tabs = dbc.Tabs(tabs_contents, id='tabs')

# layout
app.layout = dbc.Container([
    html.Br(),
    dbc.Stack([
        html.Div(
            dcc.Dropdown(
                id='group-dropdown',
                options=groups,
                value=default_group,
                clearable=False,
                searchable=False
            ), style={'min-width':'50%', 'max-width':'100%'}
        ),
        daq.BooleanSwitch(
            id='compare-boolean-switch',
            on=False
        ),
        daq.BooleanSwitch(
            id='cost-boolean-switch',
            on=False
        ),
        dcc.Clipboard(
            id='ticker-copy',
            target_id="ticker-textarea",
            style={
                "display": "inline-block",
                "fontSize": 25,
                "color": "darkgray",  # Default icon color
                "cursor": "pointer",  # Pointer cursor for better UX
                #"verticalAlign": "bottom",
            },
        ),
    ],
        #justify="start", # horizondal
        #align="center", # vertical
        direction="horizontal",
        gap=2,
        className="mb-3"
    ),
    dbc.Row(tabs),
    dbc.Row(footer),
    html.Br(),
    dcc.Store(id='price-data'),
    dcc.Store(id='density-data'),
    dcc.Textarea(
        id="ticker-textarea",
        hidden='hidden'
    ),
    dbc.Tooltip(
        '상대 비교',
        target='compare-boolean-switch',
        placement='bottom'
    ),
    dbc.Tooltip(
        '수수료 적용',
        target='cost-boolean-switch',
        placement='bottom'
    ),
    dbc.Tooltip(
        '펀드코드 복사',
        target='ticker-copy',
        placement='bottom'
    ),
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
    # add fund name to ticker for ref
    tickers = df_prc.loc[group_value].index.get_level_values('ticker').unique()
    names = [f'{k}:{v}' for k,v in fund_name.items() if k in tickers]
    data['name'] = '\n'.join(names)
    # save data for group_value
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
            var preprocessedDensity = {data_density_json};
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

# update ticker & name for copy
app.clientside_callback(
    """
    function(data) {
        return data.name;
    }
    """,
    Output('ticker-textarea', 'value'),
    Input('price-data', 'data')
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
            legend: {tracegroupgap: 1},  // Set the space between legend lines
            responsive: true,
        };

        // Detect the window width (client-side)
        const viewportWidth = window.innerWidth;
        if (viewportWidth < 768) {
            // Adjust legend position for mobile devices
            layout.legend = {
                orientation: 'h',  // Horizontal legend
                x: 0,              // Align legend to the left
                y: -0.8,           // Position legend below the plot
                xanchor: 'left',   // Anchor legend's x position to the left
                yanchor: 'top',    // Anchor legend's y position to the top
            };
            layout.yaxis = {automargin: true,};
            layout.margin = {
                //l: layout.margin?.l || 10,  // Left margin
                l: 0,
                r: 0,  // Right margin
                //t: layout.margin?.t || 0,  // Preserve the top margin if set, or default to 0
                //b: layout.margin?.b || 0   // Preserve the bottom margin if set, or default to 0
            };
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
        if (viewportWidth < 768) {
            layout.legend = {visible: false};
            layout.yaxis = {automargin: true,};
            layout.margin = {
                //l: layout.margin?.l || 10,  // Left margin
                l: 0,
                r: 0,  // Right margin
                //t: layout.margin?.t || 0,  // Preserve the top margin if set, or default to 0
                //b: layout.margin?.b || 0   // Preserve the bottom margin if set, or default to 0
            };
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


# Define clientside callback to load and initialize Giscus
app.clientside_callback(
    """
    function(data) {
        if (!data) return;  // Do nothing if data hasn't been triggered

        // Check if Giscus script is already loaded
        if (!document.querySelector('script[src="https://giscus.app/client.js"]')) {
            // Create the Giscus script element
            var script = document.createElement('script');
            script.src = "https://giscus.app/client.js";
            script.setAttribute("data-repo", "lbk209/fund");
            script.setAttribute("data-repo-id", "R_kgDONicCMA");
            script.setAttribute("data-category", "Announcements");
            script.setAttribute("data-category-id", "DIC_kwDONicCMM4Cluz9");
            script.setAttribute("data-mapping", "pathname");
            script.setAttribute("data-strict", "0");
            script.setAttribute("data-reactions-enabled", "1");
            script.setAttribute("data-emit-metadata", "0");
            script.setAttribute("data-input-position", "bottom");
            script.setAttribute("data-theme", "light");
            script.setAttribute("data-lang", "ko");
            script.setAttribute("crossorigin", "anonymous");
            script.async = true;

            // Append the script to the body
            document.body.appendChild(script);

            // Re-initialize Giscus when the script is loaded
            script.onload = function() {
                var event = new Event("giscus:reset");
                document.querySelector(".giscus").dispatchEvent(event);
            };
        } else {
            // If script is already loaded, just reset Giscus
            var event = new Event("giscus:reset");
            document.querySelector(".giscus").dispatchEvent(event);
        }

        return null;
    }
    """,
    Output("load-giscus", "data"),
    Input("load-giscus", "data"),
)

# callbacks for density

app.clientside_callback(
    """
    function(at, cost, compare) {
        if (at === "tab_new") {
            return [true, false];
        } else {
            return [cost, compare];
        }
    }
    """,
    [Output('cost-boolean-switch', 'on'), Output('compare-boolean-switch', 'on')],
    [Input("tabs", "active_tab"), Input('cost-boolean-switch', 'on'), Input('compare-boolean-switch', 'on')]
)

app.clientside_callback(
    """
    function(group) {
        return preprocessedDensity[group];
    }
    """,
    Output('density-data', 'data'),
    Input('group-dropdown', 'value')
)

app.clientside_callback(
    """
    function(data) {
        if (!data || !data.density) {
            return { 'data': [] };
        }

        const var_name = data.var_name;
        const hdi_prob = data.hdi_prob;
        const hdi_lines = data.interval;
        const density = data.density;
        const x = data.x;
        
        //const title = `Density of ${var_name.toUpperCase()} (with ${hdi_prob * 100}% Interval)`;
        const title_xaxis = '3-year rate of return'
        const title = `Density of 3-Year Return (with ${hdi_prob * 100}% Interval)`;

        let traces = [];
        let tickers = Object.keys(density[0]);

        // plotly.express.colors.qualitative.D3
        const colorPalette = ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF'];
        let colorIndex = 0;

        // Convert density data into a format suitable for Plotly
        tickers.forEach(ticker => {
            let y = density.map(d => d[ticker]);  // Extract density values for each ticker
            let color = colorPalette[colorIndex % colorPalette.length];
            const vals = hdi_lines[ticker];
            traces.push({
                x: x,
                y: y,
                type: 'scatter',
                mode: 'lines',
                name: ticker,
                line: { color: color },
                legendgroup: ticker,  // Group density line with its corresponding HDI line
                hovertemplate: `${vals.x[0].toFixed(3)} ~ ${vals.x[1].toFixed(3)} :${ticker.substring(0, 10)}<extra></extra>`,
            });

            // Store color for HDI line matching
            colorIndex++;
        });

        // Process HDI lines and add to plot
        for (const name in hdi_lines) {
            const vals = hdi_lines[name];
            let color = colorPalette[tickers.indexOf(name) % colorPalette.length];

            traces.push({
                x: vals.x,
                y: vals.y,
                mode: 'lines+markers',
                line: { color: color, width: 5 },
                marker: { size: 10, symbol: 'line-ns-open' },
                opacity: 0.3,
                //name: name,
                showlegend: false,    // Do not display in the legend
                //showlegend: true,
                legendgroup: name,    // Group HDI line with the corresponding density
                hoverinfo: 'skip',
                //hovertemplate: `${vals.x[0].toFixed(3)} ~ ${vals.x[1].toFixed(3)} :${name}<extra></extra>`,
            });
        }

        const layout = {
            title: title,
            xaxis: { title: title_xaxis },
            yaxis: { title: '', showticklabels: false },
            hovermode: 'x unified',
            hoverlabel: {bgcolor: "rgba(255, 255, 255, 0.8)"},
            legend: {tracegroupgap: 1},  // Set the space between legend lines
        }

        // Detect the window width (client-side)
        const viewportWidth = window.innerWidth;

        // Adjust legend position for mobile devices
        if (viewportWidth < 768) {
            layout.legend = {
                orientation: 'h',  // Horizontal legend
                x: 0,              // Align legend to the left
                y: -1.2,           // Position legend below the plot
                xanchor: 'left',   // Anchor legend's x position to the left
                yanchor: 'top',    // Anchor legend's y position to the top
            };
            //layout.yaxis = {automargin: true,};
            layout.margin = {
                //l: layout.margin?.l || 10,  // Left margin
                l: 0,
                r: 0,  // Right margin
                //t: layout.margin?.t || 0,  // Preserve the top margin if set, or default to 0
                //b: layout.margin?.b || 0   // Preserve the bottom margin if set, or default to 0
            };
        }

        // Format the figure
        return {
            data: traces,
            layout: layout
        };
    }
    """,
    Output('density-plot', 'figure'),
    Input('density-data', 'data')
)

if __name__ == '__main__':
    app.run_server(debug=False)
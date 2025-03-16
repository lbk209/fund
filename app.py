from dash import Dash, html, dcc, Output, Input, State
import pandas as pd
import dash_bootstrap_components as dbc
import dash_daq as daq
import json
from ddf_utils import break_line, extract_topics
from contents_info import info
from contents_topic_250204 import topics, images

external_stylesheets = [dbc.themes.CERULEAN, 
                        #dbc.themes.BOOTSTRAP,
                        dbc.icons.FONT_AWESOME,
                        dbc.icons.BOOTSTRAP]

style_heading={'color':'slategray', 'font-weight':'bold'}

default_group = '자산'
base_prc = 1000
date_format = '%Y-%m-%d'
months_in_year = 12
cols_prc = {
    'price': '수수료 적용 전', 
    'price_after_fees': '수수료 적용 후'
}
category = {
    'name': '펀드',
    'seller': '판매',
    'account': '계좌',
    'manager': '운용',
    'asset': '자산',
    'strategy': '전략',
    'region': '지역'
}

# data to import
dt = '250131'
file_prc = f'funds_monthly_{dt}.csv'
file_cat = 'funds_categories_250308.csv'
file_est = 'funds_bayesian_ret3y_250207.csv'
path = '.'

# Load data
## price
df_prc = pd.read_csv(
    f'{path}/{file_prc}',
    parse_dates=['date'],
    dtype={'ticker': str},
    index_col=['ticker', 'date']
)
df_prc.columns = [cols_prc[x] for x in df_prc.columns]

## cateory
df_cat = pd.read_csv(f'{path}/{file_cat}', index_col=['ticker'])

## beysian stats
df_est = pd.read_csv(f'{path}/{file_est}', index_col=['ticker'])

# Preprocess data to JSON-serializable
## category
data_cat = dict()
for col in df_cat.columns:
    data_cat[col] = df_cat[col].reset_index().groupby(col)['ticker'].apply(list).to_dict()

## name for plots
data_name = df_cat['name'].to_dict()

## price
data_prc = {}
for col in df_prc.columns:
    df = df_prc[col].unstack('ticker').sort_index().dropna(how='all')
    df = df.reindex(df.index.strftime(date_format))
    data_prc[col] = {x: df[x].dropna().to_dict() for x in df.columns}
    #data_prc[col] = df.to_dict(orient='dict')

## Scatter of estimations
xlabel, ylabel = 'mean', 'sd'
df_s = df_est.apply(lambda x: x[xlabel]/ x[ylabel], axis=1).rank().rename('sharpe')
data_est = df_est.join(df_s).join(df_cat)
# convert mean/sd into respective ranks
data_est[xlabel] = data_est[xlabel].rank(ascending=False, pct=True).mul(100)
data_est[ylabel] = data_est[ylabel].rank(pct=True).mul(100)
cols = ['mean', 'sd', 'hdi_3%', 'hdi_97%', 'sharpe'] + df_cat.columns.to_list()
data_est = data_est[cols].to_dict()

# define dropdown options and default value
category_options = [{'label':category[x], 'value':x} for x in df_cat.columns]
category_default = 'asset'
group_default = []


data_cat_json = json.dumps(data_cat)
data_name_json = json.dumps(data_name)
data_prc_json = json.dumps(data_prc)
data_est_json = json.dumps(data_est)

app = Dash(__name__, title="달달펀드",
           external_stylesheets=external_stylesheets)

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
            var dataCategory = {data_cat_json};
            var dataName = {data_name_json};
            var dataPrice = {data_prc_json};
            var dataScatter = {data_est_json};
        </script>
        {{%app_entry%}}
        {{%config%}}
        {{%scripts%}}
        {{%renderer%}}
    </body>
</html>
"""

# footer
footer = html.Footer(
    html.Small([
    html.I(className="fa-regular fa-copyright"),
    '2025 달달펀드'
]), style={'textAlign': 'right', 'margin-top': '20px'})

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
    dbc.Tab(dcc.Graph(id='cagr-plot'), label='수익률', tab_id='tab_cagr'),
    dbc.Tab(dcc.Graph(id='scatter-plot'), label='순위', tab_id='tab_scatter'),
    dbc.Tab(tab_info, label='정보', tab_id='tab_info')
]
tabs = dbc.Tabs(tabs_contents, id='tabs')


app.layout = dbc.Container([
    html.Br(),
    dbc.Stack([
        html.Div(
            dcc.Dropdown(
                id='category-dropdown',
                options=category_options,
                value=category_default,
                clearable=False,
            ), style={'min-width':'10%', 'max-width':'100%'}
        ),
        html.Div(
            dcc.Dropdown(
                id='group-dropdown',
                #options=groups,
                value=group_default,
                multi=True,
            ), style={'min-width':'30%', 'max-width':'100%'}
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
    dcc.Textarea(
        id="ticker-textarea",
        hidden='hidden', 
        #cols=50, rows=10
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
    dcc.Store(id='ticker-data'),
    dcc.Store(id='name-data'),
    dcc.Store(id='price-data'),
    dcc.Store(id='cagr-data'),
    dcc.Store(id='scatter-data'),
    dcc.Location(id="url", refresh=False),  # To initialize the page
#], fluid=True)  # Full-width container
])

# update group options depending on category
app.clientside_callback(
    """
    function(category) {
        let obj = dataCategory[category];
        let groups = Object.keys(obj);
        let maxLength = 20; // Set max label length

        // Prepend "All" to the list
        let result = [{ label: "All", value: "All", title: "All" }];

        // Map over groups and append them to the list
        result = result.concat(
            groups.map(group => ({
                label: group.length > maxLength ? group.substring(0, maxLength) + "..." : group,
                value: group,
                title: group
            }))
        );
        return result;
    }
    """,
    Output('group-dropdown', 'options'),
    Input('category-dropdown', 'value')
)

# check 'All' in selected groups
app.clientside_callback(
    """
    function processGroups(groups) {
        // Check if 'All' is the last element
        //if (groups.length > 0 && groups[groups.length - 1] === "All") {
        if (groups.length === 0 || groups[groups.length - 1] === "All") {
            return ["All"];
        }
    
        // If 'All' is in the array but not the last element, return without 'All'
        if (groups.includes("All")) {
            return groups.filter(group => group !== "All");
        }
    
        // Otherwise, return the original array
        return groups;
    }
    """,
    Output('group-dropdown', 'value'),
    Input('group-dropdown', 'value')
)

# update tickers based on selected groups and category
app.clientside_callback(
    """
    function(groups, category) {
        if (!groups || !category || !dataCategory[category]) return [];

        // If groups contain "All", return all tickers from the category
        if (groups.includes("All")) {
            return Object.values(dataCategory[category]).flat();
        }

        // Otherwise, return tickers only for the specified groups
        let tickers = [];
        groups.forEach(group => {
            if (dataCategory[category][group]) {
                tickers = tickers.concat(dataCategory[category][group]);
            }
        });
        return tickers;
    }
    """,
    Output('ticker-data', 'data'),
    Input('group-dropdown', 'value'),
    State('category-dropdown', 'value')
)

# save name and ticker of funds for copying
app.clientside_callback(
    """
    function(tickers) {
        let result = Object.entries(dataName)
                     .filter(([k, v]) => tickers.includes(k)) // check if k is in tickers
                     .map(([k, v]) => `${k}: ${v}`);
        return result.join('\\n');
    }
    """,
    Output('ticker-textarea', 'value'),
    Input('ticker-data', 'data'),
)

# update price data based on selected tickers
app.clientside_callback(
    """
    function(tickers) {
        if (!tickers || tickers.length === 0) return {};
        
        let data_prc_tkr = {};
        for (let fee in dataPrice) {
            data_prc_tkr[fee] = {};
            for (let tkr in dataPrice[fee]) {
                if (tickers.includes(tkr)) {
                    data_prc_tkr[fee][tkr] = dataPrice[fee][tkr];
                }
            }
        }
        return data_prc_tkr;
    }
    """,
    Output('price-data', 'data'),
    Input('ticker-data', 'data')
)

# plot price history
app.clientside_callback(
    """
    function(data, cost, compare) {
        if (!data || Object.keys(data).length === 0) {
            return { data: [], layout: {} };  // Empty plot
        }
        
        let fees = Object.keys(data);
        let fee = cost ? fees[1] : fees[0];

        if (!data[fee]) {
            return { data: [], layout: {} };
        }

        let df = data[fee];
        if (compare) {
            df = normalizePrice(df, 1000);
        }
        let traces = [];

        for (let tkr in df) {
            traces.push({
                x: Object.keys(df[tkr]),  // Assuming keys are dates
                y: Object.values(df[tkr]),  // Assuming values are prices
                type: 'scatter',
                mode: 'lines',
                name: dataName[tkr]
            });
        }

        // Title logic
        const titleBase = '펀드 가격 추이';
        const titleComp = compare ? '상대 가격' : '펀드별 최근 결산 기준가격';
        const titleCost = cost ? '수수료 적용' : null;

        let title = `${titleBase} (${titleComp}`;
        title = titleCost ? `${title}, ${titleCost})` : `${title})`;
        
        return {
            data: traces,
            layout: {
                title: { text: title},
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
                    type: "date"
                },
            }
        };
    }
    """,
    Output('price-plot', 'figure'),
    Input('price-data', 'data'),
    Input('cost-boolean-switch', 'on'),
    Input('compare-boolean-switch', 'on'),
)

# update cagr data based on selected tickers
app.clientside_callback(
    """
    function(tickers) {
        if (!tickers || tickers.length === 0) return {};
        
        let data_cagr_tkr = {};
        for (let fee in dataPrice) {
            data_cagr_tkr[fee] = {};
            for (let tkr in dataPrice[fee]) {
                if (tickers.includes(tkr)) {
                    data_cagr_tkr[fee][tkr] = calculateCAGR(dataPrice[fee][tkr]);
                }
            }
        }
        return data_cagr_tkr;
    }
    """,
    Output('cagr-data', 'data'),
    Input('ticker-data', 'data')
)

# bar chart of cagr
app.clientside_callback(
    """
    function(data, compare) {
        if (!data || Object.keys(data).length === 0) {
            return { data: [], layout: {} };
        }

        let categories = Object.keys(data);
        let tickers = Object.keys(data[categories[0]]);
        
        let traces = categories.map(category => {
            return {
                x: tickers.map(tkr => dataName[tkr]),
                y: tickers.map(tkr => data[category][tkr] || 0),
                type: 'bar',
                name: category
            };
        });

        let title;
        if (compare) {
            //const dates = dat[sel].index;
            //const dt0 = new Date(Math.min(...dates.map(d => new Date(d).getTime()))).toISOString().slice(0, 10);
            //const dt1 = new Date(Math.max(...dates.map(d => new Date(d).getTime()))).toISOString().slice(0, 10);
            //title = `펀드 연평균 수익률 (${dt0} ~ ${dt1})`;
            title = '펀드 연평균 수익률';
        } else {
            title = '펀드 연평균 수익률 (펀드별 설정일 이후)';
        };

        let layout = {
            title: {text: title},
            barmode: 'group',
            hovermode: 'x',
            //xaxis: { title: 'Ticker' },
            yaxis: { title: '연평균 수익률 (%)' }
        };

        return { data: traces, layout: layout };
    }
    """,
    Output('cagr-plot', 'figure'),
    Input('cagr-data', 'data'),
    Input('compare-boolean-switch', 'on')
)

# update scatter data based on selected tickers
app.clientside_callback(
    """
    function(tickers) {
        if (!tickers || tickers.length === 0) return {};

        const filteredData = {};
        for (const key in dataScatter) {
            filteredData[key] = {};
            for (const ticker of tickers) {
              if (dataScatter[key][ticker] !== undefined) {
                filteredData[key][ticker] = dataScatter[key][ticker];
              }
            }
        }
        
        return filteredData;
    }
    """,
    Output('scatter-data', 'data'),
    Input('ticker-data', 'data')
)

# scatter plot of mean/sd of 3yr return estimations
app.clientside_callback(
    """
    function(data, category) {
        // Define the scale for marker size
        const scale_marker_size = 0.1;
        const add_marker_size = 5;
        
        // Custom color map
        const color_map = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'];

        // Get the keys (i.e., the unique identifiers) for the data
        const keys = Object.keys(data['mean']);

        // Filter the unique categories based on the selected category
        const unique_categories = [...new Set(keys.map(key => data[category][key]))];

        // Create a map for symbols to be assigned to each category
        const symbol_map = {};
        unique_categories.forEach((cat, i) => {
            symbol_map[cat] = i;
        });

        // Create traces for each category
        let traces = unique_categories.map((cat, i) => {
            // Filter data by the selected category
            const df_filtered = keys.filter(key => data[category][key] === cat);

            // Create the trace for each category
            return {
                x: df_filtered.map(key => data['mean'][key]),
                y: df_filtered.map(key => data['sd'][key]),
                customdata: df_filtered.map(key => [
                    data['name'][key], 
                    data['hdi_3%'][key], 
                    data['hdi_97%'][key]
                ]),
                mode: 'markers',
                marker: {
                    size: df_filtered.map(key => data['sharpe'][key] * scale_marker_size + add_marker_size),
                    color: color_map[i % color_map.length],  // Assign a unique color per category
                    symbol: df_filtered.map(key => symbol_map[data[category][key]])  // Assign a unique symbol per category
                },
                name: cat,  // Legend entry
                hovertemplate: '<span style=\"font-size: 120%;\">%{customdata[0]}</span><br>' +
                               '수익률 순위(%): 평균 %{x:.0f}, 편차 %{y:.0f}<br>' +
                               '수익률 구간: %{customdata[1]} ~ %{customdata[2]}<extra></extra>',
            };
        });

        // Define layout
        let layout = {
            title: { text: '3년 평균 수익률 순위 (94% 확률 추정)' }, 
            xaxis: { title: '평균 %순위', autorange: 'reversed', zeroline:false },
            yaxis: { title: '편차 %순위', autorange: 'reversed', zeroline:false },
            hovermode: 'closest',
            legend: { title: category },
            //width: 1000,
            //height: 600,
        };

        // Return the data for the figure
        return { data: traces, layout: layout };
    }
    """,
    Output('scatter-plot', 'figure'),
    Input('scatter-data', 'data'),
    Input('category-dropdown', 'value')
);

# contrain fee/compare switch depending on tabs
app.clientside_callback(
    """
    function(tab, cost, compare) {
        if (tab === "tab_scatter") {
            return [true, false, true, true];
        } else if (tab === "tab_info") {
            return [cost, compare, true, true];
        } else if (tab === "tab_cagr") {
            return [true, compare, true, false];
        } else {
            return [cost, compare, false, false];
        }
    }
    """,
    [Output('cost-boolean-switch', 'on'), Output('compare-boolean-switch', 'on'), 
     Output('cost-boolean-switch', 'disabled'), Output('compare-boolean-switch', 'disabled')],
    [Input("tabs", "active_tab"), Input('cost-boolean-switch', 'on'), Input('compare-boolean-switch', 'on')]
)

# contrain category/group dropdown depending on tabs
app.clientside_callback(
    """
    function(tab, category, group) {
        if (tab === "tab_info") {
            return [true, true];
        } else {
            return [false, false];
        }
    }
    """,
    Output('category-dropdown', 'disabled'), 
    Output('group-dropdown', 'disabled'),
    Input("tabs", "active_tab")
)
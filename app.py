from dash import Dash, html, dcc, Output, Input, State
import pandas as pd
import dash_bootstrap_components as dbc
import dash_daq as daq
import json
from ddf_utils import break_line, extract_topics
from contents_info import info

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
dt = '250331'
file_prc = f'funds_monthly_{dt}.csv'
file_cat = 'funds_categories.csv'
file_est = f'funds_bayesian_ret3y_{dt}.csv'
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

## rank
data_rank = df_est['mean'].rank(ascending=False).to_dict()

# define dropdown options and default value
category_options = [{'label':category[x], 'value':x} for x in df_cat.columns]
category_default = 'asset'
group_default = ['All', '#Top10']

# additional group option for every cat
label = '이거어때?'
desc = '3년수익률 추정 평균/편차 순위 모두 상위권 펀드'
tickers = ['K55364CF7048', 'KR5235AK9808']
#_ = [data_cat[x].update({label:tickers}) for x in data_cat.keys()]
#data_title = {label: desc} # define option title other than label for group options
data_title = {}


# convert data to json
data_cat_json = json.dumps(data_cat)
data_name_json = json.dumps(data_name)
data_prc_json = json.dumps(data_prc)
data_est_json = json.dumps(data_est)
data_rank_json = json.dumps(data_rank)
data_title_json = json.dumps(data_title)

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
            var dataRank = {data_rank_json}
            var dataTitle = {data_title_json};
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

# notice
tab_notice = html.Div(
    children=[
        dcc.Store(id="load-giscus", data=1),  # Trigger the clientside callback on initial load
        html.Div(className="giscus"),  # Placeholder for Giscus
    ]
    , style={'margin-top': '20px'}
)

# tabs
tabs_contents = [
    dbc.Tab(dcc.Graph(id='price-plot'), label='가격'),
    dbc.Tab(dcc.Graph(id='cagr-plot'), label='수익률', tab_id='tab_cagr'),
    dbc.Tab(dcc.Graph(id='scatter-plot'), label='순위', tab_id='tab_scatter'),
    dbc.Tab(tab_notice, label='알림', tab_id='tab_notice',
            label_class_name="tab-label new-badge-label"),
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
            ), style={'min-width':'10%'}
        ),
        html.Div(
            dcc.Input(
                id='name-input', 
                type='text',
                disabled=True,
                size='12',
                className='custom-input'
            ), style={'min-width':'10%'}
        ),
        html.Div(
            dcc.Dropdown(
                id='group-dropdown',
                #options=groups,
                value=group_default,
                multi=True,
            ), style={
                'min-width':'55%', 
                'max-width':'55%',
                #'overflow': 'hidden',      # ✅ hide overflow
                'textOverflow': 'ellipsis',# ✅ trim long text
            }
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
    dcc.Store(id='previous-data'),
    dcc.Store(id='filter-data'),
    dcc.Store(id='options-data'),
    dcc.Store(id='price-data'),
    dcc.Store(id='scatter-data'),
    dcc.Location(id="url", refresh=False),  # To initialize the page
#], fluid=True)  # Full-width container
])

# update group options depending on category
app.clientside_callback(
    """
    function(category, groups_opt, tickers) {
        let obj = dataCategory[category];
        let groups = Object.keys(obj);
        let maxLength = 20; // Set max label length

        // Prepend "All" to the list
        let options = [
            { label: "All", value: "All", title: "전체 펀드" },
            { label: "#Top10", value: "#Top10", title: "3년 수익률 추정 평균 기준"},
            { label: "#Bottom10", value: "#Bottom10", title: "3년 수익률 추정 평균 기준"},
            { label: "#Random10", value: "#Random10", title: "3년 수익률 추정 평균 기준"},
        ];
        
        if (tickers) {
            options = [...options, { label: "Combined with 𝗣𝗿𝗲𝘃𝗶𝗼𝘂𝘀", value: "uPrevious", title: "이전 선택과 함께"}]
            options = [...options, { label: "Overlap with 𝗣𝗿𝗲𝘃𝗶𝗼𝘂𝘀", value: "nPrevious", title: "이전 선택 중에서"}]
        }

        // Map over groups and append them to the list
        options = options.concat(
            groups.map(group => ({
                label: group.length > maxLength ? group.substring(0, maxLength) + "..." : group,
                value: group,
                title: dataTitle[group] || group  // Use group name if dataTitle[group] is missing
            }))
        );
        // reset group values to 'All' and ranking selected before
        if (tickers) {
            if (groups_opt.length === 1 && groups_opt[0] === 'All') {
                value = ['All'];
            } else {
                value = ['nPrevious'];
            }
        } else {
            value = groups_opt?.filter(group => group.startsWith('#')) || [];
            value = ['All', ...value];
        }
        
        return [options, value, tickers, options];
    }
    """,
    Output('group-dropdown', 'options'),
    Output('group-dropdown', 'value'),
    Output('previous-data', 'data'),
    Output('options-data', 'data'), # save for name filter
    Input('category-dropdown', 'value'),
    State('group-dropdown', 'value'),
    State('ticker-data', 'data'),
)

# Process group values such as 'All', previous, ranking and N funds selected
app.clientside_callback(
    """
    function(groups, options, category, names, allnames) {
        // Split groups into `groups_m` (regular) and `groups_opt` (optional value)
        let { groups_m, group_opt } = (groups || []).reduce((acc, group) => {
            if (group.startsWith("#")) {
                acc.group_opt = group; // Keep only the latest rank option
            } else {
                acc.groups_m.push(group);
            }
            return acc;
        }, { groups_m: [], group_opt: null });

        // Find the last index of any "*Previous"
        const previous = ['uPrevious', 'nPrevious'];
        let lastIndex = -1;
        for (let i = groups_m.length - 1; i >= 0; i--) {
            if (previous.includes(groups_m[i])) {
                lastIndex = i;
                break;
            }
        }
        // Filter to keep only the last kind (if any)
        groups_m = groups_m.filter((item, index) => {
            if (!previous.includes(item)) return true;
            return index === lastIndex;
        });

        // Check if 'All' is the last element
        if (groups_m.length === 0 || groups_m[groups_m.length - 1] === 'All') {
            let result = ['All', group_opt].filter(Boolean); // Remove null values
            return [result, options, []];
        };
    
        // If 'All' is in the array but not the last element, return without 'All'
        if (groups_m.includes('All')) {
            groups_m = groups_m.filter(group => group !== 'All');
        };

        // replace fund names by 'N funds selected'
        let newNames = [];
        let newOptions = [...options];
        if (category === 'name') {
            // option value for 'N funds selected'
            const selectedPattern = /^\\d+ funds selected$/;
            
            // array of option value 'nSelected' can have 'N funds selected' and additional fund names after removing *previous
            const nSelected = groups_m.filter(group => !previous.includes(group));
            
            // refresh 'N funds selected' with additional funds names
            let nameValues = names.map(item => item.value); // new funds being added to 'N funds selected'

            // update fund names for new 'N funds selected'
            if (nSelected.some(group => selectedPattern.test(group))) {
                additionalValues = nSelected.filter(group => !selectedPattern.test(group));
                if (additionalValues.length > 0) { // add additional to existing
                    nameValues = nameValues.concat(additionalValues);
                }
            } else { // no 'N funds selected' exists
                if (nSelected.length > 0) {
                    nameValues = nSelected; // replace names with new selection
                }                
            }
            
            if (nameValues.length > 0) {
                // set new group values
                const value = nameValues.length + ' funds selected';
                groups_m = [...groups_m.filter(group => previous.includes(group)), value];

                // set options for nameValues from full fund name options
                newNames = allnames.filter(obj => nameValues.includes(obj.value));
                
                // set new options
                newOptions = allnames.filter(obj => !nameValues.includes(obj.value));
                newOptions = [...newOptions, {'label':value, 'value':value}];
            }
        }
        // return the array with new rank option
        let result = groups_m.concat(group_opt).filter(Boolean);
        return [result, newOptions, newNames];
    }
    """,
    Output('group-dropdown', 'value', allow_duplicate=True),
    Output('group-dropdown', 'options', allow_duplicate=True),
    Output('filter-data', 'data', allow_duplicate=True),
    Input('group-dropdown', 'value'),
    State('group-dropdown', 'options'),
    State('category-dropdown', 'value'),
    State('filter-data', 'data'),
    State('options-data', 'data'),
    prevent_initial_call=True
)


# Enable name-input only if category is "name"
app.clientside_callback(
    """
    function(category) {
        const isDisabled = category !== "name";
        const placeholder = isDisabled ? null : "펀드 이름으로 검색";
        return [isDisabled, placeholder, ""];
    }
    """,
    Output('name-input', 'disabled'),
    Output('name-input', 'placeholder'),
    Output('name-input', 'value'),
    Input('category-dropdown', 'value')
)

# multiple selection for name category
app.clientside_callback(
    """
    function(pattern, category, groups, options) {
        // Return current groups if pattern is empty or category isn't 'name'
        if (!pattern || category !== "name") {
            return [groups, []];
        }
        
        // Get all the fund names
        const obj = dataCategory[category];
        let names = Object.keys(obj);

        try {
            // Escape special characters and convert * to .*
            const escaped = pattern
                .replace(/[.+?^${}()|[\\]\\\\]/g, '\\\\$&')
                .replace(/\\*/g, '.*');
            const regex = new RegExp('.*' + escaped + '.*', 'i');

            // Filter and return options of matching values
            let filtered = names.filter(opt => regex.test(opt));
            return [filtered, options.filter(obj => filtered.includes(obj.value))];
        } catch (e) {
            console.error("Regex error:", e);
            return [groups, []];
        }
    }
    """,
    Output('group-dropdown', 'value', allow_duplicate=True),
    Output('filter-data', 'data'),
    Input('name-input', 'value'),
    State('category-dropdown', 'value'),
    State('group-dropdown', 'value'),
    State('group-dropdown', 'options'),
    prevent_initial_call=True
)

# update tickers based on selected groups and category
app.clientside_callback(
    """
    function(groups, category, previous, names) {
        let tickers = [];
        const localCategory = dataCategory[category];
        if (!groups || !category || !localCategory) return [];

        let localgroups = [...groups];

        // retrieve fund names to get tickers
        const index = localgroups.findIndex(item => /^\\d+ funds selected$/.test(item));
        if (index !== -1) {
            // splice() modifies the original array and returns the removed elements, not the updated array
            localgroups.splice(index, 1, ...names.map(item => item.value));
        }

        // If "All" is selected, return all tickers in the category
        if (localgroups.includes("All")) {
            tickers = Object.values(localCategory).flat();
        } else {
            // Add tickers from selected groups
            for (const group of localgroups) {
                if (localCategory[group]) {
                    tickers.push(...localCategory[group]);
                }
            }
        }
    
        // Fallback to previous tickers if none found
        if (tickers.length > 0) {
            // Modify tickers based on previous if specified
            if (previous && previous.length > 0) {
                if (localgroups.includes("uPrevious")) {
                    tickers.push(...previous);
                }
                if (localgroups.includes("nPrevious")) {
                    tickers = tickers.filter(ticker => previous.includes(ticker));
                }
            }
        } else {
            tickers = previous.length > 0 ? previous : [];
        }

        // Optional filtering by ranking
        if (tickers) {
            const groups_opt = localgroups?.filter(group => group.startsWith('#')) || [];
            if (groups_opt.length === 1) {
                const match = groups_opt[0].slice(1).match(/^([a-zA-Z]+)(\\d+)$/);
                if (match) {
                    tickers = selectTickers(match[1], tickers, dataRank, match[2]);
                }
            }
        }
        return tickers;
    }
    """,
    Output('ticker-data', 'data'),
    Input('group-dropdown', 'value'),
    State('category-dropdown', 'value'),
    State('previous-data', 'data'),
    State('filter-data', 'data')
)

# save name and ticker of funds for copying
app.clientside_callback(
    """
    function(tickers) {
        if (!Array.isArray(tickers)) {
            return '';
        }
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
        if (!Array.isArray(tickers)) {
            return {};
        }
        
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
                y: Object.values(df[tkr]).map(val => Math.round(val)),  // Assuming values are prices
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

        let layout = {
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
            //height: 500,
        }

        // Adjust legend position for mobile devices
        layout = updateLayout(layout, x = 0, y = -0.5, width = 768)
                
        return {
            data: traces,
            layout: layout
        };
    }
    """,
    Output('price-plot', 'figure'),
    Input('price-data', 'data'),
    Input('cost-boolean-switch', 'on'),
    Input('compare-boolean-switch', 'on'),
)


# plot bar chart of cagr
app.clientside_callback(
    """
    function(data, compare) {
        if (!data || Object.keys(data).length === 0) {
            return { data: [], layout: {} };
        }

        // calc CAGR
        let data_cagr = {};
        for (let fee in data) {
            let df = data[fee];
            if (compare) { // normalize depending on compare switch
                df = normalizePrice(df, 1000);
                let tickers = Object.keys(df);
                var dates = Object.keys(df[tickers[0]]);
            };
            data_cagr[fee] = {};
            for (let tkr in df) {
                data_cagr[fee][tkr] = calculateCAGR(df[tkr]);
            }
        }

        let categories = Object.keys(data_cagr);
        let tickers = Object.entries(data_cagr[categories[1]]) // use cagr after fees for sorting
                            .sort((a, b) => b[1] - a[1]) // sort descending by CAGR
                            .map(entry => entry[0]);     // extract just the ticker names
        
        let traces = categories.map(category => {
            return {
                x: tickers.map(tkr => dataName[tkr]),
                //y: tickers.map(tkr => data_cagr[category][tkr] || 0),
                y: tickers.map(tkr => Math.round((data_cagr[category][tkr] || 0) * 10) / 10), // Round to 1 decimals
                type: 'bar',
                name: category
            };
        });

        let title;
        if (compare) {
            const dt0 = new Date(Math.min(...dates.map(d => new Date(d).getTime()))).toISOString().slice(0, 10);
            const dt1 = new Date(Math.max(...dates.map(d => new Date(d).getTime()))).toISOString().slice(0, 10);
            title = `펀드 연평균 수익률 (${dt0} ~ ${dt1})`;
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

        // Adjust legend position for mobile devices
        layout = updateLayout(layout, x = 0, y = -0.5, width = 768)

        return { data: traces, layout: layout };
    }
    """,
    Output('cagr-plot', 'figure'),
    Input('price-data', 'data'),
    Input('compare-boolean-switch', 'on')
)

# update scatter data based on selected tickers
app.clientside_callback(
    """
    function(tickers) {
        if (!Array.isArray(tickers)) {
            return {};
        }

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
                               '수익률 구간: %{customdata[1]:.1%} ~ %{customdata[2]:.1%}<extra></extra>',
            };
        });

        // Define the reference line (y = x)
        const x_min = 1;
        const x_max = 100;
        const line_trace = {
            x: [x_min, x_max],
            y: [x_min, x_max],  // Slope 1 line (y = x)
            mode: 'lines',
            //line: { color: 'black', dash: 'dash' }, // Dashed black line
            line: { color: 'rgba(204, 204, 204, 0.5)', width: 1},
            showlegend: false
        };
    
        // Add the line trace to the traces array
        traces.push(line_trace);

        // Adding annotation
        var font = {size:30, weight:'bold', color:'rgba(204, 204, 204, 0.5)',
                    //family: 'Lucida Console, Courier, monospace'
                    }
        var ant1 = {x:70, y:30, showarrow:false, font:font, text:'안 정 성'};
        var ant2 = {x:30, y:70, showarrow:false, font:font, text:'수 익 성'};

        // Define layout
        let layout = {
            title: { text: '펀드 순위 (3년 수익률의 94% 확률 추정)' }, 
            xaxis: { title: '평균 %순위', autorange: 'reversed', zeroline:false},
            yaxis: { title: '편차 %순위', autorange: 'reversed', zeroline:false},
            annotations: [ant1, ant2],
            hovermode: 'closest',
            showlegend: true,
            legend: { title: category },
            //width: 600,
            height: 500,
        };

        // Adjust legend position for mobile devices
        layout = updateLayout(layout, x = 0, y = -0.5, width = 768)

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
        } else if (tab === "tab_info" || tab === "tab_notice" ) {
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
        if (tab === "tab_info" || tab === "tab_notice" ) {
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

# Register the clientside callback to check if on mobile and apply label-style-mobile to all tabs
app.clientside_callback(
    """
    function(pathname) {
        // Check if the current window width indicates a mobile device
        const isMobile = window.innerWidth < 768;
        const tabElements = document.querySelectorAll('.nav-item');  // All tab items
        
        // Add or remove the CSS class for label styling for all tabs
        tabElements.forEach(function(tabElement) {
            if (isMobile) {
                tabElement.classList.add('label-style-mobile');
            } else {
                tabElement.classList.remove('label-style-mobile');
            }
        });
        
        return window.dash_clientside.no_update;  // Return no update to children
    }
    """,
    Output('tabs', 'children'),  # Update the children of tabs (triggering the callback)
    Input('url', 'pathname'),
)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=False)
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

## cateory
df_cat = pd.read_csv(f'{path}/{file_cat}', index_col=['ticker'])

## beysian stats
df_est = pd.read_csv(f'{path}/{file_est}', index_col=['ticker'])

# Preprocess data to JSON-serializable
data_cat = dict()
for col in df_cat.columns:
    data_cat[col] = df_cat[col].reset_index().groupby(col)['ticker'].apply(list).to_dict()

# additional vars
category_options = [{'label':category[x], 'value':x} for x in df_cat.columns]
category_default = 'asset'
group_default = []


data_cat_json = json.dumps(data_cat)

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
    dbc.Tab(tab_info, label='정보')
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
        #hidden='hidden'
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
    dcc.Store(id='price-data'),
    dcc.Store(id='hdi-data'),
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
    
        return groups.map(group => ({
            label: group.length > maxLength ? group.substring(0, maxLength) + "..." : group,
            value: group,
            title: group
        }));
    }
    """,
    Output('group-dropdown', 'options'),
    Input('category-dropdown', 'value')
)

app.clientside_callback(
    """
    function(groups, category) {
        let obj = dataCategory[category];
        let result = [];
    
        // Iterate through groups and collect values from obj
        for (let group of groups) {
            result.push(obj[group]);
        }
    
        // Convert result array to a Set (to remove duplicates) and back to an array
        result = [...new Set(result)];

        let flattenedResult = result.flat().join(\n);
        //console.log(flattenedResult);
        return flattenedResult;
    }
    """,
    Output('ticker-textarea', 'value'),
    Input('group-dropdown', 'value'),
    State('category-dropdown', 'value')
)
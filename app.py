import ppdv
from dash import  dcc, Dash, html
import plotly.graph_objs as go
import requests
import redis
import threading
import time
from flask import Flask
import json
from datetime import datetime
from dash import dash_table
import pytz
import dash_bootstrap_components as dbc
import callbacks.callbacks as callbacks


FA = "https://use.fontawesome.com/releases/v5.15.1/css/all.css"
external_stylesheets = [FA]

server = Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=external_stylesheets)

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

def fetch_and_store_data():
    while True:
        for person_id in range(1, 7):  # IDs from 1 to 6
            try:
                response = requests.get(f'http://tesla.iem.pw.edu.pl:9080/v2/monitor/{person_id}')
                if response.status_code == 200:
                    data = response.json()

                    utc_time = datetime.utcnow()
                    warsaw_timezone = pytz.timezone('Europe/Warsaw')
                    warsaw_time = utc_time.replace(tzinfo=pytz.utc).astimezone(warsaw_timezone)
                    timestamp = warsaw_time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    data_with_timestamp = {'timestamp': timestamp, 'data': data}
                    # Store data in Redis
                    redis_client.rpush(f'person_{person_id}_data_list', json.dumps(data_with_timestamp))
                    redis_client.ltrim(f'person_{person_id}_data_list', -610, -1)

                    if any(sensor.get('anomaly', False) for sensor in data['trace']['sensors']):
                        anomalies_key = f'person_{person_id}_anomalies'
                        redis_client.rpush(anomalies_key, json.dumps(data_with_timestamp))

            except requests.RequestException as e:
                print(f"Error fetching data for person {person_id}: {e}")
        time.sleep(1)

data_fetch_thread = threading.Thread(target=fetch_and_store_data, daemon=True)
data_fetch_thread.start()

sensor_columns = ['L0', 'L1', 'L2', 'R0', 'R1', 'R2']
max_sensor_value = 1100
conditional_styles = []
is_sensor_refreshing_paused = False
is_anomalies_refreshing_paused = False


def get_person_options():
    person_options = []
    for i in range(1, 8):  # Assuming you have person IDs from 1 to 7
        response = requests.get(f'http://tesla.iem.pw.edu.pl:9080/v2/monitor/{i}')
        if response.status_code == 200:
            person_data = response.json()
            # Construct label from the firstname and lastname
            person_label = f"{person_data['firstname']} {person_data['lastname']}"
            # Use the ID as the value for the dropdown
            person_options.append({'label': person_label, 'value': i})
    return person_options

def get_color_for_value(value, max_value=1100):
    value = min(max(value, 0), max_value)
    ratio = value / max_value
    hue = (1 - ratio) * 120
    return f"hsl({hue}, 100%, 50%)"

sensor_value_colors = {
    value: get_color_for_value(value, max_sensor_value) for value in range(max_sensor_value + 1)
}

for column in sensor_columns:
    for value, color in sensor_value_colors.items():
        conditional_styles.append({
            'if': {
                'column_id': column,
                'filter_query': f'{{{column}}} eq {value}'
            },
            'backgroundColor': color,
            'color': 'white' if color != 'hsl(120, 100%, 50%)' else 'black'
        })


callbacks.register_callbacks(app, redis_client)

app.layout = html.Div([
    # Header
    html.Div([
        html.H1('Feet Pressure Sensor Dashboard', style={'textAlign': 'center', 'color': '#000000', 'fontSize': '2.5em', 'margin':'0', 'padding-top':'20px', 'padding-bottom':'20px'}),
    ], style={'width': '100%', 'display': 'block'}),
    
    # Content
    html.Div([
        # Person selector and details
        html.Div([
            html.H3('Patient', style={'textAlign': 'center', 'marginBottom': '10px'}),
            # Dropdown with user icon
            html.Div([
                html.I(className="fas fa-user", style={'marginRight': '10px'}),
                 dcc.Dropdown(id='person-selector', options=get_person_options(), style={'width': 'calc(100%)'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
            
            # Person details
            html.Div(id='person-details', style={ 'borderRadius': '5px'})
        ], style={
            'padding': '20px',
            'margin': '10px',
            'border': '1px solid #e9ecef',
            'borderRadius': '5px',
            'backgroundColor': '#fff', 
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)', 
            'width':'350px',
            'flex': 'none'}), # Set width to 350px and flex to none

        # Sensor chart
        html.Div([
            html.H3('Last 3 minutes sensor data chart', style={'textAlign': 'center', 'marginBottom': '10px'}),
            dcc.Graph(id='sensor-chart')
        ], style={
            'padding': '20px',
            'margin': '10px',
            'border': '1px solid #e9ecef',
            'borderRadius': '5px',
            'backgroundColor': '#fff',
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'flex': '1' # Adjust the flex value as needed
        }),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'stretch'}),

    html.Div([
        # Live pressure Points
        html.Div([
            html.H3('Live pressure points', style={'textAlign': 'center'}),
            ppdv.Ppdv(id='feet-pressure', sensorData=[])
        ], style={
            'padding': '20px', 
            'margin': '10px',
            'border': '1px solid #e9ecef', 
            'borderRadius': '5px', 
            'backgroundColor': '#fff', 
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'width': '350px', # Set width to 350px
            'flex': 'none'}), # Set flex to none
        html.Div([
            html.H3('All latest data (lastest 600 records)', style={'textAlign': 'center', 'margin-bottom':'10px', 'margin-top':'5px'}),
            dash_table.DataTable(
                id='sensors-table',
                columns=[
                    {'name': 'Timestamp', 'id': 'timestamp'},
                    {'name': 'L0', 'id': 'L0'},
                    {'name': 'L1', 'id': 'L1'},
                    {'name': 'L2', 'id': 'L2'},
                    {'name': 'R0', 'id': 'R0'},
                    {'name': 'R1', 'id': 'R1'},
                    {'name': 'R2', 'id': 'R2'},
                ],
                style_cell={
                    'textAlign': 'center',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'whiteSpace': 'normal'
                },
                style_cell_conditional=[
                    {'if': {'column_id': c},
                    'minWidth': '50px', 'width': '50px', 'maxWidth': '50px'}
                    for c in ['L0', 'L1', 'L2', 'R0', 'R1', 'R2']
                ],
                style_header={
                    'backgroundColor': '#e6f3d7',
                    'fontWeight': 'bold'
                },
                style_data_conditional=conditional_styles,
                export_format="csv",
                export_headers="display",
                page_size=15,  # Number of rows visible per page
            ),
            html.Div(style={'flex-grow': '1'}),
            dbc.Row([
                dbc.Col(html.Button(id='pause-sensor-button', n_clicks=0, children=[html.I(className="fas fa-pause")]), width=2, align='start'),
            ], style={'display':'flex', 'justify-content':'space-between'}),
        ], style={
            'padding': '20px',
            'margin': '10px',
            'border': '1px solid #e9ecef',
            'borderRadius': '5px',
            'backgroundColor': '#fff',
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'flex': '1.5',
            'display': 'flex', 
            'flex-direction': 'column'
        }),
       
        html.Div([
            html.H3('Detected anomalies', style={'textAlign': 'center', 'margin-bottom':'10px', 'margin-top':'5px'}),
            dash_table.DataTable(
                id='anomalies-table',
                columns=[
                    {'name': 'Timestamp', 'id': 'timestamp'},
                    {'name': 'L0', 'id': 'L0'},
                    {'name': 'L1', 'id': 'L1'},
                    {'name': 'L2', 'id': 'L2'},
                    {'name': 'R0', 'id': 'R0'},
                    {'name': 'R1', 'id': 'R1'},
                    {'name': 'R2', 'id': 'R2'},
                ],
                style_cell={
                    'textAlign': 'center',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'whiteSpace': 'normal'
                },
                style_cell_conditional=[
                    {'if': {'column_id': c},
                    'minWidth': '50px', 'width': '50px', 'maxWidth': '50px'}
                    for c in ['L0', 'L1', 'L2', 'R0', 'R1', 'R2']
                ],
                style_header={
                    'backgroundColor': '#e6f3d7',
                    'fontWeight': 'bold'
                },
                style_data_conditional=conditional_styles,
                export_format="csv",
                export_headers="display",
                page_size=15,  # Number of rows visible per page
            ),
            html.Div(style={'flex-grow': '1'}),
            dbc.Row([
                dbc.Col(html.Button(id='pause-anomalies-button', n_clicks=0, children=[html.I(className="fas fa-pause")]), width=2, align='start'),
            ], style={'display':'flex', 'justify-content':'space-between'}),
        ], style={
            'padding': '20px',
            'margin': '10px',
            'border': '1px solid #e9ecef',
            'borderRadius': '5px',
            'backgroundColor': '#fff',
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'flex': '1.5',
            'display': 'flex', 
            'flex-direction': 'column'
        }),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'stretch', 'min-height':'620px'}),
    # Interval component for periodic callbacks
    dcc.Interval(id='interval-update', interval=1000, n_intervals=0)
])


if __name__ == '__main__':
    app.run_server(debug=False)
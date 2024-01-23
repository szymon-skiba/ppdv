import ppdv
import dash
from dash import  dcc, Dash, callback, html, Input, Output, State,ALL
import plotly.graph_objs as go
import requests
from dash.exceptions import PreventUpdate
import redis
import threading
import time
from flask import Flask
import json
import pandas as pd
import plotly.express as px
import plotly.express as px
from datetime import datetime, timedelta
from dash import dash_table
import pytz
import dash_bootstrap_components as dbc


FA = "https://use.fontawesome.com/releases/v5.15.1/css/all.css"
external_stylesheets = [FA]


server = Flask(__name__)


redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

def fetch_and_store_data():
    while True:
        for person_id in range(1, 7):  # IDs from 1 to 6
            try:
                response = requests.get(f'http://tesla.iem.pw.edu.pl:9080/v2/monitor/{person_id}')
                if response.status_code == 200:
                    data = response.json()
                    timestamp = datetime.utcnow().isoformat() 
                    data_with_timestamp = {'timestamp': timestamp, 'data': data}

                    redis_client.rpush(f'person_{person_id}_data_list', json.dumps(data_with_timestamp))
                    redis_client.ltrim(f'person_{person_id}_data_list', -610, -1) 

                    if any(sensor.get('anomaly', False) for sensor in data['trace']['sensors']):
                        # Append to a list for anomalies for the person
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

def get_anomalies_data(person_id):
    anomalies_key = f'person_{person_id}_anomalies'

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=10)
    anomalies_records = redis_client.lrange(anomalies_key, 0, -1)

    anomalies_data = []
    for record in anomalies_records:
        try:
            anomaly = json.loads(record)
            anomaly_time = datetime.strptime(anomaly['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')

            warsaw_timezone = pytz.timezone('Europe/Warsaw')
            warsaw_timestamp = anomaly_time.replace(tzinfo=pytz.utc).astimezone(warsaw_timezone)

            if start_time <= warsaw_timestamp <= end_time:
                anomalies_data.append({'timestamp': warsaw_timestamp.strftime('%Y-%m-%d %H:%M:%S')})
        except Exception as e:
            return pd.DataFrame(anomalies_data)

    return pd.DataFrame(anomalies_data)

def get_last_5_minutes_data(person_id):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=5)
    sensor_data_key = f'person_{person_id}_data_list'
    sensor_data_records = redis_client.lrange(sensor_data_key, 0, -1)

    # Prepare DataFrame
    data = []
    for record in sensor_data_records:
        record_data = json.loads(record)
        record_time = datetime.strptime(record_data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
        if start_time <= record_time <= end_time:
            sensors_data = record_data['data']['trace']['sensors']
            for sensor in sensors_data:
                data.append({
                    'timestamp': record_time,
                    'sensor': sensor['name'],
                    'value': sensor['value']
                })

    return pd.DataFrame(data)
app = Dash(__name__, external_stylesheets=external_stylesheets)

@app.callback(
    Output('sensor-chart', 'figure'),
    [Input('interval-update', 'n_intervals'), 
     Input('person-selector', 'value')]
)
def update_sensor_chart(n, person_id):
    if not person_id:
        return go.Figure()

    df = get_last_5_minutes_data(person_id)
    anomalies_df = get_anomalies_data(person_id)
    # Create line chart
    fig = px.line(df, x='timestamp', y='value', color='sensor',
                  color_discrete_map={
                      'L0': '#808700', 'L1': '#d7e120', 'L2': '#f2ff00',
                      'R0': '#0017ff', 'R1': '#182183', 'R2': '#515fe9'  
                  })
    
    if not anomalies_df.empty and 'timestamp' in anomalies_df.columns:
        for anomaly_time in anomalies_df['timestamp']:
            fig.add_vline(x=anomaly_time, line_width=2, line_dash="dash", line_color="red")

        
    fig.update_layout(
        title='Sensor Data Over Last 10 Minutes',
        xaxis_title='Time',
        yaxis_title='Sensor Value',
        yaxis=dict(range=[0, 1200]),
        legend_title='Sensor',
        template='plotly_white'
    )

    return fig

@app.callback(
    Output('pause-sensor-button', 'children'),
    [Input('pause-sensor-button', 'n_clicks')],
    prevent_initial_call=True
)
def toggle_sensor_refreshing(n_clicks):
    global is_sensor_refreshing_paused
    is_sensor_refreshing_paused = not is_sensor_refreshing_paused
    icon_class = "fas fa-play" if is_sensor_refreshing_paused else "fas fa-pause"
    return html.I(className=icon_class)

@app.callback(
    Output('pause-anomalies-button', 'children'),
    [Input('pause-anomalies-button', 'n_clicks')],
    prevent_initial_call=True
)
def toggle_anomalies_refreshing(n_clicks):
    global is_anomalies_refreshing_paused
    is_anomalies_refreshing_paused = not is_anomalies_refreshing_paused
    icon_class = "fas fa-play" if is_anomalies_refreshing_paused else "fas fa-pause"
    return html.I(className=icon_class)


@app.callback(
    Output('anomalies-table', 'data'),
    [Input('interval-update', 'n_intervals'), 
     Input('person-selector', 'value')]
)
def update_anomalies_table(n, person_id):
    if not person_id or is_anomalies_refreshing_paused:
        raise PreventUpdate
    
    if not person_id:
        return []
    
    try:
        # Fetch anomalies from Redis
        anomalies_key = f'person_{person_id}_anomalies'
        anomalies_records = redis_client.lrange(anomalies_key, 0, -1)
        
        # Process the records and prepare the data for the table
        anomalies_data = []
        for record in anomalies_records:
            anomaly = json.loads(record)
            sensors_data = anomaly['data']['trace']['sensors']
            utc_timestamp = datetime.strptime(anomaly['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
            warsaw_timezone = pytz.timezone('Europe/Warsaw')
            warsaw_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(warsaw_timezone)
            formatted_timestamp = warsaw_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            row = {'timestamp': formatted_timestamp}
            row.update({sensor['name']: sensor['value'] for sensor in sensors_data})
            anomalies_data.append(row)
            
        # Sort by newest first
        sorted_anomalies = sorted(anomalies_data, key=lambda x: x['timestamp'], reverse=True)
        return sorted_anomalies
    except Exception as e:
        return []  # Return an empty list if there's an error

@app.callback(
    Output('sensors-table', 'data'),
    [Input('interval-update', 'n_intervals'), 
     Input('person-selector', 'value')]
)
def update_sensor_data_table(n, person_id):
    if not person_id or is_sensor_refreshing_paused:
        raise PreventUpdate
    
    if not person_id:
        return []
    
    try:
        # Fetch sensor data from Redis
        sensor_data_key = f'person_{person_id}_data_list'
        sensor_data_records = redis_client.lrange(sensor_data_key, 0, -1)
        
        # Process each record and prepare the data for the table
        sensor_data_list = []
        for record in sensor_data_records:
            sensor_data = json.loads(record)  # Parse each record from the list
            sensors_data = sensor_data['data']['trace']['sensors']
            utc_timestamp = datetime.strptime(sensor_data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
            warsaw_timezone = pytz.timezone('Europe/Warsaw')
            warsaw_timestamp = utc_timestamp.replace(tzinfo=pytz.utc).astimezone(warsaw_timezone)
            formatted_timestamp = warsaw_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            row = {'timestamp': formatted_timestamp}
            row.update({sensor['name']: sensor['value'] for sensor in sensors_data})
            sensor_data_list.append(row)
        
        sorted_sensor_data_list = sorted(sensor_data_list, key=lambda x: x['timestamp'], reverse=True)
        
        return sorted_sensor_data_list
        
    except Exception as e:
        return []  

@app.callback(
    Output('person-details', 'children'),
    [Input('person-selector', 'value')]
)
def display_person_details(person_id):
    redis_client.set('some_key', 'some_value')
    if not person_id:
        return "Select a person to see their details."

    response = requests.get(f'http://tesla.iem.pw.edu.pl:9080/v2/monitor/{person_id}')
    if response.status_code == 200:
        person_data = response.json()
        details_style = {
            'border': '1px solid #ddd',
            'padding': '10px',
            'borderRadius': '5px',
            'marginBottom': '20px',
        }
        detail_row_style = {
            'display': 'flex',
            'justifyContent': 'start',
            'marginBottom': '5px'
        }
        detail_label_style = {
            'minWidth': '100px',
            'fontWeight': 'bold'
        }
        detail_value_style = {
            'fontWeight': 'bold',
            'fontSize': '1.2em',
            'marginLeft': '10px'
        }
        details = html.Div([
            html.Div([
                html.Div('First Name:', style=detail_label_style),
                html.Div(person_data.get('firstname', 'N/A'), style=detail_value_style)
            ], style=detail_row_style),
            html.Div([
                html.Div('Last Name:', style=detail_label_style),
                html.Div(person_data.get('lastname', 'N/A'), style=detail_value_style)
            ], style=detail_row_style),
            html.Div([
                html.Div('Person ID:', style=detail_label_style),
                html.Div(person_id, style={'marginLeft': '10px'})
            ], style=detail_row_style),
            html.Div([
                html.Div('Birthdate:', style=detail_label_style),
                html.Div(person_data.get('birthdate', 'N/A'), style={'marginLeft': '10px'})
            ], style=detail_row_style),
            html.Div([
                html.Div('Disabled:', style=detail_label_style),
                html.Div('Yes' if person_data.get('disabled', False) else 'No', style={'marginLeft': '10px'})
            ], style=detail_row_style)
        ], style=details_style)
    
        global is_sensor_refreshing_paused
        global is_anomalies_refreshing_paused
        is_sensor_refreshing_paused = False
        is_anomalies_refreshing_paused = False

        return details
    else:
        return "Failed to load person details."

@app.callback(
    Output('feet-pressure', 'sensorData'),
    [Input('interval-update', 'n_intervals')],
    [State('person-selector', 'value')]
)
def update_pressure_data(n, person_id):
    if not person_id:
        return []
    
    try:
        # Fetch the last record from Redis list
        last_record = redis_client.lrange(f'person_{person_id}_data_list', -1, -1)
        if last_record:
            data = json.loads(last_record[0])  # Parse the latest JSON data from Redis
            sensors_data = data['data']['trace']['sensors']
            formatted_data = [
                {'id': sensor['id'], 'name': sensor['name'], 'value': sensor['value']}
                for sensor in sensors_data
            ]
            return formatted_data
    except Exception as e:
        print(f"Error fetching or processing latest sensor data for person {person_id}: {e}")

    return []


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
        ], style={'padding': '20px', 'margin': '10px', 'border': '1px solid #e9ecef', 'borderRadius': '5px', 'backgroundColor': '#fff', 'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)', 'flex': '0.5'}),
        html.Div([
            html.H3('Live pressure Points', style={'textAlign': 'center'}),
            ppdv.Ppdv(id='feet-pressure', sensorData=[])
        ], style={
            'padding': '20px', 
            'margin': '10px',
            'border': '1px solid #e9ecef', 
            'borderRadius': '5px', 
            'backgroundColor': '#fff', 
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'flex': '1',
            'display': 'flex',
            'flexDirection': 'column',
            'alignItems': 'center'  }),    
       
        html.Div([
            html.H3('Last 10 minutes sensor data chart', style={'textAlign': 'center', 'marginBottom': '10px'}),
            dcc.Graph(id='sensor-chart')
        ], style={
            'padding': '20px',
            'margin': '10px',
            'border': '1px solid #e9ecef',
            'borderRadius': '5px',
            'backgroundColor': '#fff',
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'flex': '1'
        }),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'stretch'}),
    html.Div([
        html.Div([
            # Whitesapce
            html.Div([
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px', 'width': 'calc(100% - 30px)'}),
            
        ], style={'padding': '20px', 'margin': '10px', 'flex': '0.5'}),
        
        html.Div([
            html.H3('Sensor data last 10 minutes', style={'textAlign': 'center', 'margin-bottom':'10px', 'margin-top':'5px'}),
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
                style_cell={'textAlign': 'center'},
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
                dbc.Col(html.Button(id='pause-sensor-button', n_clicks=0, children=[html.I(className="fas fa-pause")]), width=2, align='start', style={'position': 'absolute', 'bottom': '70px'}),
                # dbc.Col(html.Button(id='download-sensor-data', n_clicks=0, children=[html.I(className="fas fa-download")]), width=2, align='end')
            ], style={'display':'flex', 'justify-content':'space-between'}),
        ], style={
            'padding': '20px',
            'margin': '10px',
            'border': '1px solid #e9ecef',
            'borderRadius': '5px',
            'backgroundColor': '#fff',
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'flex': '1',
            'display': 'flex', 
            'flex-direction': 'column'
        }),
       
        html.Div([
            html.H3('Anomalies', style={'textAlign': 'center', 'margin-bottom':'10px', 'margin-top':'5px'}),
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
                style_cell={'textAlign': 'center'},
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
                dbc.Col(html.Button(id='pause-anomalies-button', n_clicks=0, children=[html.I(className="fas fa-pause")]), width=2, align='start', style={'position': 'absolute', 'bottom': '70px'}),
                # dbc.Col(html.Button(id='download-anomalies-data', n_clicks=0, children=[html.I(className="fas fa-download")]), width=2, align='end')
            ], style={'display':'flex', 'justify-content':'space-between'}),
        ], style={
            'padding': '20px',
            'margin': '10px',
            'border': '1px solid #e9ecef',
            'borderRadius': '5px',
            'backgroundColor': '#fff',
            'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
            'flex': '1',
            'display': 'flex', 
            'flex-direction': 'column'
        }),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'stretch', 'min-height':'620px'}),
    # Interval component for periodic callbacks
    dcc.Interval(id='interval-update', interval=1000, n_intervals=0)
])


if __name__ == '__main__':
    app.run_server(debug=False)
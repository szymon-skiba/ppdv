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
from datetime import datetime
from dash import dash_table

server = Flask(__name__)

FA = "https://use.fontawesome.com/releases/v5.15.1/css/all.css"
external_stylesheets = [FA]


# Initialize Redis client
# Replace 'localhost' and '6379' with your Redis server's address and port
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)


def fetch_and_store_data():
    while True:
        for person_id in range(1, 7):  # IDs from 1 to 6
            try:
                response = requests.get(f'http://tesla.iem.pw.edu.pl:9080/v2/monitor/{person_id}')
                if response.status_code == 200:
                    data = response.json()
                    timestamp = datetime.utcnow().isoformat()  # Get current UTC time in ISO format
                    data_with_timestamp = {'timestamp': timestamp, 'data': data}

                    # Store data with expiration of 600 seconds (10 minutes)
                    redis_client.setex(f'person_{person_id}_data', 600, json.dumps(data_with_timestamp))

                    # Check for anomalies and store them separately without expiration
                    if any(sensor.get('anomaly', False) for sensor in data['trace']['sensors']):
                        # Create or append to a list for anomalies for the person
                        anomalies_key = f'person_{person_id}_anomalies'
                        redis_client.rpush(anomalies_key, json.dumps(data_with_timestamp))

            except requests.RequestException as e:
                print(f"Error fetching data for person {person_id}: {e}")
        time.sleep(1) 
        
data_fetch_thread = threading.Thread(target=fetch_and_store_data, daemon=True)
data_fetch_thread.start()

app = Dash(__name__, external_stylesheets=external_stylesheets)


app.layout = html.Div([
    # Header
    html.Div([
        html.H1('Feet Pressure Sensor Dashboard', style={'textAlign': 'center', 'color': '#000000', 'fontSize': '2.5em', 'margin':'0', 'padding-top':'20px', 'padding-bottom':'20px'}),
    ], style={'width': '100%', 'display': 'block'}),
    
    # Content
    html.Div([
        # Person selector and details
        html.Div([
            # Dropdown with user icon
            html.Div([
                html.I(className="fas fa-user", style={'marginRight': '10px'}),
                dcc.Dropdown(id='person-selector', style={'width': 'calc(100% - 30px)'})
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '20px'}),
            
            # Person details
            html.Div(id='person-details', style={'padding': '10px', 'borderRadius': '5px'})
        ], style={'padding': '20px', 'margin': '10px', 'border': '1px solid #e9ecef', 'borderRadius': '5px', 'backgroundColor': '#fff', 'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)', 'flex': '0.5'}),
        html.Div([
            html.H2('Pressure Points', style={'textAlign': 'center'}),
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
            html.H3('Anomalies', style={'textAlign': 'center', 'marginBottom': '10px'}),
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
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    },
                    {
                        "if": {"state": "selected"},
                        "backgroundColor": "inherit !important",
                        "border": "inherit !important",
                    }
                ],
                page_size=15,  # Number of rows visible per page
        ),
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
    
    # Interval component for periodic callbacks
    dcc.Interval(id='interval-update', interval=500, n_intervals=0)
])


@app.callback(
    Output('anomalies-table', 'data'),
    [Input('person-selector', 'value')],
    prevent_initial_call=True
)
def update_anomalies_table(person_id):
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
            row = {'timestamp': anomaly['timestamp']}
            row.update({sensor['name']: sensor['value'] for sensor in sensors_data})
            anomalies_data.append(row)
            
        # Sort by newest first
        sorted_anomalies = sorted(anomalies_data, key=lambda x: x['timestamp'], reverse=True)
        for row in sorted_anomalies:
        # Split the timestamp into date and time, remove microseconds
            date, time = row['timestamp'].split('T')
            time = time.split('.')[0]  # Keep only up to seconds
            row['timestamp'] = f"{date} {time}"
        
        return sorted_anomalies
    except Exception as e:
        print(f"Error fetching or processing anomalies: {e}")
        return []  # Return an empty list if there's an error



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
        return details
    else:
        return "Failed to load person details."

@app.callback(
    Output('person-selector', 'options'),
    Input('interval-update', 'n_intervals'),
    prevent_initial_call=True
)
def populate_person_options(n):
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

@app.callback(
    Output('feet-pressure', 'sensorData'),
    [Input('interval-update', 'n_intervals')],
    [State('person-selector', 'value')]
)
def update_pressure_data(n, person_id):
    if not person_id:
        return []
    
    # Fetch data from Redis instead of making a new request
    redis_data = redis_client.get(f'person_{person_id}_data')
    if redis_data:
        data = json.loads(redis_data)  # Parse JSON data from Redis
        data = data['data']
        if 'trace' in data and 'sensors' in data['trace']:
            formatted_data = [{'id': sensor['id'], 'name': sensor['name'], 'value': sensor['value']} for sensor in data['trace']['sensors']]
            return formatted_data

    return []


if __name__ == '__main__':
    app.run_server(debug=True)
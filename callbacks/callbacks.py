from dash import  html, Input, Output, State, ctx
import plotly.graph_objs as go
import requests
from dash.exceptions import PreventUpdate
import json
import pandas as pd
import plotly.express as px
import plotly.express as px
from datetime import datetime, timedelta
import pytz
import callbacks.shared_state as shared_state


def register_callbacks(app, redis_client):
    
    def get_last_3_minutes_anomalies_data(person_id):
        try:
            anomalies_key = f'person_{person_id}_anomalies'

            end_time = datetime.now(pytz.timezone('Europe/Warsaw'))
            start_time = end_time - timedelta(minutes=2)

            anomalies_records = redis_client.lrange(anomalies_key, 0, -1)
            anomalies_list = [json.loads(record) for record in anomalies_records]
            anomalies_df = pd.DataFrame(anomalies_list)
            
            anomalies_df['timestamp'] = pd.to_datetime(anomalies_df['timestamp']).dt.tz_localize('Europe/Warsaw')
            filtered_df = anomalies_df[(anomalies_df['timestamp'] >= start_time) ]

            return filtered_df
        except Exception:
            return pd.DataFrame()

    def get_last_3_minutes_data(person_id):
        sensor_data_key = f'person_{person_id}_data_list'

        end_time = datetime.now(pytz.timezone('Europe/Warsaw'))
        start_time = end_time - timedelta(minutes=2)

        sensor_data_records = redis_client.lrange(sensor_data_key, 0, -1)
        sensor_data_list = [json.loads(record) for record in sensor_data_records]
        sensor_df = pd.DataFrame(sensor_data_list)

        sensor_df['timestamp'] = pd.to_datetime(sensor_df['timestamp']).dt.tz_localize('Europe/Warsaw')
        filtered_df = sensor_df[(sensor_df['timestamp'] >= start_time)]
        
        return filtered_df

    @app.callback(
        Output('sensor-chart', 'figure'),
        [Input('interval-update', 'n_intervals'), 
        Input('person-selector', 'value')]
    )
    def update_sensor_chart(n, person_id):
        if not person_id:
            return go.Figure()

        sensor_data_df = get_last_3_minutes_data(person_id)
        if sensor_data_df.empty:
            return go.Figure()

        # Flatten the nested JSON structure
        exploded_records = []
        for index, row in sensor_data_df.iterrows():
            sensors = row['data']['trace']['sensors']
            for sensor in sensors:
                exploded_records.append({
                    'timestamp': row['timestamp'],
                    'sensor': sensor['name'],
                    'value': sensor['value']
                })
        sensor_records_df = pd.DataFrame(exploded_records)

        # Fetch anomalies data
        anomalies_df = get_last_3_minutes_anomalies_data(person_id)


        # Create the line chart
        fig = px.line(sensor_records_df, x='timestamp', y='value', color='sensor',
                    color_discrete_map={
                        'L0': '#808700', 'L1': '#d7e120', 'L2': '#f2ff00',
                        'R0': '#0017ff', 'R1': '#182183', 'R2': '#515fe9'  
                    })
        
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='lines',
            line=dict(color="red", width=2),
            name='Anomalies'
        ))

        # Add vertical lines for anomalies
        if not anomalies_df.empty and 'timestamp' in anomalies_df.columns:
            for anomaly_time in anomalies_df['timestamp']:
                fig.add_vline(x=anomaly_time, line_width=2, line_color="red")

        # Update layout
        fig.update_layout(
            xaxis_title='Time',
            yaxis_title='Sensor Value',
            yaxis=dict(range=[0, 1100]), # Assuming max_sensor_value is defined globally
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
        shared_state.toggle_sensor_refreshing()
        icon_class = "fas fa-play" if shared_state.is_sensor_refreshing_paused else "fas fa-pause"
        return html.I(className=icon_class)

    @app.callback(
        Output('pause-anomalies-button', 'children'),
        [Input('pause-anomalies-button', 'n_clicks')],
        prevent_initial_call=True
    )
    def toggle_anomalies_refreshing(n_clicks):
        shared_state.toggle_anomalies_refreshing()
        icon_class = "fas fa-play" if shared_state.is_anomalies_refreshing_paused else "fas fa-pause"
        return html.I(className=icon_class)


    @app.callback(
        Output('anomalies-table', 'data'),
        [Input('interval-update', 'n_intervals'), 
        Input('person-selector', 'value')]
    )
    def update_anomalies_table(n, person_id):
        if not person_id or shared_state.is_anomalies_refreshing_paused:
            raise PreventUpdate
        
        
        if not person_id:
            return []
        

        if not person_id:
            return []
        
        try:
            anomalies_key = f'person_{person_id}_anomalies'
            sensor_data_records = redis_client.lrange(anomalies_key, 0, -1)

            if not sensor_data_records:
                return []

            # Convert to DataFrame
            df = pd.DataFrame([json.loads(record) for record in sensor_data_records])
            df = df.assign(**{sensor['name']: sensor['value'] for record in df['data'] for sensor in record['trace']['sensors']})
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('Europe/Warsaw')

            # Sort by timestamp in descending order
            df_sorted = df.sort_values(by='timestamp', ascending=False)

            return df_sorted[['timestamp'] + [sensor['name'] for sensor in df['data'][0]['trace']['sensors']]].to_dict('records')
        except Exception as e:
            return []


    @app.callback(
        Output('sensors-table', 'data'),
        [Input('interval-update', 'n_intervals'), 
        Input('person-selector', 'value')],
        [State('sensors-table', 'data')],
    )
    def update_sensor_data_table(n, person_id, rows):
        if not person_id:
            raise PreventUpdate
        
        triggered_id = ctx.triggered_id 
        if triggered_id == 'person-selector' or rows == None :
            try:
                sensor_data_key = f'person_{person_id}_data_list'
                sensor_data_records = redis_client.lrange(sensor_data_key, 0, -1)

                if not sensor_data_records:
                    return []

                # Convert to DataFrame
                df = pd.DataFrame([json.loads(record) for record in sensor_data_records])
                df = df.assign(**{sensor['name']: sensor['value'] for record in df['data'] for sensor in record['trace']['sensors']})
                df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('Europe/Warsaw')

                # Sort by timestamp in descending order
                df_sorted = df.sort_values(by='timestamp', ascending=False)

                return df_sorted[['timestamp'] + [sensor['name'] for sensor in df['data'][0]['trace']['sensors']]].to_dict('records')
            except Exception as e:
                return []
        else:
            if shared_state.is_sensor_refreshing_paused:
                raise PreventUpdate
        
            last_record = redis_client.lrange(f'person_{person_id}_data_list', -1, -1)
            if not last_record:
                print(1)
                return rows

            # Deserialize the latest record
            new_data = json.loads(last_record[0])
            
            new_row = {'timestamp': pd.to_datetime(new_data['timestamp']).tz_localize('Europe/Warsaw')}
            for sensor in new_data['data']['trace']['sensors']:
                new_row[sensor['name']] = sensor['value']
                
            rows.insert(0, new_row)

            return rows

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
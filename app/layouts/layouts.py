from dash import html, dcc
import utils

def main_layout():
    return html.Div([
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
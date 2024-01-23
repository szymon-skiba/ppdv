from dash import Dash
import dash_bootstrap_components as dbc
import ppdv
from layouts import main_layout

external_stylesheets = [dbc.themes.BOOTSTRAP, "https://use.fontawesome.com/releases/v5.15.1/css/all.css"]

app = Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = main_layout

if __name__ == '__main__':
    app.run_server(debug=False)
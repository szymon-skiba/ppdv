is_sensor_refreshing_paused = False
is_anomalies_refreshing_paused = False

def toggle_sensor_refreshing():
    global is_sensor_refreshing_paused
    is_sensor_refreshing_paused = not is_sensor_refreshing_paused

def toggle_anomalies_refreshing():
    global is_anomalies_refreshing_paused
    is_anomalies_refreshing_paused = not is_anomalies_refreshing_paused
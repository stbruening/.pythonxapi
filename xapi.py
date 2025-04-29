import requests
import xml.etree.ElementTree as ET
import json
import csv
import os
import datetime
import pytz
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from jinja2 import Template
import urllib3
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging configuration
logging.basicConfig(
    filename='py-scripts/room_analytics.log',  # Definiert den Speicherort für das Logfile
    level=logging.INFO,  # Legt das Minimum an Log-Level fest (z.B. INFO, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Definiert das Format der Lognachrichten
)

# Define the path to the config file
config_file_path = 'py-scripts/config.json'

# Load configuration from JSON file
try:
    with open(config_file_path, 'r') as config_file:
        config = json.load(config_file)
    
       # Access the configuration values
        device_ip = config['device_ip']
        username = config['username']
        password = config['password']
        verify_ssl = False

        if not device_ip or not username or not password:
            raise ValueError("Incomplete configuration. Make sure 'device_ip', 'username', and 'password' are provided in the config file.")
except FileNotFoundError:
    logging.error(f"Config file '{config_file_path}' not found.")
except json.JSONDecodeError:
    logging.error(f"Error parsing config file '{config_file_path}'. Make sure it's properly formatted JSON.")
except ValueError as e:
    logging.error(str(e))

# API URLs
session_begin_url = f'http://{device_ip}/xmlapi/session/begin'
session_end_url = f'http://{device_ip}/xmlapi/session/end'
get_xml_url = f'http://{device_ip}/getxml?location='

# CSV File Path and Header
filename = 'py-scripts/room_analytics.csv'
headers = ['unit_name', 'room_occupied', 'people_count', 'occupation_level', 'ambient_noise', 'ambient_temp', 'relative_humi', 'sound_level', 'time_stamp']

# HTML Template
template_file_path = 'py-scripts/template.html'

session = requests.Session()

def create_session():
    # Starts a new session
    try:
        # sends a POST message to start the session
        response = session.post(session_begin_url, auth=(username, password), verify=verify_ssl, timeout=5)
        response.raise_for_status()  # Exception in case of a http error

        # If succesfull
        logging.info("Session started.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error while establishing the session: {e}")
        return False

def end_session():
    # Ends the session
    try:
        # sends a POST message, to end the session
        response = session.post(session_end_url, auth=(username, password), verify=verify_ssl, timeout=5)
        response.raise_for_status()  # Exception in case of a http error
        logging.info("Session closed")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error while closing the session: {e}")
    

def get_xstatus(path):
    # Requests the current environment data from device
    try:
        # url building
        url = get_xml_url + path
        
        # GET request for status
        response = session.get(url, auth=(username, password), verify=verify_ssl, timeout=5)
        response.raise_for_status()  # Exception in case of a http error

        # XML parsing
        xml_data = response.content
        root = ET.fromstring(xml_data)

        # Extracting data from XML
        people_count = int(root.find('.//RoomAnalytics/PeopleCount/Current').text or 0)
        people_capacity = int(root.find('.//RoomAnalytics/PeopleCount/Capacity').text or 0)
        ambient_noise = root.find('.//RoomAnalytics/AmbientNoise/Level/A').text or '0'
        ambient_temp = root.find('.//RoomAnalytics/AmbientTemperature').text or '0'
        relative_humi = root.find('.//RoomAnalytics/RelativeHumidity').text or '0'
        sound_level = root.find('.//RoomAnalytics/Sound/Level/A').text or '0'
        time_stamp_str = root.find('.//Time/SystemTime').text
        unit_name = root.find('.//SystemUnit/BroadcastName').text or 'unknown'

        # occupied or not?
        room_occupied = people_count > 0
        occupation_level = (people_count / people_capacity * 100) if people_capacity else 0
        
        # convert timestamp
        time_stamp = datetime.datetime.strptime(time_stamp_str, "%Y-%m-%dT%H:%M:%S%z")

        return unit_name, room_occupied, people_count, occupation_level, ambient_noise, ambient_temp, relative_humi, sound_level, time_stamp

    except Exception as e:
        logging.error(f"Error while requesting xstatus: {e}")
        return None
    
def render_html(data):
    # creates html file
    try:
        # Read template
        with open(template_file_path, 'r') as template_file:
            template_content = template_file.read()
        
        # Create Jinja2 template object
        template = Template(template_content)

        # Rendering html with variables
        rendered_html = template.render(
            unit_name=data[0],
            room_occupied=data[1],
            people_count=data[2],
            occupation_level=data[3],
            ambient_noise=data[4],
            ambient_temp=data[5],
            relative_humi=data[6],
            sound_level=data[7],
            time_stamp=data[8]
        )

        # Save rendered html in file
        output_file_path = 'py-scripts/room_analytics.html'
        with open(output_file_path, 'w') as output_file:
            output_file.write(rendered_html)
        logging.info("HTML file succesfully created.")
      
    except IOError as e:
        logging.error(f"Error while creating html file: {e}")
    except Exception as e:
        logging.error(f"Error while rendering html file: {e}")

def create_plots():
    # Creates diagrams of the last 24h and saves them as png files
    # Read csv data
    df = pd.read_csv(filename)

    # Filter data of last 24h
    start_time = datetime.datetime.now(pytz.timezone("Europe/Berlin")) - datetime.timedelta(hours=24)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'], format="%Y-%m-%d %H:%M:%S%z")
    filtered_data = df[df['time_stamp'] >= start_time]

    # columns to plot (except 'time_stamp' and 'unit_name')
    plot_columns = filtered_data.columns.difference(["time_stamp", "unit_name"])

    # List of plot files
    plot_files = []

    for column in plot_columns:
        # Diagramm erstellen
        plt.figure(figsize=(10, 6))
        plt.gca().set_facecolor('none')
        plt.tick_params(axis='x', colors='#008F5C')
        plt.tick_params(axis='y', colors='#008F5C')
        plt.gcf().set_facecolor('#212121')
        plt.subplots_adjust(bottom=0.2)
        plt.box(False)

        # Plotting
        plt.plot(filtered_data['time_stamp'], filtered_data[column], label=column, color='#0672EF')

        # Rotation x-axis-label
        plt.xticks(rotation=90)

        # header and axis-label
        plt.xlabel('Time', color='#008F5C')
        plt.ylabel('Value', color='#008F5C')
        plt.title(f'{column} last 24h', color='#008F5C')

        # Legend and grid
        plt.grid(True, color='#6E84A6')

        # Save diagram to png
        plot_file_path = f'py-scripts/{column}_diagram.png'
        plt.savefig(plot_file_path, dpi=300, transparent=True)
        plt.close()

        # add file path to list
        plot_files.append(plot_file_path)

    return plot_files

# Main program
if __name__ == "__main__":
    # If connection failed variables will be filled with 0 to have some data that could be written into the csv
    fallback_data = ['unknown', False, 0, 0, '0', '0', '0', '0', datetime.datetime.now(pytz.timezone("Europe/Berlin")).strftime("%Y-%m-%d %H:%M:%S%z")]

    # establish session
    connected = create_session()

    if connected:
        # if connected request xstatus
        room_analytics = get_xstatus('/Status/')

        if room_analytics:
            # verification that file exists
            file_exists = os.path.isfile(filename)

            # Open csv file in attached when file exists or in write mode if it not exists
            with open(filename, 'a' if file_exists else 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # Write headers if the file doesn't exist
                if not file_exists:
                    writer.writerow(headers)

                # Write data in csv
                writer.writerow(room_analytics)
            
            # plot diagrams
            plot_files = create_plots()

            # Render html
            render_html(room_analytics)
  

        # close session
        end_session()

    else:

        logging.error("Error: No connection to the device.")
         
        # verification that file exists
        file_exists = os.path.isfile(filename)

        # Open csv file in attached when file exists or in write mode if it not exists
        with open(filename, 'a' if file_exists else 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Write headers if the file doesn't exist
            if not file_exists:
                writer.writerow(headers)

            # Write fallback data in csv
            writer.writerow(fallback_data)
        
        # Diagramme erstellen und den Dateipfad zurückgeben
        plot_files = create_plots()

        # Render html with fallback data
        render_html(fallback_data)
 

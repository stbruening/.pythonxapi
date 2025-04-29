The idea was to have small python script that could access my Cisco Desk Pro to extract the environmental sensor data and visualize them in HTML Dashboard. Furthermore I was interested in some historical trends (last 24h) so save the values in a csv file.
When you hover over the dashboard cards a diagram of the data of the last 24hours will be displayed. The png files for the diagrams will be plotted each time the script is running.

I used my synology diskstation to host the script. I set a timer to let the script run every 5 mins. Because I usually shutdown the Desk Pro during non working hours I use some fallback data and write them in the CSV.

The code is written based on python 3.12

The HTML template has dark mode and a light mode, by default it should recognize your system setting for dark or light mode and use this mode accordingly.




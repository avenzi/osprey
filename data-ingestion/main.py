# Third-party module imports
import time
import socketserver
import http.server
from queue import Queue
from utils import Utils
from http.server import HTTPServer, BaseHTTPRequestHandler
import pymysql.cursors

# Codebase module imports
from audio_listener import AudioListener
from video_ingester import VideoIngester
from sense_listener import SenseListener
from thread import Thread
from database import Database
from session_monitor import SessionMonitor

# Create the SQL tables to store data if they don't already exist
database = Database()
database.ensure_schema()

session_handler = SessionMonitor()
session = session_handler.block_until_new_session()

db_connection, cursor = Database().get_connection()
sql = """SELECT id, INET_NTOA(IP), SessionId, SensorType FROM SessionSensor WHERE SessionId = %s;"""
cursor.execute(sql, (session["id"],))
session_sensors = cursor.fetchall()

sense_listener_thread = Thread({
    "http_server": HTTPServer(("0.0.0.0", 5510), SenseListener)
})
sense_listener_thread.start()

audio_listener_thread = Thread({
    "http_server": HTTPServer(("0.0.0.0", 5515), AudioListener) # Thread serves the HTTPServer instance forever
})
audio_listener_thread.start()

workers = []
for session_sensor in session_sensors:
    if session_sensor["SensorType"] == "PiCamera":
        url = "http://%s:%s/stream.mjpg" % (session_sensor["INET_NTOA(IP)"], 8000)
        
        video_ingester_thread = Thread({
            "runnable_instance": VideoIngester({ # Thread executes .run() on the provided object when .start() is called on the Thread
                    "url": url,
                    "session_id": session["id"],
                    "session_sensor": session_sensor
                }),
            "session_sensor": session_sensor
        })
        workers.append(video_ingester_thread)

for worker in workers:
    worker.start()


try:
    session_handler.block_until_end(session)
except KeyboardInterrupt:
    pass

print("Data Ingestion Layer Closed")
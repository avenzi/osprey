from listener import Listener
import time
import json
import requests
import os
#import cv2 # pip install opencv-python (also installs numpy)
# also 'sudo apt install python3-opencv' <- 800+ MB package
import numpy as np
from database import Database

# MySQL imports
import pymysql.cursors
# https://github.com/PyMySQL/PyMySQL

class VideoIngester:
    filepath_format = "data/%d/%d/%d/%s"
    filename_format = "frame-%d.jpg"
    chunk_size = 1024

    def __init__(self, data):
        self.url = data['url']
        self.session_id = data['session_id']
        self.session_sensor = data['session_sensor']
        self.sensor_id = self.session_sensor['id']

        self.data_directory_name = self.filepath_format.split("/")[0]
        self.has_data_dir = False
        self.session_dirs = []
        self.sensor_dirs = []
        self.data_directories = []
    
    def run(self, data):
        self.ensure_database_connection()
        self.fetch_mjpg()
    
    def ensure_database_connection(self):
        try:
            x = self.db_connection
        except Exception:
            self.db_connection, self.cursor = Database().get_connection()
    
    def write_frames_record(self, session_id, sensor_id, first_frame_timestamp, last_frame_timestamp,
        first_frame_number, last_frame_number, frames_metadata):
        
        compacted_json = json.dumps(frames_metadata, separators=(',', ':'), sort_keys=True)
        #print(compacted_json)

        sql = """INSERT INTO `VideoFrames` (`FirstFrameTimestamp`, `LastFrameTimestamp`, `FirstFrameNumber`, `LastFrameNumber`, `SessionId`, `SensorId`, `FramesMetadata`)
            VALUES (FROM_UNIXTIME(%s * 0.001), FROM_UNIXTIME(%s * 0.001), %s, %s, %s, %s, %s)"""
        
        self.cursor.execute(sql, (first_frame_timestamp, last_frame_timestamp, first_frame_number, last_frame_number, session_id, sensor_id, compacted_json))
        self.db_connection.commit()

        print("Committed record to database")
    
    def ensure_directories(self, session_id, sensor_id, directory_number):
        if not self.has_data_dir:
            if not os.path.exists(self.data_directory_name):
                os.mkdir(self.data_directory_name)
            self.has_data_dir = True
        
        if not session_id in self.session_dirs:
            session_dir = "%s/%d" % (self.data_directory_name, session_id)
            if not os.path.exists(session_dir):
                os.mkdir(session_dir)

            self.session_dirs.append(session_id)

        if not sensor_id in self.sensor_dirs:
            sensor_dir = "%s/%d/%d" % (self.data_directory_name, session_id, sensor_id)
            if not os.path.exists(sensor_dir):
                os.mkdir(sensor_dir)
            self.sensor_dirs.append(sensor_id)

        if not directory_number in self.data_directories:
            data_dir = "%s/%d/%d/%d" % (self.data_directory_name, session_id, sensor_id, directory_number)
            if not os.path.exists(data_dir):
                os.mkdir(data_dir)
            self.data_directories.append(directory_number)
    
    def get_and_ensure_filepath(self, session_id, sensor_id, directory_number, jpg_number):
        self.ensure_directories(session_id, sensor_id, directory_number)
        return self.filepath_format % (session_id, sensor_id, directory_number, self.filename_format % jpg_number)
    
    def fetch_mjpg(self):
        response = requests.get(self.url, stream=True) # TODO: add authentication #response = requests.get(self.url, auth=('user', 'password'), stream=True)
        if (response.status_code != 200):
            print("Failed to connect to video stream at %s" % self.url)
            return
        
        chunk_bytes = bytes()
        frames_metadata = {}
        frames_per_database_record = 5
        frames_per_directory = 5
        directory_number = 1
        current_record_frames_total = 0
        current_directory_frames_total = 0
        total_jpgs = 1
        first_frame_timestamp = 0
        first_frame_number = 1

        for chunk in response.iter_content(chunk_size=self.chunk_size):
            chunk_bytes += chunk

            a = chunk_bytes.find(b'\xff\xd8')
            b = chunk_bytes.find(b'\xff\xd9')

            if a != -1 and b != -1:
                jpg_bytes = chunk_bytes[a:b+2]
                header = chunk_bytes[0:a].decode("utf-8", "ignore")
                chunk_bytes = chunk_bytes[b+2:]
                
                header_name = "Timestamp: "
                frame_timestamp = header[header.find(header_name) + len(header_name):]
                frame_timestamp = float(frame_timestamp[:frame_timestamp.find('\n')].strip())
                #print(frame_timestamp)

                current_directory_frames_total = current_directory_frames_total + 1
                if current_directory_frames_total > frames_per_directory:
                    current_directory_frames_total = 1
                    directory_number = directory_number + 1

                frame_path = self.get_and_ensure_filepath(self.session_id, self.sensor_id, directory_number, total_jpgs)
                frame_metadata = {
                    'path': frame_path,
                    'time': frame_timestamp,
                    'frame_number': total_jpgs
                }
                frames_metadata[total_jpgs] = frame_metadata

                if len(frames_metadata) == 1:
                    first_frame_timestamp = frame_timestamp
                    first_frame_number = total_jpgs
                
                #print(frame_metadata['frame_number'])
                #print(frame_path)
                
                # Write the frame to the disk
                with open(frame_path, 'wb') as frame_file:
                    frame_file.write(jpg_bytes)
                

                current_record_frames_total = current_record_frames_total + 1
                if current_record_frames_total == frames_per_database_record:
                    current_record_frames_total = 0
                    self.write_frames_record(self.session_id, self.sensor_id, first_frame_timestamp, frame_timestamp, first_frame_number, total_jpgs, frames_metadata.copy())
                    frames_metadata.clear()

                total_jpgs = total_jpgs + 1

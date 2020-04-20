import time
import json
import os
import pymysql.cursors

from listener import Listener
from database import Database

class AudioListener(Listener):
    filepath_format = "data/%d/%d/%d/%s"
    filename_format = "frame-%d.mp3"

    has_init = False
    has_data_dir = False

    def ensure_init(self):
        if AudioListener.has_init == False:
            AudioListener.has_init = True
            self.init()
        
    def get_session_data(self):
        sql = """SELECT * FROM Session WHERE StartDate = (SELECT MAX(StartDate) FROM Session)"""
        self.cursor.execute(sql)
        active_session = self.cursor.fetchone()
        AudioListener.session_id = active_session['id']
    
    def get_sensor_data(self):
        sql = """SELECT id FROM SessionSensor WHERE SessionId = %s AND IP = INET_ATON(%s) AND SensorType = 'Microphone';"""
        self.cursor.execute(sql, (AudioListener.session_id, self.client_address[0]))
        AudioListener.sensor_id = self.cursor.fetchone()['id']
        self.ensure_sensor_data()
    
    def init(self):
        self.get_session_data()

        AudioListener.data_directory_name = self.filepath_format.split("/")[0]
        AudioListener.has_data_dir = False
        AudioListener.session_dirs = []
        AudioListener.sensor_dirs = []
        AudioListener.data_directories = []

        AudioListener.frames_metadata = {}
        AudioListener.frames_per_database_record = 2
        AudioListener.frames_per_directory = 10
        AudioListener.directory_number = {}
        AudioListener.current_record_frames_total = {}
        AudioListener.current_directory_frames_total = {}
        AudioListener.total_frames = {}
        AudioListener.first_frame_timestamp = {}
        AudioListener.first_frame_number = {}

    
    def ensure_directories(self, session_id, sensor_id, directory_number):
        if not AudioListener.has_data_dir:
            if not os.path.exists(AudioListener.data_directory_name):
                os.mkdir(AudioListener.data_directory_name)
            AudioListener.has_data_dir = True
        
        if not session_id in AudioListener.session_dirs:
            session_dir = "%s/%d" % (AudioListener.data_directory_name, session_id)
            if not os.path.exists(session_dir):
                os.mkdir(session_dir)
            AudioListener.session_dirs.append(session_id)

        if not sensor_id in AudioListener.sensor_dirs:
            sensor_dir = "%s/%d/%d" % (AudioListener.data_directory_name, session_id, sensor_id)
            if not os.path.exists(sensor_dir):
                os.mkdir(sensor_dir)
            AudioListener.sensor_dirs.append(sensor_id)

        if not directory_number in AudioListener.data_directories:
            data_dir = "%s/%d/%d/%d" % (AudioListener.data_directory_name, session_id, sensor_id, directory_number)
            if not os.path.exists(data_dir):
                os.mkdir(data_dir)
            AudioListener.data_directories.append(directory_number)
    
    def get_and_ensure_filepath(self, session_id, sensor_id, directory_number, frame_number):
        self.ensure_directories(session_id, sensor_id, directory_number)
        return self.filepath_format % (session_id, sensor_id, directory_number, self.filename_format % frame_number)

    def write_frames_record(self, session_id, sensor_id, first_frame_timestamp, last_frame_timestamp,
        first_frame_number, last_frame_number, frames_metadata):
        
        compacted_json = json.dumps(frames_metadata, separators=(',', ':'), sort_keys=True)

        sql = """INSERT INTO `AudioSegments` (`FirstSegmentTimestamp`, `LastSegmentTimestamp`, `FirstSegmentNumber`, `LastSegmentNumber`, `SessionId`, `SensorId`, `SegmentsMetadata`)
            VALUES (FROM_UNIXTIME(%s * 0.001), FROM_UNIXTIME(%s * 0.001), %s, %s, %s, %s, %s)"""
        
        self.cursor.execute(sql, (first_frame_timestamp, last_frame_timestamp, first_frame_number, last_frame_number, session_id, sensor_id, compacted_json))
        self.db_connection.commit()
    
    def ensure_sensor_data(self):
        if not self.sensor_id in AudioListener.current_directory_frames_total:
            AudioListener.current_directory_frames_total[self.sensor_id] = 0
        
        if not self.sensor_id in AudioListener.directory_number:
            AudioListener.directory_number[self.sensor_id] = 1
        
        if not self.sensor_id in AudioListener.total_frames:
            AudioListener.total_frames[self.sensor_id] = 1
        
        if not self.sensor_id in AudioListener.frames_metadata:
            AudioListener.frames_metadata[self.sensor_id] = {}

        if not self.sensor_id in AudioListener.first_frame_number:
            AudioListener.first_frame_number[self.sensor_id] = 1
        
        if not self.sensor_id in AudioListener.first_frame_timestamp:
            AudioListener.first_frame_timestamp[self.sensor_id] = 0
        
        if not self.sensor_id in AudioListener.current_record_frames_total:
            AudioListener.current_record_frames_total[self.sensor_id] = 0
        

    def post_request(self, headers, data):
        self.ensure_init()
        self.get_sensor_data()

        frame_timestamp = float(headers['timestamp'])
        
        AudioListener.current_directory_frames_total[self.sensor_id] = AudioListener.current_directory_frames_total[self.sensor_id] + 1
        if AudioListener.current_directory_frames_total[self.sensor_id] > AudioListener.frames_per_directory:
            AudioListener.current_directory_frames_total[self.sensor_id] = 1
            AudioListener.directory_number[self.sensor_id] = AudioListener.directory_number[self.sensor_id] + 1
        
        frame_path = self.get_and_ensure_filepath(AudioListener.session_id, AudioListener.sensor_id, AudioListener.directory_number[self.sensor_id], AudioListener.total_frames[self.sensor_id])
        frame_metadata = {
            'path': frame_path,
            'time': frame_timestamp,
            'frame_number': AudioListener.total_frames[self.sensor_id]
        }

        AudioListener.frames_metadata[self.sensor_id][AudioListener.total_frames[self.sensor_id]] = frame_metadata
        
        if len(AudioListener.frames_metadata[self.sensor_id]) == 1:
            AudioListener.first_frame_timestamp[self.sensor_id] = frame_timestamp
            AudioListener.first_frame_number[self.sensor_id] = AudioListener.total_frames[self.sensor_id]
        
        # Write the frame to the disk
        with open(frame_path, 'wb') as frame_file:
            frame_file.write(data)
        
        AudioListener.current_record_frames_total[self.sensor_id] = AudioListener.current_record_frames_total[self.sensor_id] + 1
        if AudioListener.current_record_frames_total[self.sensor_id] == AudioListener.frames_per_database_record:
            AudioListener.current_record_frames_total[self.sensor_id] = 0
            self.write_frames_record(AudioListener.session_id, AudioListener.sensor_id, AudioListener.first_frame_timestamp[self.sensor_id], frame_timestamp, AudioListener.first_frame_number[self.sensor_id], AudioListener.total_frames[self.sensor_id], AudioListener.frames_metadata[self.sensor_id].copy())
            AudioListener.frames_metadata[self.sensor_id].clear()

        AudioListener.total_frames[self.sensor_id] = AudioListener.total_frames[self.sensor_id] + 1
        

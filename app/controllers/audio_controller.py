from app.controllers.controller import Controller

from flask import Response, jsonify, request
import json
import os.path

class AudioController(Controller):
    ###############################################
    # serve_segment  : Prepares a Flask Response containing the bytes of an audio segment
    # Input         : timestamp int - timestamp of the segment
    # Input         : segment int - frame number of the segment
    # Input         : session int - the session id that the segment was recorded in
    # Input         : sensor int - the sensor id of the sensor that produced the segment
    # Outputs       : <response Flask> - a Flask response containing the bytes of the segment
    ###############################################
    def serve_segment(self, timestamp, segment, session, sensor):
        #------------------------------------------
        # Retrieve the metadata for the segment from the database
        #------------------------------------------
        sql = "SELECT * FROM AudioSegments WHERE SessionId = %s AND SensorId = %s AND %s BETWEEN FirstSegmentNumber AND LastSegmentNumber;"
        self.database_cursor.execute(sql, (session, sensor, segment))
        segments_record = self.database_cursor.fetchone()

        if segments_record is None:
            response = Response()
            response.headers.add('segment-number', segment)
            response.headers.add('found', 'no')
            return response

        segments_metadata = json.loads(segments_record[7])
        base_path = os.path.dirname(__file__) + '/../../data-ingestion/'

        segment_metadata = segments_metadata[str(segment)]
        timestamp = int(segment_metadata['time'])
        path = base_path + segment_metadata['path']

        response_bytes = bytes()
        with open(path, 'rb') as segment_file:
            response_bytes = segment_file.read()
        
        response = Response(
            response_bytes,
            200,
            mimetype='audio/mpeg',
            direct_passthrough=True,
        )
        response.headers.add('segment-number', segment)
        response.headers.add('segment-time', timestamp)
        response.headers.add('found', 'yes')

        return response
    
    def get_sensor_info(self):
        self.database_cursor.execute("""SELECT MAX(id) FROM Session""")
        session_id = self.database_cursor.fetchone()[0]
        identifier = request.form['identifier']

        sql = """SELECT id FROM SessionSensor WHERE SessionId = %s AND Name = %s"""
        self.database_cursor.execute(sql, (session_id, identifier))
        sensor_id = self.database_cursor.fetchone()[0]

        return jsonify({"session_id": session_id, "sensor_id": sensor_id})

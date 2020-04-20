from app.controllers.controller import Controller

from flask import Response
import json
import os.path

class AudioController(Controller):
    def serve_segment(self, timestamp, segment, session, sensor):
        segments_record = []

        sql = "SELECT * FROM AudioSegments WHERE SessionId = %s AND SensorId = %s AND %s BETWEEN FirstSegmentNumber AND LastSegmentNumber;"
        self.database_cursor.execute(sql, (session, sensor, segment))
        segments_record = self.database_cursor.fetchone()

        if segments_record is None:
            return Response()

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

        return response

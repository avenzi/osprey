from app.controllers.controller import Controller

from flask import Response
import json
import os.path

class VideoController(Controller):
    def serve_frame(self, frame, session, sensor):
        sql = "SELECT * FROM VideoFrames WHERE SessionId = %s AND SensorId = %s AND %s BETWEEN FirstFrameNumber AND LastFrameNumber;"
        self.database_cursor.execute(sql, (session, sensor, frame))

        frames_record = self.database_cursor.fetchone()
        last_frame_number = int(frames_record[4])
        frames_metadata = json.loads(frames_record[7])

        response_frames = []
        frame_metadata = frames_metadata[str(frame)]
        base_path = os.path.dirname(__file__) + '/../../data-ingestion/'
        path = base_path + frame_metadata['path']
        with open(path, 'rb') as frame_file:
            response_frames.append(frame_file.read())
        
        response_bytes = b"".join(response_frames)
        response = Response(
            response_bytes,
            200,
            mimetype='image/jpeg',
            direct_passthrough=True,
        )
        response.headers.add('Accept-Ranges', 'bytes')

        return response
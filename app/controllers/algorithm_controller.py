from app.controllers.controller import Controller
from app import app

from flask import Response, session, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os

class AlgorithmController(Controller):
    # Only .py files are allowed to be uploaded
    ALLOWED_EXTENSIONS = set(['py'])

    def handle_upload(self):
        algorithms = []
        runningAlgorithms = []
        user_id = session.get('user_id')

        # Checking that the POST request has the file part
        if 'file' not in request.files:
            return jsonify({'result' : 'No File Part'})

        file = request.files['file']

        # Checking that a file was selected
        if file.filename == '':
            return jsonify({'result' : 'No File Selected'})

        # Checking that the file name has an extension that is allowed
        if file and ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS):
            filename = secure_filename(file.filename)

            # Search Algorithm table for algorithm filename to get file path if it exists
            sql = """
                SELECT Path 
                FROM Algorithm 
                WHERE UserId = %s AND Name = %s;
            """
            self.database_cursor.execute(sql, (user_id, filename))
            path = self.database_cursor.fetchone()

            # If algorithm filename does not exist
            if path == None:
                # Get the path of the most recently uploaded algorithm pertaining to a user
                sql = """
                    SELECT Path
                    FROM Algorithm
                    WHERE UserId = %s
                    ORDER BY id DESC
                    LIMIT 1;
                """
                self.database_cursor.execute(sql, (user_id,))
                pth = self.database_cursor.fetchone()

                # If user has no recently uploaded algorithm
                if pth == None:
                    sql = """ 
                        INSERT INTO Algorithm
                        (UserId, Status, Name, Path)
                        VALUES (%s, %s, %s, %s);
                    """
                    self.database_cursor.execute(sql, (user_id, 0, filename, str(user_id) + "-1"))
                    self.database_connection.commit()

                    file.save(os.path.join(app.config['UPLOADS_FOLDER'], str(user_id) + "-1.py"))

                # If user has a recently uploaded algorithm
                else:
                    alg_num = int(pth[0].split('-')[1]) + 1
                    sql = """ 
                        INSERT INTO Algorithm
                        (UserId, Status, Name, Path)
                        VALUES (%s, %s, %s, %s);
                    """
                    self.database_cursor.execute(sql, (user_id, 0, filename, str(user_id) + "-" + str(alg_num)))
                    self.database_connection.commit()

                    file.save(os.path.join(app.config['UPLOADS_FOLDER'], str(user_id) + "-" + str(alg_num) + ".py"))
                
            # If algorithm filename exists
            else:
                # TODO: Algorithm overwrite prompt

                # Update the old file path
                file.save(os.path.join(app.config['UPLOADS_FOLDER'], path[0] + ".py"))
            
            # Search Algorithm table for filenames of algorithms pertaining to a user
            sql = """
                SELECT Status, Name 
                FROM Algorithm 
                WHERE UserId = %s;
            """            
            self.database_cursor.execute(sql, (user_id,))
            algs = self.database_cursor.fetchall()

            # TODO: move to View class
            for alg in algs:
                if alg[0] == 1:
                    runningAlgorithms.append(alg[1])
                algorithms.append(alg[1])

            return render_template('snippets/uploads_list_snippet.html', algorithms=algorithms, runningAlgorithms=runningAlgorithms)

        return jsonify({'result' : 'File Extension Not Allowed'})
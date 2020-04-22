from app.controllers.controller import Controller
from app import app, mysql

from app.main.program import Program
from queue import Queue

from flask import Response, session, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import os

class AlgorithmController(Controller):
    # Only .py files are allowed to be uploaded
    ALLOWED_EXTENSIONS = set(["py"])

    def download_boilerplate(self):
        return send_from_directory(directory=app.config["DOWNLOADS_FOLDER"], filename="boilerplate.py", as_attachment=True)

    def handle_upload(self):
        algorithms = []
        runningAlgorithms = []
        user_id = session.get("user_id")

        # Checking that the POST request has the file part
        if "file" not in request.files:
            return jsonify({"result" : "No File Part"})

        file = request.files["file"]

        # Checking that a file was selected
        if file.filename == "":
            return jsonify({"result" : "No File Selected"})

        # Checking that the file name has an extension that is allowed
        if file and ("." in file.filename and file.filename.rsplit(".", 1)[1].lower() in self.ALLOWED_EXTENSIONS):
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

                    file.save(os.path.join(app.config["UPLOADS_FOLDER"], str(user_id) + "-1.py"))

                # If user has a recently uploaded algorithm
                else:
                    alg_num = int(pth[0].split("-")[1]) + 1
                    sql = """ 
                        INSERT INTO Algorithm
                        (UserId, Status, Name, Path)
                        VALUES (%s, %s, %s, %s);
                    """
                    self.database_cursor.execute(sql, (user_id, 0, filename, str(user_id) + "-" + str(alg_num)))
                    self.database_connection.commit()

                    file.save(os.path.join(app.config["UPLOADS_FOLDER"], str(user_id) + "-" + str(alg_num) + ".py"))
                
            # If algorithm filename exists
            else:

                # Update the old file path
                file.save(os.path.join(app.config["UPLOADS_FOLDER"], path[0] + ".py"))
            
            # Search Algorithm table for filenames of algorithms pertaining to a user
            sql = """
                SELECT Status, Name 
                FROM Algorithm 
                WHERE UserId = %s;
            """            
            self.database_cursor.execute(sql, (user_id,))
            algs = self.database_cursor.fetchall()

            for alg in algs:
                if alg[0] == 1:
                    runningAlgorithms.append(alg[1])
                algorithms.append(alg[1])

            return render_template("snippets/uploads_list_snippet.html", algorithms=algorithms, runningAlgorithms=runningAlgorithms)

        return jsonify({"result" : "File Extension Not Allowed"})

    def handle_algorithm(self):
        algorithms = []
        runningAlgorithms = []
        database_cursor = mysql.connection.cursor()
        filename = request.form["filename"] + ".py"
        buttonPressed = request.form["button"]
        user_id = session.get("user_id")

        if buttonPressed == "run":
            # Search Algorithm table for running algorithms pertaining to a user
            sql = """
                SELECT Name
                FROM Algorithm
                WHERE UserId = %s AND Status = 1;
            """
            database_cursor.execute(sql, (user_id,))
            algs = database_cursor.fetchall()

            for alg in algs:
                runningAlgorithms.append(alg[0])

            # Get the actual filename of the file to run
            sql = """
                SELECT Path
                FROM Algorithm
                WHERE UserId = %s AND Name = %s;
            """
            database_cursor.execute(sql, (user_id, filename))
            filename_actual = database_cursor.fetchone()[0] + ".py"

            if filename not in runningAlgorithms:
                program_thread = Program(Queue(), args=(True, filename_actual, user_id))
                program_thread.start()
            
                # Set Status of file to 1 for running
                sql = """
                    UPDATE Algorithm
                    SET Status = 1
                    WHERE UserId = %s AND Name = %s;
                """
                database_cursor.execute(sql, (user_id, filename))
                mysql.connection.commit()

                # Search Algorithm table for filenames of algorithms pertaining to a user
                sql = """
                    SELECT Status, Name 
                    FROM Algorithm 
                    WHERE UserId = %s;
                """            
                database_cursor.execute(sql, (user_id,))
                algs = database_cursor.fetchall()

                runningAlgs = []

                for alg in algs:
                    if alg[0] == 1:
                        runningAlgs.append(alg[1])
                    algorithms.append(alg[1])

                return render_template("snippets/uploads_list_snippet.html", algorithms = algorithms, runningAlgorithms = runningAlgs)

            else:       
                # Set Status of file to 0 for not running
                sql = """
                    UPDATE Algorithm
                    SET Status = 0
                    WHERE UserId = %s AND Name = %s;
                """
                database_cursor.execute(sql, (user_id, filename))
                mysql.connection.commit()

                # Search Algorithm table for filenames of algorithms pertaining to a user
                sql = """
                    SELECT Status, Name 
                    FROM Algorithm 
                    WHERE UserId = %s;
                """            
                database_cursor.execute(sql, (user_id,))
                algs = database_cursor.fetchall()

                runningAlgs = []

                for alg in algs:
                    if alg[0] == 1:
                        runningAlgs.append(alg[1])
                    algorithms.append(alg[1])

                return render_template("snippets/uploads_list_snippet.html", algorithms = algorithms, runningAlgorithms = runningAlgs)

        elif buttonPressed == "view":
            # Search Algorithm table for algorithm filename to get file path
            sql = """
                SELECT Path 
                FROM Algorithm 
                WHERE UserId = %s AND Name = %s;
            """
            database_cursor.execute(sql, (user_id, filename))
            path = database_cursor.fetchone()[0]

            f = open(os.path.join(app.config["UPLOADS_FOLDER"], path + ".py"), "r")
            content = f.read()
            f.close()
            return render_template("snippets/uploads_view_snippet.html", content = content, filename = filename)

        elif buttonPressed == "delete":
            return render_template("snippets/uploads_delete_snippet.html")

        elif buttonPressed == "delete_confirm":
            # Search Algorithm table for algorithm filename to get file path
            sql = """
                SELECT Path 
                FROM Algorithm 
                WHERE UserId = %s AND Name = %s;
            """
            database_cursor.execute(sql, (user_id, filename))
            path = database_cursor.fetchone()[0]

            with os.scandir(os.path.join(app.config["UPLOADS_FOLDER"])) as entries:
                for entry in entries:
                    if entry.is_file() and (entry.name == (path + ".py")):
                        os.remove(os.path.join(app.config["UPLOADS_FOLDER"], path + ".py"))

            sql = """
                DELETE FROM Algorithm
                WHERE UserId = %s AND Name = %s;
            """
            database_cursor.execute(sql, (user_id, filename))
            mysql.connection.commit()

            # Search Algorithm table for filenames of algorithms pertaining to a user
            sql = """
                SELECT Status, Name 
                FROM Algorithm 
                WHERE UserId = %s;
            """            
            database_cursor.execute(sql, (user_id,))
            algs = database_cursor.fetchall()

            runningAlgs = []

            for alg in algs:
                if alg[0] == 1:
                    runningAlgs.append(alg[1])
                algorithms.append(alg[1])

            return render_template("snippets/uploads_list_snippet.html", algorithms = algorithms, runningAlgorithms = runningAlgs)
                        
        return jsonify({"result" : "Button Not Handled"})
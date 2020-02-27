import io
import time
import datetime
import socket
import struct
from PIL import Image
from PIL import ImageFile
import PIL

# MySQL Create example
#sql = """CREATE TABLE `users` (
#`id` int(11) NOT NULL AUTO_INCREMENT,
#`email` varchar(255) COLLATE utf8_bin NOT NULL,
#`password` varchar(255) COLLATE utf8_bin NOT NULL,
#PRIMARY KEY (`id`))"""
#cursor.execute(sql)

# MySQL Insertion example
#cursor = db_connection.cursor()
#sql = "INSERT INTO `users` (`email`, `password`) VALUES (%s, %s)"
#cursor.execute(sql, ('devolde2@msu.edu', 'very-secret'))
#db_connection.commit()




# MySQL imports
import pymysql.cursors
# https://github.com/PyMySQL/PyMySQL

def clear_tokens():
    print("ATTEMPT CLEARED TOKENS")
    sql = """DELETE FROM Token"""
    cursor.execute(sql)
    db_connection.commit()
    print("CLEARED TOKENS")

def get_latest_token_value(cursor):
    sql = """SELECT Value FROM Token WHERE id = (SELECT MAX(id) FROM Token)"""
    cursor.execute(sql)
    #db_connection.commit()
    result = cursor.fetchone()

    print("result: ", result)

    # DELETE THIS LINE - ITS FOR DEBUG
    if 1==1:
        return "START"

    if result == None or len(result) == 0:
        return None
    else:
        return result['Value']

def listen_and_work(cursor):
    # Start a socket listening for connections
    server_socket = socket.socket()
    server_socket.bind(('0.0.0.0', 5566))
    server_socket.listen(0)
    print("Listening on port 5566")

    # Create the MySQL connection after the client connects
    # move db_connection initialization here

    # Accept a single connection and make a file-like object out of it (raspberry pi started streaming)
    connection, addr = server_socket.accept() #s[0].makefile('rb')


    #sql = """DROP TABLE IF EXISTS `Session`"""
    #cursor.execute(sql)
    #db_connection.commit()
    #if 1 == 1:
    #    raise Exception('spam', 'eggs')

    sql = """CREATE TABLE IF NOT EXISTS `Session` (id INT(11) NOT NULL AUTO_INCREMENT, StartDate DATETIME(3) NOT NULL, EndDate DATETIME(3) NULL, PRIMARY KEY (id));"""
    cursor.execute(sql)
    db_connection.commit()

    #sql = """DROP TABLE IF EXISTS `VideoFrame`"""
    #cursor.execute(sql)
    #db_connection.commit()

    sql = """CREATE TABLE IF NOT EXISTS `VideoFrame` (id int(11) NOT NULL AUTO_INCREMENT, Time DATETIME(3) NOT NULL, SessionId INT(11) NOT NULL, Frame INT(11) NOT NULL, Path VARCHAR(255) NOT NULL, PRIMARY KEY (id));"""
    cursor.execute(sql)
    db_connection.commit()

    # Get the next session id
    sql = """SELECT id FROM Session WHERE id = (SELECT MAX(id) FROM Session)"""
    cursor.execute(sql)
    result = cursor.fetchone()
    #print(result)
    session_id = 1 if result == None else result['id'] + 1
    print("Next Session id: ", session_id)
    video_frame = 1 # the Frame column of VideoFrame

    # Insert a new Session
    sql = "INSERT INTO Session (`StartDate`) VALUES (NOW(3))"
    #params = (datetime.datetime.utcnow(), )
    #cursor.execute(sql, params)
    cursor.execute(sql)
    db_connection.commit()


    #sql = "SELECT id FROM VideoFrame WHERE id = (SELECT MAX(id) FROM VideoFrame)"
    #cursor.execute(sql)
    #result = cursor.fetchone() #(235,)
    #session_frame = result[0]

    token_check_ticks = 0

    try:
        while True:
            if (1 == 2):
                token_check_ticks = token_check_ticks + 1
                if token_check_ticks % 15 == 0:
                    token_value = get_latest_token_value(cursor)

                    if token_value != None and token_value == "STOP":
                        print("STOP TOKEN RECEIVED")
                        clear_tokens()
                        #break
            
            path = "/root/capstone-site/site/static/video/" + str(session_id) + "-" + str(video_frame) + ".mp4"
            print("1")
            
            buffer = connection.recv(1024)
            print(len(buffer))
            if len(buffer) == 0:
                # TODO: check if connection is alive, otherwise close connection
                time.sleep(0.1)
                continue
            print("2")

            # using 'with', we don't need to explicitly close files
            with open(path, "wb") as video:
                i = 0
                while buffer:                
                    video.write(buffer)
                    if i % 250 == 0:
                        print("buffer {0}".format(i))
                    i += 1
                    
                    if (buffer[-9:] == b"FinalByte"):
                        break
                    buffer = connection.recv(1024)

            print("Done reading bytes..")

            ### image_stream.getvalue() # image bytes as string
            # Construct a stream to hold the image data and read the image data from the connection
            if (1 == 2):
                image_stream = io.BytesIO()
                image_stream.write(connection.read(image_len))
                image_stream.seek(0) # remove this????????/ Rewind the stream, open it as an image with PIL and do some processing on it
                #####print("image as string:", image_stream.getvalue())
                image = Image.open(image_stream)
                image.load()
                #####print('Image is %dx%d' % image.size)
                #####image.verify() # this causes save() to fail
                #####print('Image is verified')
                f = open(path, 'w')
                image.save(f)
                #print("wrote actual image to disk")

            # Insert the data into the database
            # TODO: make path configurable (environment variable?)
            cursor = db_connection.cursor()
            sql = "INSERT INTO `VideoFrame` (`SessionId`, `Time`, `Frame`, `Path`) VALUES (%s, NOW(3), %s, %s)"
            cursor.execute(sql, (session_id, video_frame, path))
            db_connection.commit()

            #print("wrote image data to db")

            video_frame = video_frame + 1
            if video_frame % 25 == 0:
                print("Frames captured: ", video_frame)
    finally:
        #db_connection.close()
        print("hello?")
        connection.close()
        server_socket.close()


db_connection = pymysql.connect(host='localhost',
    user='CapstoneMySQLUser',
    password='CapstoneMySQLUserDbPw',
    db='CapstoneData',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True)

while True:
    time.sleep(2)

    cursor = db_connection.cursor()

    try:
        token_value = get_latest_token_value(cursor)

        print("Token value: ", token_value)

        if token_value == "None":
            print("Token table does not have records")
            continue
        elif token_value == "START":
            pass
            clear_tokens()
            print("---STARTING---")
            time.sleep(1)
            listen_and_work(cursor)
    except Exception as _e:
        print("Caught Exception:", _e)
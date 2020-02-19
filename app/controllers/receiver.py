import io
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

# 1. Create table if not exists Video
# 2. Create an id for the video data coming in to this socket/port so that we can retrieve it among other records
# ^ New table or just generate the id in this script? (in this script for now)
# https://github.com/PyMySQL/PyMySQL

db_connection = pymysql.connect(host='localhost',
    user='CapstoneMySQLUser',
    password='CapstoneMySQLUserDbPw',
    db='CapstoneData',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor)


class Receiver():

    def StartReceiving(self):

        try:
            cursor = db_connection.cursor()

            # Read a single record
            #sql = "SELECT `id`, `password` FROM `users` WHERE `email`=%s"
            sql = "SELECT * FROM `users` WHERE `email`=%s"
            cursor.execute(sql, ('devolde2@msu.edu',))
            result = cursor.fetchone()
            #print(result)

            # connection is not autocommit by default. So you must commit to save your changes:
            #db_connection.commit()
        except:
            print("MySQL exception")

        # Start a socket listening for connections
        server_socket = socket.socket()
        server_socket.bind(('0.0.0.0', 5566))
        server_socket.listen(0)
        print("Listening on port 5566")

        # Create the MySQL connection after the client connects
        # move db_connection initialization here

        # Accept a single connection and make a file-like object out of it
        connection = server_socket.accept()[0].makefile('rb')
        try:
            index = 1
            max_index = 500
            while True:
                # Read the length of the image as a 32-bit unsigned int. If the
                # length is zero, quit the loop
                image_len = struct.unpack('<L', connection.read(struct.calcsize('<L')))[0]
                if not image_len:
                    break
                # Construct a stream to hold the image data and read the image
                # data from the connection
                image_stream = io.BytesIO()
                image_stream.write(connection.read(image_len))
                # Rewind the stream, open it as an image with PIL and do some
                # processing on it
                image_stream.seek(0)
                image = Image.open(image_stream)
                print('Image is %dx%d' % image.size)
                #image.verify() # does this causes save() to fail
                #print('Image is verified')
                path = "/root/capstone-site/app/static/video/" + str(index) + ".jpg"
                image.load()
                f = open(path, 'w')
                image.save(f)

                print("wrote: ", index)

                index = index + 1
                if index > max_index:
                    index = 1
        finally:
            db_connection.close()
            connection.close()
            server_socket.close()


    def StopReceiving(self):
        pass
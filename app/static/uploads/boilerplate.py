"""This code is run in a separate thread as the Flask web application, and is outside of the Flask web application context"""

import os
import time
import pymysql.cursors

# Set up database connection
db_connection = pymysql.connect(host='localhost',
    user='CapstoneMySQLUser',
    password='CapstoneMySQLUserDbPw',
    db='CapstoneData',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True)

cursor = db_connection.cursor()
user_id = ""

# Get user id from tmp file then remove it
if os.path.exists("app/static/tempfiles/tmp.txt"):
    f = open("app/static/tempfiles/tmp.txt", "r")
    user_id = f.readlines()[0].strip()
    f.close()
    os.remove("app/static/tempfiles/tmp.txt")
else:
    print("The file does not exist")


# Runs indfinitely until process has ended from the UI, return, or error
while True:

    # Write data to database
    sql = "INSERT INTO `eventlog` (`user_id`, `alert_time`, `alert_type`, `alert_message`) VALUES (%s, NOW(), %s, %s)"
    cursor.execute(sql, (int(user_id), "Audio", "Audio Alert"))
    db_connection.commit()

    time.sleep(1)    
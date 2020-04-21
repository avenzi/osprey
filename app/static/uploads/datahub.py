"""DataHub Algorithm Tool

This module allows the user to interact with DataHub from within the user's uploaded algorithm.

This module requires that `json`, `pymysql.cursors`, `datetime`, `skimage`, and `numpy` be installed within the Python environment
this module is running in.
"""

import json
import pymysql.cursors
from datetime import datetime

# TO INSTALL SKIMAGE AS ITS DEPENDENCIES AND NUMPY, GO TO: https://scikit-image.org/docs/stable/install.html
# INSTALL ALL REQUIRED DEPENDENCIES: sudo apt-get install python3-matplotlib python3-numpy python3-pil python3-scipy python3-tk
# INSTALL SUITABLE COMPILERS: sudo apt-get install build-essential cython3
# PIP INSTALLATION: pip3 install scikit-image
from skimage import io, img_as_float
import numpy as np

# Set up database connection
db_connection = pymysql.connect(host='localhost',
    user='CapstoneMySQLUser',
    password='CapstoneMySQLUserDbPw',
    db='CapstoneData',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True)

cursor = db_connection.cursor()


def update_eventlog(filename, alert_type = '', alert_message= ''):
    """Updates the eventlog

    Args:
        filename (str): The name of the file using this function
        alert_type (str): The type of alert to be entered into the eventlog (default is '')
        alert_message (str): The message to be entered into the eventlog (default is '')

    Returns:
        None
    """

    # The id associated with a user
    user_id = int(filename.split('/')[6].split('-')[0])

    sql = """
        INSERT INTO eventlog 
        (user_id, alert_time, alert_type, alert_message) 
        VALUES (%s, NOW(), %s, %s);
    """
    cursor.execute(sql, (user_id, alert_type, alert_message))
    db_connection.commit()

def get_algorithm_status(filename):
    """Gets the status of an algorithm to determine if it is supposed to be running or not

    Args:
        filename (str): The name of the file using this function

    Returns:
        int: 1 if the algorithm is supposed to be running, 0 if it is not
    """
    
    # The id associated with a user
    user_id = int(filename.split('/')[6].split('-')[0])
    # The path of the file using this function
    path = str(filename.split('/')[6].split('.')[0])

    sql = """
        SELECT Status 
        FROM Algorithm 
        WHERE UserId = %s AND Path = %s;
    """
    cursor.execute(sql, (user_id, path))
    return cursor.fetchone()['Status']

def get_sense_data(ip, time_start = '', time_end = ''):
    """Gets temperature, pressure, and humidity data from a specified Sense HAT

    Args:
        sense_num (int): The Sense HAT device to get sense data from
        time_start (str): The time to start gathering sense data. For example, format should be like '03/24/20 22:40:19.000' 
            (default is '')
        time_end (str): The time to end gathering sense data. For example, format should be like '03/24/20 22:40:19.000' 
            (default is '')

    Returns:
        list: a list of dictionaries containing sense data at a point in time
    """

    #-------------------------------------------------------------------------------------------------
    # If time_start and time_end are not specified, get the latest data for the specified Sense HAT
    #-------------------------------------------------------------------------------------------------
    if (len(time_start) == 0) and (len(time_end) == 0):

        sql = """
            SELECT Time, Temp, Press, Humid
            FROM Sense
            WHERE IP = INET_ATON(%s)
            ORDER BY Time DESC;
        """
        cursor.execute(sql, (ip,))

        return [cursor.fetchone()]

    #-------------------------------------------------------------------------------------------------
    # If time_start is specified and time_end is not, get all data from time_start and on for the 
    # specified Sense HAT
    #-------------------------------------------------------------------------------------------------
    elif (len(time_start) > 0) and (len(time_end) == 0):

        # Converting string to datetime
        time_start_datetime_object = datetime.strptime(time_start, '%m/%d/%y %H:%M:%S.%f')

        sql = """
            SELECT Time, Temp, Press, Humid
            FROM Sense
            WHERE IP = INET_ATON(%s) AND Time >= %s;
        """
        cursor.execute(sql, (ip, time_start_datetime_object))
        
        return cursor.fetchall()

    #-------------------------------------------------------------------------------------------------
    # If time_start and time_end are both specified, get all data from between time_start and time_end 
    # for the specified Sense HAT
    #-------------------------------------------------------------------------------------------------
    elif (len(time_start) > 0) and (len(time_end) > 0):

        # Converting strings to datetime
        time_start_datetime_object = datetime.strptime(time_start, '%m/%d/%y %H:%M:%S.%f')
        time_end_datetime_object = datetime.strptime(time_end, '%m/%d/%y %H:%M:%S.%f')

        sql = """
            SELECT Time, Temp, Press, Humid
            FROM Sense
            WHERE IP = INET_ATON(%s) AND Time >= %s AND Time <= %s;
        """
        cursor.execute(sql, (ip, time_start_datetime_object, time_end_datetime_object))
        
        return cursor.fetchall()

def get_video_data(ip):
    """

    Args:
        ip (str): The IP address for the camera

    Returns:
        ...: ...
    """

    sql = """
        SELECT LastFrameTimestamp, FirstFrameNumber, LastFrameNumber, FramesMetadata
        FROM SessionSensor INNER JOIN VideoFrames
        ON SessionSensor.id = VideoFrames.SensorId
        WHERE SessionSensor.IP = INET_ATON(%s)
        ORDER BY LastFrameTimestamp DESC;
    """
    cursor.execute(sql, (ip,))
    metadata = cursor.fetchone()
    return metadata

def get_pix_intensity_percentage(metadata):
    """

    Args:
        metadata (dict): ...

    Returns:
        ...: ...
    """

    first_frame_number = metadata['FirstFrameNumber']               
    last_frame_number = metadata['LastFrameNumber']    
    
    # Contains "time", "frame_number", and "path" for frames in a segment
    frames_metadata = metadata['FramesMetadata']         

    # Converting frames_metadata to JSON format    
    json_frames_metadata = json.loads(frames_metadata)

    # Contains the pixel intensities for frames in a segment
    intensities = []                                                

    for i in range (first_frame_number, last_frame_number + 1):
        path = json_frames_metadata[str(i)]["path"]    
        full_path = "/root/capstone-site/data-ingestion/" + path

        # Get mean of each frame in a segment, and add it to the intensities list
        image = io.imread(full_path)
        image = img_as_float(image)
        mean =  np.mean(image)
        intensities.append(mean)

    # Return the mean of the means of each frame in a segment
    return str(round(np.mean(intensities) * 100, 2)) + ' %'


def get_pix_intensity_value(metadata):
    """

    Args:
        metadata (dict): ...

    Returns:
        ...: ...
    """

    first_frame_number = metadata['FirstFrameNumber']               
    last_frame_number = metadata['LastFrameNumber']    
    
    # Contains "time", "frame_number", and "path" for frames in a segment
    frames_metadata = metadata['FramesMetadata']         

    # Converting frames_metadata to JSON format    
    json_frames_metadata = json.loads(frames_metadata)

    # Contains the pixel intensities for frames in a segment
    intensities = []                                                

    for i in range (first_frame_number, last_frame_number + 1):
        path = json_frames_metadata[str(i)]["path"]    
        full_path = "/root/capstone-site/data-ingestion/" + path

        # Get mean of each frame in a segment, and add it to the intensities list
        image = io.imread(full_path)
        mean =  np.mean(image)
        intensities.append(mean)

    # Return the mean of the means of each frame in a segment
    return str(round(np.mean(intensities), 2))
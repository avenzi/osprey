"""Code in this file should be built off of to ensure that data can be interacted with properly

update_eventlog(filename, alert_type = '', alert_message = ''): Updates the eventlog. filename must always be __file__
    Args:
        filename (str): The name of the file using this function
        alert_type (str): The type of alert to be entered into the eventlog (default is '')
        alert_message (str): The message to be entered into the eventlog (default is '')
    
    Returns:
        None


get_algorithm_status(filename): Gets the status of an algorithm to determine if it is supposed to be running or not. 
    filename must always be __file__
    Args:
        filename (str): The name of the file using this function

    Returns:
        int: 1 if the algorithm is supposed to be running, 0 if it is not


get_sense_data(sense_num, time_start = '', time_end = ''): Gets temperature, pressure, and humidity data from a specified 
    Sense HAT
    Args:
        sense_num (int): The Sense HAT device to get sense data from
        time_start (str): The time to start gathering sense data. For example, format should be like '03/24/20 22:40:19.000' 
            (default is '')
        time_end (str): The time to end gathering sense data. For example, format should be like '03/24/20 22:40:19.000' 
            (default is '')

    Returns:
        list: a list of dictionaries containing sense data at a point in time

    Examples:
        #----------------------------------------------------------------------------------------------------------
        # If time_start and time_end are not specified, the latest data for the specified Sense HAT is returned
        #----------------------------------------------------------------------------------------------------------
        >>> datahub.get_sense_data(1)
        [{'Time': datetime.datetime(2020, 3, 24, 22, 40, 27, 704000), 'Temp': 71.58, 'Press': 989.02, 'Humid': 26.85}]

        #----------------------------------------------------------------------------------------------------------
        # If time_start is specified and time_end is not, all data from time_start and on for the 
        # specified Sense HAT is returned
        #----------------------------------------------------------------------------------------------------------
        >>> datahub.get_sense_data(1, '03/24/20 22:40:24.448')
        [{'Time': datetime.datetime(2020, 3, 24, 22, 40, 24, 448000), 'Temp': 71.74, 'Press': 989.02, 'Humid': 26.69}, 
        {'Time': datetime.datetime(2020, 3, 24, 22, 40, 25, 537000), 'Temp': 71.55, 'Press': 989.02, 'Humid': 26.53}, 
        {'Time': datetime.datetime(2020, 3, 24, 22, 40, 26, 613000), 'Temp': 71.74, 'Press': 989.01, 'Humid': 27.03}, 
        {'Time': datetime.datetime(2020, 3, 24, 22, 40, 27, 704000), 'Temp': 71.58, 'Press': 989.02, 'Humid': 26.85}
        ...]

        #----------------------------------------------------------------------------------------------------------
        # If time_start and time_end are both specified, all data from between time_start and time_end 
        # for the specified Sense HAT is returned
        #----------------------------------------------------------------------------------------------------------
        >>> datahub.get_sense_data(1, '03/24/20 22:40:24.448', '03/24/20 22:40:26.613')
        [{'Time': datetime.datetime(2020, 3, 24, 22, 40, 24, 448000), 'Temp': 71.74, 'Press': 989.02, 'Humid': 26.69}, 
        {'Time': datetime.datetime(2020, 3, 24, 22, 40, 25, 537000), 'Temp': 71.55, 'Press': 989.02, 'Humid': 26.53}, 
        {'Time': datetime.datetime(2020, 3, 24, 22, 40, 26, 613000), 'Temp': 71.74, 'Press': 989.01, 'Humid': 27.03}]
"""

# AVAILABLE IMPORTS
import time
import datahub


# THIS LINE IS NECESSARY TO ENSURE THAT THE ALGORITHM STOPS WHEN TURNED OFF MANUALLY
while datahub.get_algorithm_status(__file__):

    # TESTING LIGHT INTENSITY FROM VIDEO FEED
    intensity = datahub.get_pix_intensity(datahub.get_video_data("68.62.53.255"))
    datahub.update_eventlog(__file__, "Intensity Alert", str(intensity))

    # TESTING SENSE DATA
    # if datahub.get_sense_data("35.9.42.110")[0]['Temp'] > 70.00:
    #     datahub.update_eventlog(__file__, 'Temperature Alert', 'The temperature on Sense 1 has exceeded 70.00 F')
 
    # THIS LINE IS NECESSARY TO ENSURE INFINITE LOOPS DO NOT OCCUR
    time.sleep(1)

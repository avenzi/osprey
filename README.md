# Data Hub

### Project Components Overview
This repository contains the computational infrastructure to allow for data from sensors to be streamed to a server. The sensor data 
and metadata are stored on the server and can be viewed and analyzed using a web application.

Data Hub (Flask web application) Overview:
The Data Hub is the web application in the app directory at the root of the repository that can be used to view a near 
real-time livestream of sensor data as well as play back the sensor streams. Using the Data Hub's algorithms feature, 
a user can upload algorithms to analyze the livestream data as it becomes available.

Data Ingestion Overview:
The Data Ingestion Layer is the application in the data-ingestion directory at the root of the repository that serves
as the server endpoint for receiving the sensor streams. Here, sensor stream data is written to the disk and metadata
is stored in the database.

Data Collection Overview:
The Data Collection component of the system is located in the data-collection directory at the root of the repository and
is the software that runs on a machine which has an interface with a sensor from which data needs to be collected. It also handles
streaming to the Data Ingestion Layer. Currently the Data Collection software is supported on the Raspberry Pi computer.


### Configuration
At the root of the repository is the config.json file, which serves as a global configuration file that can be used by 
any software in the repository. In this file the SERVER_IP_ADDRESS constant should be set to the IP address of the server
where the Data Hub and Data Ingestion layer are installed. The Data Ingestion MySQL connection parameters are also configured
in this file. To configure the Data Hub MySQL connection parameters, the connection parameters in config.py at the root of the 
repository can configured, or environment variables can be used (see Set-up instructions document for more detail).

### Running the software

Running the data hub application (Flask web application):

1. Ensure you are in the root of the repository and then enter the Python virtual environment:
```python
source venv/bin/activate
```

2. Run the website with the provided Bash script:
```python
sh run.sh
```

Running the data collection layer (sensor software):

	1. Ensure you are in the data-collection folder of the repository on the Raspberry Pi with the correct sensors attached and then run the software with:
```python
python3 main.py
```

Running the data ingestion layer:

1. Ensure you are in the root of the repository and then enter the Python virtual environment:
```python
source venv/bin/activate
```

2. Navigate to the data ingestion folder:
```python
cd data-ingestion
```

3. Run the application:
```python
python3 main.py
```

# Extending the Software
The back-end Data Hub logic uses the Model-View-Controller (MVC) web design pattern for organization. To handle additional user actions,
the appropriate controller class should be used or created based on the primary area of concern of the user action. The controller classes
should inherit from the base Controller class, where functionality common to all controllers can be defined.

The Data Hub uses a combination of View classes with the templatting engine Jinja to render the markup pages to be served to the browser.
View classes contain the logic to fetch and organize data which is either returned as a JSON response directly or fed into a Jinja page
and then served. Supporting additional pages on the website should be done by extending the existing View classes and creating new ones,
all of which inherit from the base View class. Additional Jinja pages should be added to the templates directory in the Data Hub's directory.

The Data Collection component of the system supports plug-and-play collection of sensor hardware as long as the sensor interface 
is written and a streaming method is defined. Each sensor interface, or component of a sensor interface, should be defined in 
its own class and inherit from Python's Thread class (threading module) so that collection and streaming of each type of sensor data can 
happen independently without interference. The main.py file in the data-collection directory can then be used to define which sensor 
interfaces should be activated on whichever system the software is installed on. The current version of the main.py assumes usage on a Raspberry 
Pi computer and uses sensor interfaces for a Samsung Go Mic, Sense HAT, and PiCamera.

The Data Ingestion layer follows a similar design to the Data Collection component and uses multi-threading HTTP servers to handle ingestion as 
well as runnable instances through the Thread class. Essentially, either an HTTP request handling class or a Thread-inheriting object can be passed
to the Thread class, which will run the logic in parallel with any other Threads defined in the data-ingestion directory's main.py file.
HTTP request handling classes are easy construct by inherting from the Listener class that is provided.

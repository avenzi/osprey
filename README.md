##### Setup

On the data server, run           $bash scripts/server/setup.sh
On any raspberry pi, run         $bash scripts/raspi/setup.sh
Follow the instructions given.

All configuration options can be modified in config/server_config.json and config/raspi_config.json

##### Running the application

On the pi, no further interaction is necessary. The application will automatically start on boot.

For the server, make sure that the port you wish to use is open on the network the server is connected to.

Start the server by running  $bash scripts/server/run.sh

Use a browser to navigate to the IP of the server with the port number you assigned (e.g. 123.456.78.9:12345). 



### Creating and modifying streamer classes

Examples can be found in app/lib/raspi/streamers.py and app/lib/server/handlers.py

##### Handling Requests

Within a Streamer or Handler class, create a function with the name of the method you want to handle, with a single argument. A Request object will be passed in through which you can access the following:

> Request.origin      # socket that sent this request (passed in as the second argument to self.send())
> Request.path        # request path
> Request.header    # dictionary of request headers
> Request.version   # HTTP version string
> Request.content   # encoded payload
>
> \# if the request is a response:
> Request.code 	    # response code
> Request.message  # response message

This function will be called when the Node received a request using that method name. For example, defining the method self.GET() will be called whenever a GET request is received. 

If this function is to be run continually (i.e. streaming something using a continuous loop), add a conditional to check "not self.exit" as a cue to stop the loop cleanly. Otherwise the thread will be killed abruptly when the process terminates.

##### Sending Requests

Within a Handler or Streamer class, requests can be sent back and forth between one another. Data is sent according to Standard HTTP 1.1 format using a Request object:

> request = Request()       # new request
> request.add_request("METHOD_NAME")   # optional path and version arguments
> request.add_header("keyword1", value1)
> request.add_header("keyword2", value2)
> ...
> request.add_content(content)   # If it's a string, it will be converted to bytes
> self.send(request, origin_socket)   # where self is a Handler or Streamer class

This will send a byte-encoded and properly formatted request to the origin_socket specified.


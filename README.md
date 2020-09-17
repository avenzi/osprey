##### Setup
Navigate to main/installations/
On the data-hub server, run   $bash server_install
On any raspberry pi, run         $bash pi_install

##### Running the application

Make sure that the port you wish to use for the server is open on the network the server is connected to.

First, start the server by running  $bash run_server
If the configuration is not set up yet, you will be prompted for config information. This will only happen the first time, and any config data can be changed in lib/config.json. 

Once you see "Listening for connections....", start a raspberry pi with   $bash run_pi
Again, you will be prompted for config info, and it can be changed in the same location on the Pi.

If everything is working properly, use a browser to navigate to the IP of the server with the port number you assigned (e.g.    123.456.7.8:12345). 


##### Sending Requests

Data is sent according to Standard HTTP 1.1 format using a Request object:

> request = Request()       # new request
> request.add_request("METHOD_NAME")  # optional path and version arguments
> request.add_header("keyword1", value1)
> request.add_header("keyword2", value2)
> ...
> request.add_content(content)  # If it's a string, it will be converted to bytes
> Node.send(request, origin_socket_handler)

This will send a byte-encoded and properly formatted request to the origin_socket specified.

##### Handling Requests

Within the derived Streamer or Handler class, create a function with the name of the method you want to handle, with a single argument. A Request object will be passed in through which you can access the following:

> Request.origin      # socket that send this request (passed in as the second argument to Node.send())
> Request.path        # request path
> Request.header    # dictionary of request headers
> Request.version   # HTTP version string
> Request.content   # encoded payload
>
> \# if the request is a response:
> Request.code 	    # response code
> Request.message  # response message

This function will be called when the Node received a request using that method name. For example, defining the method self.GET() will be called whenever a GET request is received. 

If this function is to be run continually (i.e. streaming something using a continuous loop), add a conditional to check "not self.exit" as a cue to stop the loop cleanly. Otherwise the thread will be killed when the process terminates.


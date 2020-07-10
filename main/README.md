##### Sending Requests

Within the derived Handler class, data is sent according to Standard HTTP 1.1 format using a Request object:

> request = Request()       # new request
> request.add_request("METHOD_NAME")  # optional path and version arguments
> request.add_header("keyword1", value1)
> request.add_header("keyword2", value2)
> ...
> request.add_content(content)  # strings will be converted to bytes if needed
> self.send(request) 

This will add an encoded and properly formatted request to the Connection's outgoing buffer. The push() method is called during the Handler's main loop, which will send everything at once, so there is no need to do it manually. 

##### Handling Requests

Within the derived Connection class, create a function with the name of the method you want to handle, with a single argument. A Request object will be passed in through which you can access the following:

> Request.path        # request path
> Request.header    # dictionary of request headers
> Request.version   # HTTP version string
> Request.content   # encoded payload
>
> \# if the request is a response:
> Request.code 	    # response code
> Request.message  # response message

This function will be called when the connection received a request using that method name. For example, defining the method self.GET() will be called whenever a GET request is sent. 

If this function is to be run continually (i.e. streaming something using a continuous loop), add a conditional to check "self.exit" as a queue to stop the loop cleanly. Otherwise the thread could be killed in an undesirable spot.


##### Sending Requests

Within the derived connection class, data is send according to Standard HTTP 1.1 format:

> self.add_request("METHOD_NAME")  # optional path and version arguments
> self.add_header("keyword1", value1)
> self.add_header("keyword2", value2)
> ...
> self.end_headers()
> self.add_content(content)  # string will be converted to bytes

These functions will add the data to the Connection's outgoing buffer. The push() method is called during it's main loop, which will send everything at once, so there is no need to do it manually. 



##### Handling Requests

Within the derived Connection class, create a function with the name of the method you want to handle, which no arguments. It will be called when the connection received a request using that method name. For example, defining the method self.GET() will handle all GET requests.
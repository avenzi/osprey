Materials for the research paper are in /research_paper.

As of right now, code that I am experimenting with is in /testing:

* echo_server  contains code for a simple ping program that sends text data back and forth
* image_data  contains code for a program that captures individual images and sends them to the server.
* live_image_data  contains code for a program in which I am experimenting with a more live experience, based on the image_data program. Didn't go too well.
* live_video_stream_pi_server  contains code for a program that hosts a server on the Raspberry pi, then streams video to either the data-ingestion client or a web browser. Unfortunately I was only able to get this to work on the local network - the remote VM couldn't connect. I suspect this may have to do with the face that the Pi is hosting the server, rather than the VM. 
* live_video_stream  contains code for a program that hosts a server on the VM and streams images from the Raspberry pi. This one is able work with the remote VM, however I was not able to get the web-browser live feed working as a result. The config file allows the user to specify the public IP of the server running ingestion.py and the port with which to connect over. Currently only ports 5000 and 8000 are forwarded on the remote server.


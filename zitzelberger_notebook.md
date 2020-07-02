## Aven Zitzelberger's Lab Notebook

### Project Description:
You will work to develop and run experiments within a Psychophysics Lab. The lab is a sensor embedded room (many cameras, microphones, temperature sensors, etc.) where individual activity is characterized and streamed to a centralized server for research and analysis. For this project specifically, you will build (or aquire) an Electroencephalograph (EEG) headset and extend this repository to live stream EEG data to the sensor data hub. You will then develop machine learning models that use the EEG data stream to predict human activities as measured by the other sensors.

### Contact Information
* Mohammad Ghassemi, ghassem3@msu.edu, 617-599-6010
* Aven Zitzelberger, zitzelbe@msu.edu, 248-404-5522, 919 East Shaw Ln. (East Holmes Hall)


### Specific Tasks:

1. [Due June 1st] Student will review and familiarize himself with the existing Ghassemi lab data-hub codebase. Student will ensure they can launch the data hub, stream data to the database, and visualize data in the front end.
2. [Due July 1st] Stream EEG data from the Open BCI device to the datahub, and visualize data from EEG and other sensors concurrently.
3. [Due August 1st] Collect data on proof of concept visual stimulus task (TBD), and train machine learning model to reverse engineer visual stimulus from the raw EEG data.


Additional tasks will be added at a future date.

### Project Expectations:
By working on this project you are agreeing to abide by the following expectations:

1. You will keep a daily log of your activities in this notebook. Your update should be 1-2 sentences that outlines what has been accomplished that day, and must be commited by the end of the day. 
2. You will provide a weekly email update, every Monday, to Dr. Ghassemi detailing 
    * What was accomplished the previous week,
    * Any issues you faced, 
    * What you plan to accomplish in the coming week.
3. You will keep all code, data and any other project-related items within this repository in neat and professional condition; this includes: 
    * keeping the code commented, 
    * naming scripts in a way that reflects their functionality, 
    * making regular code commits with meaningful commit messages and,
    * organizing the contents of the project into a logical directory structure.

### Daily Updates:

##### July 1st, 2020:

The issue at the end of yesterday turned out to be a memory leak as a result of one of my connections streaming even when the socket was disconnected. There was an issue with some threads not getting the signal to exit, and I fixed it rather quickly once I figured that out. I would like to figure out how to implement parallel process for different connections rather than just threading, but it looks like the AWS server only has access to one thread. I'll bring it up with Ghassemi when that becomes an issue.

##### June 30th, 2020:

I went thought with most of the ideas I had yesterday - I split the Handler class into a Server and Client version, and moved the GET handler method into the ServerHandler in lib.py. The website now displays a list of links to all the streams currently connected, and each will redirect to a page displaying that individual stream. Eventually there could be a page that displays all of them at once, but I think I'll have to implement parallelism for that - I don't think threading would be enough. At the moment, each stream is identified by the unique ip and port that the pi connected through, and the way that the server knows which stream was requested is by parsing the path, which contains that address. This is a bit unconventional, so I'd like to change this in the future. Perhaps each link will go to the same page but with a different GET query? Really that seems like the same method except a little nicer to look at, but that may be worth it. Also, I changed the pi startup method a bit - the pi now sends an INIT request to the server, giving it some preliminary info like it's 'name' and framerate and such. The server handles this and responds with the START request, which the Pi then handles by streaming. However, I discovered after hours of debugging that the Pi cannot receive data when the server is hosted on the same network (i.e. on my laptop). It can still stream just fine, of course, I had simply never sent more than one request back to the Pi before. I found this out when I used the same code but hosted on the AWS server, and it worked just as expected. I modified the simple echo server to test and demonstrate this and got the same results, so I don't think it has anything to do with my program. I submitted a ticket to MSU IT asking about it, but haven't gotten a response. Also in the middle of working and running the server, I noticed an unexpected connection from an IP I didn't recognize. I looked it up, and it was apparently a common scraping bot. It didn't do anything, but I created a list of banned IPs and run all incoming connections through that list now. Once I got everything working, I tried running the stream for a long time and eventually it slowed down to the point where it was only a frame every few seconds, then the program ended with the message "Killed." This happened once before a couple weeks ago with once of my previous iterations of the program, but I'm not sure what the problem is. Figuring that out will be my task for tomorrow.

##### June 29th, 2020:

I have isolated the issue from Friday. Each new connection was creating a new Handler object, which is where I was initializing the frame buffer. Each time the frame buffer was re-initialized, it cleared the threading condition variables which stopped the stream because there was nothing to release the condition locks. With this in mind as well as my chat with Dr. Ghassemi this morning, I began to restructure a little. I will need to keep an index of all the connections coming in to the server and allow any other connection to access it. That way any incoming connection could read any of the data streams, which is what a browser connection will need to do. Dr. Ghassemi also mentioned that there should be the possibility of running many many video streams at once, so I also want to separate the videos on the website - maybe display links to each stream on a main page? This also made the GET method function in ingestion.py much longer as I have to handle requests for various links. I am considering moving the GET function to lib.py as the user probably won't have a reason to change it. This also brings into question whether I want to split the Handler class into a Client and Server version, as it is getting quite long and complicated. I have also considered making a separate class for each type of streaming connection, but I think that may be a bit much. I'll settle for making the derived ServerHandler class a bit more general, like having a data_buffer which holds the raw payload bytes, and an image_buffer which holds the mjpg images ready to be sent to a browser via multipart stream. These will both be written to in the method defined in the derived class, as it will no doubt be different for every new sensor data stream we add.

##### June 26th, 2020:

Success! I have now gotten the multipart stream to work (on the AWS as well). However I have discovered that Firefox is one of the few browsers that actually supports this particular content type (x-mixed-replace), so it does not work on Chrome, Safari, or Internet Explorer. I spent some time looking to see if there were alternatives to use, but nothing I found was easily compatible with my current program. Some solutions like using HLS or ffmpeg streaming would need a complete overhaul of my code, from what I could tell. Maybe another time. I have also noticed that the stream is only accessible from one browser connection at a time. Any additional connections stops them both. The causes me concern because I thought my program would be able to handle multiple connections - that was the whole point of this threading rewrite. This indicates that there might be something going on that I did not account for, so I will need to fix that before I start anything else. I'll be looking into it on Monday.

##### June 25th, 2020:

Progress! I believe I have fixed that nasty fragmented-data problem. It had to do with the way that python's socket module implements socket.sendall() versus socket.send(). The former calls the latter repeatedly until it is all sent through. Usually this isn't a problem, but I believe that somehow it was sending repeats when the data was too big. I am now using socket.send() exclusively, manually re-sending, and moving down my outgoing data buffer. It seems to have solved the problem so far. I am immeasurably relieved that something finally worked - I didn't end up emailing Ghassemi, so I'll just mention it at our next meeting. Since I got that figured out earlier in the day, I began working on the browser stream.  I have written a method in the Connection class that implements an HTTP multipart stream, but I haven't yet gotten it to work. There seems to be something I don't quite understand about how a browser sends a request and I will start by looking into what that might be tomorrow.

##### June 24th, 2020:

Today was frustrating. I fixed the bug from yesterday, and was finally able to get the "new" program running. The whole reason I rewrote the program was to try to solve the strange problem I mentioned on the 19th. However, even after a complete overhaul, the *same exact* bug still happened. The problem is this: The stream works fine until any single frame size reaches some size threshold, then the read buffer appears to receive the same message over and over again in fragments. I have now sunk more time into debugging it, and I have zeroes in on that threshold - it is exactly 77,500 bytes. If the total size of the data being sent over the connection is even one byte larger, it happens: The receiving end gets a fragmented data stream that contains the same information repeated 10-20 times, overlapping itself. I have no explanation for this, and I will email Ghassemi about it tomorrow. Right now, the only solution I can think of is to manually split the data into smaller chunks. The problem with that is if that particular number (77,500) is unique to my network, operating system, or machine. I will do further testing to figure this out as well.

##### June 23rd, 2020:

Much more progress today. I restructured my classes (yet again) to a state that I am happy with given that shared buffers problem I had yesterday. I was getting some really strange issues that I suspected were due to race conditions on the threads handling requests, so I created a new Request class that each handler method creates an instance of independently. Once a full request is created, it can be sent to the connection's outgoing buffer, which *should* now be thread-safe.  I also rewrote my logging class again so it can handle the same message being sent many times over, and not print it out on a new line every time. Instead it indicates how many times that message has been called to the right of it (super handy when you have a debugging message in a while loop). However there seems to be a problem with interpreters that don't accept the carriage return characters such as python IDLE... it gets messy. I don't know a way around that, but one idea is just to somehow determine whether the interpreter can handle the carriage return, then not print any messages that otherwise would overwrite a previous one if it can't. That's not super important, so it's not my top priority. Right now, I have a bug that is preventing the client from receiving the START request. That is my next task for tomorrow.

##### June 22nd, 2020:

Today was rather unproductive. First, I realized that I had a serious problem with my class structure: Each Connection object is meant to be created when a new connection is found, then run on a separate thread. However, each of those connections must have access to shared buffers so that, for example, one connection can stream in video and another can stream out that same video. As it was this morning, the Connection object were completely independent. The way I am going about fixing this is to pass in a reference to the parent object into the Connection's constructor. This way, each connection has access to the parent's attributes and can share them. This completely throws off the whole way in which I had designed the program to be modified, though, so I experimented with some other ways of re-writing it., but didn't get very far. Another concern that I just realized is that the EEG data will be streaming a much much higher rate than the image data, and I'm worried that my program won't be able to handle it. I looked into implementing parallel processes rather than just threads, but there are some issues with sharing data between processes that I don't know how to get around. I would like to find a better way of structuring my program first before trying anything like that, though. 

##### June 19th, 2020:

Alright so my basic idea is complete - I figured out how to have the server constantly look for new connections and run them on separate threads once they are established. This should theoretically allow any number of connections to the server. Most of my day, however, was spent trying to debug a strange problem where the server was seemingly grabbing too much data from the stream and causing it to lose its 'place' in the data (it would try to read the request line but found itself in the middle of random image data). I have no idea how this was happening. In fact, it shouldn't be - the server was only reading the amount of data specified in the header. I spent hours on this problem, and never quite found the cause but I do have my suspicions. I believe it may have had something to do with the way I had set up the non-blocking socket on the client side when sending data. Regardless, I decided to rewrite the buffer system to make absolutely sure that all the data is sent in the proper order. I implemented a pull-handle-push system with non-blocking read and write operations. The problem now is that doesn't play nicely with the way I want request handling to work - I will need to find a way to efficiently thread that as well. That will be my next task.

##### June 18th, 2020:

Alright so I had to take a step back today and figure out which methods I am going to use to both stream to a browser and stream from multiple devices. One option is to use non-blocking sockets paired with the python select module for multiplexing. The other option is to use blocking sockets but on different threads. After some experimenting in little testing programs, I have decided on the latter. This is for multiple reasons: I understood the threading method better in my testing, threading has a much broader scope of applications, and I need experience with it. The idea is that the server will run a thread that creates new sockets and accepts connections, then delegates a separate thread to handle the stream on that connection. I have begun to write a class to represent that connection, which will then be inherited by the ServerConnection and ClientConnection classes. I also rewrote some of my logging functions because I'm too stubborn to use the logging module. 

##### June 17th, 2020:

I have rewritten my program in terms of HTTP requests, and it is functioning just as it was before. I also added some more error catching functionality, including the ability to catch interrupts and disconnections and exit smoothly. The problem now is to get the browser video feed working, which is not as simple as I originally thought. There was some interactions with the threading and condition modules that I'm not sure about, so tomorrow I will be looking into how those work to make the live feed possible. I have moved the (previously StreamOutput) FrameBuffer class to lib.py, where both the server and client child classes can access it. Previously, only the client class was using it for the picam to write to, but I think I will need it as a buffer from which to stream to a web browser. 

##### June 16th, 2020:

I began writing a new class structure that somewhat imitates the functionality of python's HTTP sertver modules. I didn't understand them well enough to solve this problem so I'm building them from the ground up, albeit a bit simplified. I haven't finished yet, and I will also have to rewrite the data collection program to incorporate standard HTTP request syntax. I had created my own method of sending and parsing data, but it's not compatible with what I need to create the web application with a live feed. I will create a custom HTTP request method (much like I did in my original design with the Pi as the server host) that requests a connection to the server and streams data to it.

##### June 15th, 2020:

Dr. Ghassemi suggested I try to get a live video feed web app running on my working version of the program. The way I got it to work before was by setting up python's HTTPRequestHandler class and rewriting the method that is called for a GET request from a browser, then feeding the camera frames into the webpage. The problem is that the class I wrote for the new program is not based on that handler class, so it isn't contained within its server_forever() method, which is effectively an infinite loop that calls the appropriate request methods. My program does the same thing - I use an infinite loop that constantly receives the stream. I tried rewriting it with the handler class, but I ended up breaking what I had before, so I started over. I looked into the python threading library, and tried a couple things to see if I could get the web app running at the same time as receiving the stream, but I had a hard time getting them to communicate. I have another thing to try tomorrow - trying to rewrite python's handler class (or a simplified version of it) to incorporate my code. All it needs to do is handle GET requests, so it shouldn't be too bad.

##### June 12th, 2020:

I tried the program with the remote server, and was unable to make a connection. I then went back to the small "echo server" program I write awhile ago to make sure it still worked, and it did.  I also noticed that when running my video streaming program the ingestion client (using my laptop on the same network) was connecting through a different port every time, even through the server was hosted through port 8000 as I specified - I am fairly certain that this may be what was preventing the remote VM from connecting. I suspected that this was because the echo server project used the remote VM to host the server, to which the Pi connected and sent data to. With the video stream, the Pi was used as the host for the server instead. I wrote it this way so that either a web browser or the ingestion client could connect to the Pi from different machines and receive the stream. To test that this might be the problem, I rewrote the echo server program and switched the client/server roles, making the pi host the server to which the VM connected just like the streaming program. This version of the echo server failed, which was good because it meant that I had potentially found the problem. For the remainder of the day I rewrote the video streaming program (in /testing/live_video_stream) such that VM hosted the server, and the pi streamed directly to it. This version worked, to my immense delight. However, I was not able to figure out a way to get the web browser live feed working, which is why I wrote it in the original configuration to begin with.  

My next steps will be to teach myself how to use python's threading module so that I will be able to stream the image data to whatever neural networking program we will be using and run it concurrently (problem #4 I made note of on the 10th). I have never worked with parallel programming before so this will also be new to me.

##### June 11th, 2020: 

I accomplished more than I thought I would today. The Pi can now stream to a web browser and the client at the same time. I spent a lot of time digging through the source code of python's HTTPRequestHandler and figured out how to communicate a custom HTTPS request method ("CLIENTSTREAM") from the client to the pi, which allows it to stream separately to both a web browser and the client (this solved problem #1 I had yesterday). To the client, it first sends a 2-byte mini-header (referred to as the proto-header in the code) that denotes the length of the actual header. The actual header can potentially contain whatever information I want, but for now just sends the length of the image and the number of images sent from the pi thus far (solving problem #2 from yesterday). The TCP class I wrote yesterday is designed to parse this header style. Also, I discovered that the client is not lagging behind like I thought - the lag that I observed yesterday was from saving the images to the local machine, which is a time consuming process. When the images aren't saved, there is no problem. This solves problem #3. As of yet, I have not figured out problem #4, although it's not really urgent as of yet. Tomorrow I plan to try this code on the remote server, and update Dr. Ghassemi of my progress.

##### June 10th, 2020:

I have made a lot of progress! I wrote a class on the data-ingestion side that receives and parses the TCP data stream from the pi, including header data with any extra information I want to send along. Problems that I still need to solve:

1) Figure out how to send the image data through the connection without overwriting BaseHTTPRequestHandler.handle(). The problem is that, for some reason, I couldn't receive data sent to the server in order to start the stream. The handle() method starts immediately, but overwriting it means that the do_GET() never gets called, but that's what I use to stream to the browser. Essentially right now it's one or the other, and I want to be able to stream to a browser AND to the data-ingestion server.

2) Figure out how to track and report how many images were sent on the pi-side (I can already track how many were received on the server side). This would allow me to asses how many of the images I'm losing between the two.

3) Need to figure out if the server is able to keep up with the pi. I suspect that there may be a back-log of image data that isn't being processed, which would result in an increasingly out-of-date image feed. If that is the case, I would need to be able to detect that from the server and intentionally skip frames to keep up. That or just reduce the framerate on the pi until they are synchronized, but that is less adaptable to different hardware.

4) Need to figure out how to send the received image stream to a program that can process it (like the neural network). Will I need to use Threading in order to do these simultaneously? I don't have enough experience with this kind of thing to know.

##### June 9th, 2020:    

I have finished my draft of the annotated bibliography with 12 sources. I have also made some progress with the video streaming - I learned a lot today, actually. I have been experimenting with TCP streaming and parsing data sent back and forth between a server and client. I was able to modify the code from the picam documentation to additionally provide a handler for direct socket connection requests, and send individual frames through the connection. I am currently struggling with syncronizing the connections so that I know exactly what it is that the server is receiving, along with being able to send additional information along with the frames. Online research has suggested that sending a header along with the main payload is the preferred method, but I can't seem to find what the conventional method is - I will update Dr. Ghassemi and ask about it.

##### June 8th, 2020: 

I began looking for sources for the annotated bibliography, and found a number that I thought were relevant. I have read through 15 papers today, and wrote annotations for 6 of them as of yet. I will finish the rest tomorrow and notify Dr. Ghassemi - this will be my first official research paper so no doubt he will have some feedback. I did not work on video streaming today - I would like to make sure I have time to finalize the bibliography by Friday (June 12th).

##### June 5th, 2020:   

I tried a new method of setting up live streaming from the Raspberry Pi Camera documentation (data-hub/testing/live_video_stream/client_1.py). This method was successful, and had much less latency than the method used by the baby monitor guide. I was still unable to access the stream remotetly from the virtual machine, however this time I was able to access from a machine on the same network. I tried using port 80 instead, as well as moving one or both ends onto my phone's wifi hotspot to no effect. This would indicate that the error is on the end of the Raspberry Pi (An hypothesis that Dr. Ghassemi also posed after I was unable to establish an FTPS link). Even so, I think this new approach is much cleaner as it required no setup on the end of the machine reading the data. Of course once we want to analyze the data, I will have to figure out how to connect to the signal being sent rather than just viewing it through a browser. I experimented with this by trying different ways in which to parse the stream data. I was able to convert individual images into numpy arrays that could then be fed into a neural network, but I was unable to do it "live." It was only after they had all been transmitted. My next step is to try and do that in "batches." If I were able to make these batches shorter and shorter, I believe it would constitute being "live," however I have no idea whether it would be efficient enough to consider.

##### June 4th, 2020: 

No luck on the FTPS. I tried Filezilla, which claims to support SSL, but all documentation on the matter is extremelt outdated and I simply could not figure out how to do it on the most recent installtion. SSL/TLS is nowhere to be seen in the filezilla client. Dr. Ghassemi opened ports 21 and 990 on his end, but it did not seem to help. Here are some examples of what I tried that actuallt produced a result, but simply failed to connect:

> $lftp -c 'open -e "set ftps:initial-prot ""; set ftp:ssl-force true; set ftp:ssl-protect-data true; put newfile.txt; " -u "USERNAME","PASSWORD" ftps://HOSTNAME:990 '

> $lftp -c 'open -e "set ftps:initial-prot ""; set ftp:ssl-force true; set ftp:ssl-protect-data true; put newfile.txt; " ftps://ubuntu@3.136.140.191:990 '

(those two commands required GnuTLS)

I also followed this guide: http://www.yourownlinux.com/2015/06/how-to-set-up-ftps-ftp-over-ssl-server-on-linux.html

Dr. Ghassemi reminded me of something I wanted to try with the testing programs I wrote last week, so I've started experimenting with getting live video data from the Pi to the server over a TCP connection. I have been having some trouble with the PIL library, and after scouring the documentation I've fixed a few of those issues. I am making slow progress, but progress nonetheless. I also contacted MSGC and the responded saying that they require no action on my part.

##### June 3rd, 2020:  

I was having a number of connection issues, and it turns out that I actually did not succeed in getting local streaming to work. I had assumed that I did, as I was able to connect to the Picam from the Pi's browser. However, I am unable to connect from my laptop on the same network, or even when both are on my phone's hotspot (as suggested by Dr. Ghassemi as a test). I could not ping the Pi's hostname either, although I can still ping its public ip. My attempts to find the cause of the issue thus far have failed. I asked Dr. Ghassemi for advice, and I was instructed to test the following:
1) Whether the Pi can connect to the internet: Yes
2) Whether the Pi can SSH into the remote virtual machine: Yes
3) Whether the Pi can send files to the VM via SFTP: Yes (I was successful in using the linux sftp command)
4) Whether the Pi can send files to the VM via FTPS: Not yet. 

I have tried unsuccessfully to use FTPS using linux's lftp command, however I believe there is a significant possibility that I simply have not done it right. I did not know there was a difference between the two before today. Online guides seem to indicate that this process is much more involved than with SFTP, so I will need to try more methods. In other news, I have received a response from MSGC about my last inquiry, but they haven't mentioned everything being "finalized." If I do not hear from them tomorrow morning, I will contact them again.

##### June 2nd, 2020:

I have continued the setup process, and was able to get streaming to work on the local network. I ran into a few problems but I was able to solve them with some researching. Next step is to set up remote streaming to the server. Even then, I am not sure how I will download the video data for storage/analysis, as I reallt don't know how the image data is processed. I may have to learn a lot more to be able to do that. I have still not heard back from MSGC about my questions.

##### June 1st, 2020: 

Dr. Ghassemi discovered the connection issue that I have been having, and I can now access the data hub web application remotely - Yay! It was because the ports (8000 and 5000) needed to be forwarded from the his end, not just mine. I feel vindicated in my identification of the problem, at least. Even so, the redirection loop I encountered last time was still present, which I suspected might be the case. Ben has not responded to my last three emails, and I am not optimistic. Dr. Ghassemi has encouraged me to try my own method if video streaming using the data-hub (and another similar project he found about building a baby monitor) as a reference. I have begun following the instruction for the baby monitor project, but I am struggling to decipher the bash script that it is having me write. It's not really necessary, but I would like to learn as much as I can in the process. Our project has been accepted by the MSGC for funding - I have filled out the requested paperwork and am waiting to hear back about a few questions I had.

##### May 29th, 2020: 

The Netsurf browser could not be found for install by apt, and once I installed it from source, it refused to be recognized by the command like. Same deal with Qupzilla, and I couldn't install midori at all.. Finally I was able to install Epiphany (Gnome Web) through Snap:
$sudo apt install snapd
$sudo snap install epiphany

Then I was able to run epiphany remotely and view it's graphic environment on my laptop. Success! However when I tried to run the data-hub web application (using sh run.sh, as I have successully done many times), I got the following error: "ImportError: libmysqlclient.so.20: cannot open shared object file: No such file or directory." Sigh. Online solutions all seemed to suggest reinstalling the package. I uninstalled mysql, mysql-server, and mysql-client, then I went back to the team's seup guide. When I ran the $wget command (which worked just fine before), I got the following error: "https://repo.mysql.com/mysql-apt-config_0.8.13-1_all.deb: Scheme missing." This is the exact same command I used during the initial setup. Online solutions suggested using the "-A" flag with $wget" I did this, and was able to install the mysql packages again. This did not solve the original error. I navigated to the directory specified in the error (~/data-hub/venv/lib/python3.6/site-packages/MySQLdb), and it apparently has not been modified since last week when I installed it. I was completelty mystified for couple hours, but all it took was to run $sudo apt-get install libmysqlclient20. How this library was deleted, I do not know. The server now runs properly (as far as I can tell). I opened up epiphany and navigated to 172.26.0.249:5000, and was greeted with the login page. YAY!
I went to the registration page and created an account, username Aven, password "zitzelbe_password." After logging in, it took me to a page that had a button to start a new session, but upon clicking it, I was redirected to the login page. The process repeated. I checked the user table in the database, and my account was indeed entered. I will send another email to Ben.

##### May 28th, 2020: 

Today I wanted to try to access the remote server with a graphical interface so that I could attempt to visit the web application on its local network. This would allow me to continue with the project I was assigned, even though I have not been able to resolve the networking issues. I made numerous attempts to access the server with a remote desktop utility (X2GO) with SSH, but I can't seem to get through. I can get through via CLI just fine, but it seems X2Go just isn't having it. According to everything I know (which isn't much, granted) it should be working, however I get an ambiguous authentication error that no amount of googling has resolved. I spent way too much time trying to debug this, but I had to cut my losses and give up eventually. However, I did manage to get an Xserver client going and was able to verify that I can access some graphical interfaces on the server from my laptop. With this, I will see if I can get a lightweight web browser to access the web application on the server's network. It's not ideal, but it should get the result I want.

##### May 27th, 2020: 

I've been trying to reach the website with UFW running with no success. I first did a trial with UFW on port 80 to make sure it was allowing the port properly, then tried with 8000: With UFW enabled, only default settings, my test program was not able to get through (as expected). After running "sudo ufw allow 80", my test program was able to get through (as expected). Then I set my test program to use port 8000, and it was not able to get through (as expected). After running "sudo ufw allow 8000", my test program was not able to get through (unexpected). It seems that using UFW did not have an effect on the connection issue with port 8000. Also there's something I noticed - Gunicorn says that it's listening at *.5000. Where as everywhere else in the code, port 8000 is specified. I tried allowing port 5000 as well, but that didn't help. I have been consulting with Ben, and he cannot say why this is happeneing. He said he may have to look at the code himself.

##### May 26th, 2020: 

Today I've managed to write a program that is able to sent a stream of images captured from the pi to the remote server. I have moved all of my "experimenting" scripts to the directory "testing" in the root directory. I wasn't able to save the images on the server, but I did confirm that they were being sent. I've been trying to figure out a way to view the images on the server, but I have been having a lot of trouble with X server authentication and couldn't get it to work. I see why a web app is the preferred method. My goal with this was to write my own program to stream video to the capstone's database and use their web app to view it, however I have absolutely no idea how long it would take me to figure that out. I've learned a lot in the last two days, but not quite enough to do it from scratch I'm afraid. Ben has been replying to my emails and given me some useful information, however. He said that the team used UFW to manage the ports they needed to go through. My goal for tomorrow will be to follow the steps he layed out and see where it takes me - looks promising so far.

##### May 25th, 2020:

I was able to confirm that the data from the collection layer is not being sent to the ingestion layer. After fiddling around with the python socket library for awhile, I was able to write a program that can communicate between the raspberry pi and the remote server. They are in the root directory: testing_server.py and testing_client.py (EDIT June 4th - moved to /testing/basic: client.py, server.py). I noticed, however, that I was not able to use ports other than the default ports, so I used TCP port 80 for my script. I suspect that one of the reasons the data-hub is unable to connect is because they may be using a port that is unavailable. I made an attempt to change the port they were using (8000 for video, it looks like), however it did not help. There might be a particular reason for using port 8000, in which case I will need to contact the IT department and ask if they would forward that port on the MSU network - they would undoubtedly require confirmation from Dr. Ghassemi. I have sent another email to the team asking about this. One team member has replied, saying only that he is unable to help.

##### May 22nd, 2020:

Still no response from the team. I was able to track down some of the errors to the pyaudio library, and some others seem to be related to the Sense HAT software. I disabled the audio and Sense HAT programs, leaving only video, and was able to get rid of all the errors I was seeing. However I still don't know if that ultimately affects anything as there is no instruction on what should happen after I run the main programs, as I mentioned in my last email to the team. I would like to test one thing at a time - my next step will be to see if the data-collection layer is working properly.

##### May 21st, 2020:

I have successfully completed the steps in the instructions to set up the data-ingestion layer on the Lightsail instance, but it seems to fail to start. I have no idea what it should look like when it does start, actually. I also was able to finally get the ffmpeg configuration to run without errors on the Pi by installing LAME from sourceforge (https://sourceforge.net/projects/lame/files/lame/3.100/). I haven't heard back yet from the team, and I sent them another email. I mentioned that I thought the extra installs I had to perform should be in the instructions, and asked about the data-ingestion layer problems. I don't think I can proceed further without help from the team, but I will continue to look for solutions. And by that I mean I will read documentation and google error messages until the stackoverflow logo is burned into my retinas.

##### May 20th, 2020:

After receiving a solution from one of the previous team members, I continued with the rest of the setup. Very few steps given in the instructions worked as intended, and numerous packages had to be installed in alternative ways. I emailed the previous group to ask whether my process was adequate or if it might cause further problems. I also asked whether a Sense HAT was necessary for the program to work. Dr. Ghassemi created an AWS Lightsail instance on which I will initialize the data-ingenstion layer - I'll begin working on that tomorrow.

##### May 19th, 2020:

I received the go-ahead from Dr. Ayres to submit our project proposal to the MSGC, along with some additional specifications which I am currently working on. I have also received the raspberry pi. I initially had some issues getting it to recognize MSU's network, but I eventually got it to work via ethernet. I also encountered a problem causing the file system to crash after restarting the system, but I believe I have it working after a full-upgrade. I now have another problem installing MySQL due to my Raspbian Buster installation not being supported. I have found no solution and will contact Dr. Ghassemi.

##### May 18th, 2020:

I have not received the raspberry pi yet. I have been going over the code given to me by Dr. Ghassemi.

##### May 16th, 2020:

I received the first amazon package - the keyboard and mouse. The raspberry pi and camera was due to arrive, but appears to have been delayed. 

##### May 15th, 2020: 

I received the email from Dr. Ayres, and submitted the proposal to the D2L Dropbox as instructed.

##### May 14th, 2020:

I continued work on the application. Dr. Ghassemi gave me feedback and revised it, after which I emailed Dr. Ayres for information on how to apply.

##### May 13th, 2020:

Dr. Ghassemi ordered a bundle from OpenBCI which includes the items I listed plus some wet electrode equipment. He also informed me of an opportunity for us to apply for the NASA Michigan Space Grant Consortium. I began work on the application, and found an interesting paper from 2018 about similar research (https://ieeexplore.ieee.org/document/8396819).

##### May 12th, 2020:

Sent an application to join the OpenBCI forums, and emailed OpenBCI asking whether their software is capable of simultaneously steaming over 16 channels of data at once. I received a response to both today. Evidently the answer to my quetion was definitely 'No', but I was accepted into their forum. 
I suggested to Dr. Ghassemi that we still purchase the 16 channel head set, as it would give us the option of both monitoring the brain fully, or various muscle groups with fewer brain channels. 
Received an update from Amazon saying that the keyboard and mouse has been shipped.

##### May 11th, 2020:

Discussed amazon purchases with Dr. Ghassemi, and placed an order for a Raspberry Pi, an accompanying camera, and a cheap keyboard & mouse, totalling $153.60.
Researched necessary parts for the project from OpenBCI, and compiled a preliminary list of possible purchases.
Emailed OpenBCI with questions, and will modify the list before purchase if necessary.

Preliminary OpenBCI Purchase List:
* Ultracortex Mark IV EEG Headset (Unassembled, Large, 16 channels): $700
* Cyton + Daisy Biosensing Board  (16 channels): $950
* Pulse Sensor: $25
* Dry EEG Comb Electrodes (30/pack): $30
* EMG/ECG Foam Solid Gel Electrodes (30/pack) (2x): $13 x2
* EMG/ECG Snap Electrode Cables: (x2) $40 x2
* Total cost: ~$1,811



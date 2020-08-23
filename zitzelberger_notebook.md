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

##### August 22nd / 23rd, 2020:

This weekend I have been trying to teach myself the bash scripting language. Eventually I will need to write an install script that can get everything set up on the Pi or Server. 

##### August 21st, 2020:

The multiprocessing Pipe() worked like a charm. The Pipe() differs from the Queue() in that is has two distinct "ends". Each has a send() and recv() method that connects to the other end. Queues, on the other hand, have a single entry/exit point which was causing the problem from yesterday. I now have it set up such that a KeyboardInterrupt will trigger in all processes, but the main process can still shut down all worker processes if an error occurs. I have also added an option called automatic_shutdown that will automatically shut down a host node when all workers have terminated. At the moment, this option is only activated on the Client. The Server will still remain active, waiting for new connections. 

Now there is another problem I need to solve: Each process is designed to handle specific requests. This is so that separate data streams have a minimal effect on each other. Some streams, like the EEG and Sense data streams, send numerous requests from the browser to the server per second. Because those requests will be handled on a separate process, none of them go through the main server process which means they shouldn't interfere with any other server operations. However, sometimes a request for a server page is sent on the same socket as a data request. This means that the request gets sent to a process that can't handle it. I seem to have no control over whether a request is sent on a new socket or an old one. Ether I figure out how to do that, or I allow the data-stream process to transfer the socket back to the main process to be handled. The problem with that is it allows for constant transfer back and forth, which is serious speed constraint. 

I know I haven't been pushing my work recently, but that's because I've been writing and re-writing it so much it seemed disingenuous to submit all those in-between stages. For the moment I am happy with it's current structure, so I've committed all the changed made since I started working on multiprocessing.

##### August 20th, 2020:

I ran into some odd behavior that took me nearly the whole day to work out. I have the IPC Queue() set up in both processes such that they both listen for messages, much like a socket. When the main Host process received a KeyboardInterrupt, it sends a SHUTDOWN signal to the Worker, which shuts down then responds with a SHUTDOWN message in return. What I didn't realize is that the thread in which the Worker process is called becomes the new main thread for that process, allowing it to receive KeyboardInterrupts. This was unexpected as I assumed that the MainThread of the MainProcess was the only thread that could receive KeyboardInterrupts. Even more confusingly, that new main thread is not named MainThread, but rather the name of the thread that called the new process. To make this clearer for debugging purposes, I have since called the Process.start() method on it's own thread named NewMainThread. Anyway, because that new main thread can receive KeyboardInterrupts, it also triggered my shutdown() method. This made everything work as I expected it too, but only because both of these things sort of covered for each other, and I didn't realize it until I tested some edge cases. 

It appears that a multiprocessing queue doesn't have two distinct "ends", and my worker process was reading it's own messages. I am going to switch over to a multiprocessing Pipe() and see if that will provide the behavior I want.

##### August 19th, 2020:

I rewrote by Base class to include the basic error-thread functionality that I've been using thus far. Essentially, every class that inherits from Base can call self.run_exit_trigger() to run a separate thread that waits for the self.exit flag to be set. Once triggered, if the self.close flag is also set, then self.cleanup() is called. the cleanup method can be overwritten to do anything that the object needs to before shutting down. The reason I have separate self.exit and self.close flags is because sometimes I need to stop all the running functions in the object, but not completely shut it down. So far this is only used in the SocketHandler class, where I need to be able to stop reading/writing to/from the raw socket, but I don't necessarily want to shutdown the raw socket itself. This is the case for the issue I described yesterday, where I need to be able to send the raw socket through a process pipe. Also, you can call self.run_exit_trigger(block=True) to block the current thread instead of starting a new one. this is necessary when the object in question is running on the MainThread (i.e., a Client or Server). It is important to note that KeyboardInterrupts are ignored on any thread except the main thread, so if you want the exit_trigger() to catch it, one must be run on the main thread.

##### August 18th, 2020:

I found the source of a lot of the weird behavior that I've been seeing. Evidently when I transfer a socket to another process, it continues to run on the first process anyway, resulting in unwanted handling of requests on the first process. The solution would ideally be to stop the SocketHandler but not close the socket itself, remove that SockerHandler from the Host's index, pass the socket through the process Pipe, create a new SocketHandler with the socket, then run the new SocketHandler on the worker process. This would effectively "pause" the socket while it's being transferred. At the moment I have no way to stop the SocketHandler without shutting down the socket completely, so I'll have to re-write some of the SocketHandler. Either that or duplicate the socket, and shutdown the original.

##### August 17th, 2020:

Today was mainly just debugging. I ran across an issue where the initial "sign-on" request from the client streamer was being sent before the streamer itself was run on a new process. I know that's not a huge performance issue, but it feels like evidence of a bigger issue. I re-wrote some of that to give the startup procedure more flexibility. 

I also changed how the "source socket" is dealt with - it should not be necessary to run a handler. I want there to be room for a server handler that doesn't have a data stream (which would mean having a source socket). This kind of handler would be useful for something like a diagnostic stream from the server to the browser - something like a live feed of the memory or CPU usage. Ideally, it shouldn't be difficult to implement given this setup.

##### August 14th, 2020:

I decided that the INIT method problem from yesterday is best solved by just having a completely isolated SIGN_ON method that is called, and any other information can be sent afterward in the INIT method. 

I re-wrote the PickledRequest class (now called SocketPackage because I am never satisfied with a name for more than a day) to try and speed things up, but I suspect that this may be a bottleneck in my program. In order to speed things up, I will need to be able to reduce the amount of socket transfers that occur. This would mean dictating what requests (from a browser) are sent on what sockets. New requests pertaining to a specific client should only send requests to that client, and any other requests (such as for html pages) should be started on new sockets. As far as I know, there is not way to control this, but I will ask Dr. Ghassemi if he has any ideas. If I cannot speed up the process of socket transfer, I am unsure how I will be able to parallelize this program. the only parallelization I would have left would be the separation of the data-stream and the neural network training. So basically I really really hope that this will be fast enough. Hopefully I will have all the bugs worked out and I can start testing it.

##### August 13th, 2020:

Still going strong today. I've now completely redone the way that request methods are called by the Connection. I'm having trouble figuring out a way to call both the default INIT method and a user-defined INIT method. Previously I just had a default _INIT method that also triggered when an INIT request was sent, but with this new structure it just feels wrong to hard code that in. I might have to leave it for now and figure out a nicer way later.

I am also really happy with the way that the process-piping system I've built worked out. Each HostConnection and WorkerConnection has Pipe objects that connect to their respective host/workers. This pipe object has a reference to the process running the other end, that Connection's name, and the shared queue object. 

Another issue at the moment is transferring sockets from one process to another. I've created a PickedRequest class that extracts the raw information from a Request so that it can be send through a process queue. It also takes the raw socket object out of the Request.origin and sends that through alone, because my SocketHandler class cannot be pickled due to the threading Locks it contains. At the other end of the queue, the PickledRequest is re-constructed into a Request object, and the socket is given a new SocketHandler. I hope this process won't be too time-costly.

##### August 12th, 2020:

Alright I've re-written my Server and Client classes. Here's the new structure that I'm working with:

The Connection classes hold an index of SocketHandlers, and each run on a separate Thread. Theses threads run on an isolated Process, which uses a multiprocessing Queue to communicate with the main Connection object, which is the main server. 

The problem I am trying to solve right now is to figure out the best method of shutting everything down. Should the SocketHandlers be trusted to shut themselves down, or should they send a signal to the Connection that forces them to? Same situation for the Server and the Connection, except this time it's between processes not threads. Processes can be easily terminated, but threads cannot. My thought right now is that when the server shuts down, it will give each connection a time window in which to close all it's associated socket handlers. Once that window expires, the main Server will terminate the process, ending all socket handling threads. Which reminds me, I've got to figure out a better way to keep a reference to all the processes and signal queues than just a dictionary of tuples.

##### August 11th, 2020:

(I wrote down the wrong date on yesterday's log entry. It should have been the 10th instead of the 8th. Fixed now.)

I had a conversation with Dr. Ghassemi last night about our plans for the coming semester, and I explained my concerns about whether I should switch over to an API given that my code is a rather naïve implementation of stuff that already exists. We discussed the fact that this code needs to be easy to modify for others to add features, so organization is extremely important. I am finding it incredibly difficult to make this as "general purpose" as possible with the limited knowledge that I have, and an API might be the best way to do that.  Ghassemi also mentioned that it is not at all uncommon to write and re-write code many times over, which was reassuring to hear as I have been doing that frequently. 

I took some time today to go back and re-write some stuff that I think I've been holding onto for too long (another thing Ghassemi and I discussed). I took out some of the multiprocessing and got a working version that I am happy with - I am going to start over with the multiprocessing tomorrow.

##### August 10th, 2020:

Sigh... today was rather unproductive. I encountered an issue with the ServerConnection structure so I rewrote it again, but then later realized that I didn't actually need to do that so I just rolled it back.  I'm still trying to get this program to shut down. I've solved some of it, but the problem is that the SocketHandlers need to communicate to their Connection objects whenever they run into a problem so that the Connection can remove them from it's index of sockets. Right now I'm trying to do that by writing a callback function in the Connections that all sockets are required to call if it exists. This allows the Connection to do whatever it needs to in addition to removing it from it's index. This includes shutting down completely if the socket being shut down is the source socket, which means that the Pi disconnected, which means that any request aimed at that connection should not go through. However I still want the rest of the Connections to remain functional even if a single device disconnects. I'll be working on that tomorrow.

##### August 7th, 2020:

I have not yet mastered the multiprocessing module, it seems.  A major issue is that I can't seem to get the program to shut down properly. I cannot find any processed or threads that are still running. I think I will try to get rid of all threads first and get it working, then add them back if I can find the problem.

Lastly, I changed the SocketHandler so that new commands are no longer called on a separate thread. I am realizing now that this might have been the cause of some problems I experienced awhile back. The idea was to make all commands concurrent, but I am realizing now that the contents of the commands are not necessarily thread-safe, which would be up to the user to implement. For now, if something would take long enough to warrant concurrency, I will leave it up to the user to do that. Keep in mind that at this point the "user" is not an "end-user" in the general use of the word, but rather whoever inherits this code before it's turned into a working application. The main reason I have this concept of a user is because I don't yet know what kinds of data might need to be transferred and visually displayed, and I want my program to be flexible enough to incorporate anything I can think of.

##### August 6th, 2020:

I have decided on a way to deal with that inconsistency between the ServerConnection and the ClientConnection I mentioned yesterday. I am going to have the ClientConnection hold a reference to a source SocketHandler, just like the ServerConnection. From a development standpoint it seems kinda useless, but I think it makes a whole lot more sense from a user standpoint.

Anyway, I also realized that there is another issue with this setup. When a request is sent to the server and handled by one of it's Connections, the method that is called doesn't know which socket the request came from. To solve this I had to pass a reference of the requesting SocketHandler into the request object constructor. This is a *bit* hacky as the Request object is also used by users, and I would rather not confuse the issue by having a constructor argument that isn't used. I am thinking of redesigning the Request object structure into a couple different classes - one that is used by users, and one that is used in the code. I'll work on that tomorrow.

A more general problem I ran into is that the ServerConnections don't have a great way of passing along a request back to the ServerHandler if it can't handle the request. In theory, this should never happen as any request that specifies a connection ID should be intended for the ServerConnection, however I want to have a safety net incase (for some unknown reason) a request is received that has an unnecessary connection ID attached to it. Rather than throw an error, I would much rather the ServerConnection just pass the request along to the server, and only then throw an error if it can't be handled.

I would also like to make it possible to reuse as many ServerHandler objects as possible, swapping out the sockets for new ones as they time out (timeouts is another thing I need to implement). This way I would bog down my program with big objects being created and destroyed all the time.

##### August 5th, 2020:

In light of the information I got yesterday, I have been re-organizing my code to accommodate. The new structure is as follows:

The SocketHandler is essentially a wrapper for a socket, which reads and writes to it as all my Handlers have done previously. This class used to be the one derived and amended by users (to add request methods and such), but now the handler instead calls the request methods of it's parent object, defined by the connection parameter. The connection object can be anything which has methods that should be called in response to requests, but is most notable a ServerConnection object.

The ServerConnection class holds multiple SocketHandlers: The source socket handler is for the socket connected by the Raspberry Pi. There is only one source. All other sockets are stored in ServerConnection.clients, which is a list of SocketHandlers, holding sockets that are connected to anything else (presumably a browser or anything else that wants the data from the source socket). This is the class that should be inherited by users looking to create request methods on the server.

The main Server class, which is created in ingestion.py, holds an index of all the ServerConnection objects. The keys are unique IDs for each ServerConnection, which right now is just the IP:PORT of the source socket. 

The Server also has it's own ServerHandler object, which is a derivative of the SocketHandler. It is special in that it's handle_request() method is overwritten. Instead of simply calling the method specified by the request, this handler first checks to see if an ID was specified in the request query string (like so: 123:456:788/some-page?id=IDHERE). If no ID is specified, then the request is handled as usual (most likely a GET request for a server page). If an ID is specified, it looks for a matching ID in the index of connections. If no such ID exists, the handler then attempts to handle the request while ignoring the ID. If the ID is valid, then the socket sending the request is added to the corresponding ServerConnection's client list, and all further requests from that socket are handled by that connection, instead of the server. This is for cases where a streaming page may need to continually send requests to update the stream, as in the case of the plot streams. These requests on that socket will now go directly to the ServerConnection object, rather than through the ServerHandler first. 

Another special case for the ServerHandler is if the incoming request is an INIT request (reserved method name). In this case, a new ServerConnection object is created with that socket as the source socket, as only a user created client would send an INIT request. The ServerHandler looks for the required headers (class, device, and name), then calls the user defined INIT methods if it exists. Once done, subsequent requests on that source socket will be handled by the new ServerConnection. This, again, is so that the high amount of traffic over that socket does not go through the ServerHandler, but rather directly to the ServerConnection instead.

Essentially, the ServerConnections represent a connection to a single Raspberry Pi, and allows browsers to retrieve the data from it. The ServerHandler is what figures out which ServerConnection any given request should be sent to, and also handles general server unrelated to the data streams.

Finally, the ClientConnection object is the equivalent of the ServerConnection, but on the client side. I am still debating how to structure this, though, because it would make sense for a ClientConnection to hold many sockets, but that doesn't make any sense because any given client connection will only have one socket - to the server. It would then be logical to have the ClientConnection inherit directly from the SocketHandler, but I am afraid that the inconsistency between server and client structure may confuse users. One solution to this would be to rewrite the SocketHandler class to be able to handle multiple sockets (like with the Select module), then there would be no need for a ServerConnection class. The ServerHandler could just pass any number of sockets to another SocketHandler. However I would like to get this version fully working before I do something like that, as SocketHandler is the most difficult to debug.

##### August 4th, 2020:

Did more research to answer my questions from yesterday:

1) Yes. 
	On UNIX:  os.sched_setaffinity(pid, mask). 
	On Windows: ctypes.windll.kernel32.SetProcessAffinityMask(pid, cpu_mask)
I'm not sure if the pid on the Windows version is actually the pid or something else. Doesn't matter, though, since this is going to be run on Ubuntu. I have also noticed that not manually setting the cpu affinity results in everything being run on one core. Apparently this is because some modules like numpy mess with cpu affinity. I will have to be sure to watch out for this.

2) I can run more processes than CPU cores available, and it looks like the extra processed are just scheduled as if they were threads, but on the machine level rather than on the Python level. I couldn't find a complete answer, but from what I have read I believe that running threads on each process would be less costly that running extra processes.

3) It looks like it is best practice to avoid sharing data between processes, which means that I should most likely find a way to move the socket itself to another process. On Windows, python's socket module provides a way to serialize sockets to be transmitted to another process. On UNIX, sockets can already be passed to child processed due to the fact that os.fork() exists, which allows processes to share file descriptors. I don't *entirely* know why file descriptors are significant in this context, but I will probably learn that as I work on this.

I also got a bit side-tracked today when I realized that the system I have been using to transfer files to the server is basically the same as what PHPStorm does to access a remote host. I spent some time trying to move my project over to PHPStorm, but it turns out PHPStorm doesn't quite have the same level of Python syntax highlighting. Also, since I have to run my programs through the command line, I eventually decided just to keep using SuperPuTTY as I have been. Maybe in the future once the server is meant to run more continuously, I can move everything over to make things easier.

##### August 3rd, 2020:

I spent the day reading the multiprocessing documentation and fiddling with test programs, trying to get a grasp of how this stuff works. I still don't quite understand how I am supposed to control which cores the processes are run on, but it's possible that python just takes care of that automatically. I did learn, though, learned that it is indeed the multiprocessing module that I should use, rather than the subprocess module - I was unsure about that until this afternoon. The subprocess module is for accessing any other type of program from inside python. I also learned that the best practice for this application will be to try and create processes which will run for the longest period of time, rather than starting and stopping processes. Unlike threading, that would be rather costly. The multiprocessing was built with similar usage cases to the threading module which made it easy to run, but I still don't quite grasp the behind-the-scenes conceptual stuff so I don't think I can fully make use of the efficiency it provides.

Questions that I need to figure out:

1) Can I control which CPU core each process runs on? If so, how?
2) If I run more processes than there are CPU cores, do the extra processes run like thread? Would it be better to use the threading module for extra processes instead?
3) Since sockets aren't serializable using pickle, what is the best way to transmit sockets to another process? Is it to duplicate the socket in the new process, or share the data being transferred instead?

##### July 31st, 2020:

Today I spent my time rewriting some of my program in preparation for parallelism. Moving forward, I think it is prudent at this time to implement multiprocessing rather than threading. I think this will take some time for me to figure out, but now that EnSURE is coming to an end I believe I will have the time.

##### July 30th, 2020:

Today I spent most of my time writing up my project outline and putting my poster presentation together, which I will present at MidSURE next week. I got a really nice demonstration of the EEG stream with eye-blinks.

##### July 29th, 20020:

I was finally able to get a working version of the Sense and EEG stream working. It took awhile to get the AjaxDataSource() properly working in Bokeh, but once I did it worked like a charm. I also wrote a wrapper class for the graph that allows for a Handler class to input a Bokeh layout object, containing any kind of plot layout. All the user has to do is create figures and glyphs just like in Bokeh, then pass it all into the GraphStream() object. After that, it's just a matter of writing new data to the GraphStream.buffer, and my program takes care of the rest. 

The biggest changes I made today were actually to the way that my handler responds to browser GET requests. I hadn't anticipated rapid-fire requests from a browser, so I had to throw some 'patchwork' code into my program to get it running. After I finish this poster presentation, I will certainly be going back and refactoring quite a bit.

And best of all, that nasty segfault is nowhere in sight.

##### July 28th, 2020:

Sadly I was not able to solve the segfault problem with matplotlib. 

However, I have discovered my next obsession: Bokeh. The Bokeh module is made specifically for streaming plots and displaying them using JavaScript. No more converting plots into images! It's taken me the better part of the day to acquaint myself with Bokeh, but so far I am loving it. Sometime tomorrow (hopefully) I should have a working version with the EEG stream. 

My main focus today was digging through the Bokeh module and picking out the right stuff that I need to display and update an image in a browser window. Basically it boils down to:

1) Creating the initial HTML for the page that will display the plot, with a designated div tag that Bokeh recognizes

2) writing the necessary JS to send continual requests to my server, which will respond with updated JSON containing the new data to be plotted each time

Bokeh takes care of the rest. I think I'm in love.

##### July 27th, 2020:

Progress was awful today. I tried to find the source of the segfault, only to realize it probably isn't where I thought it was for most of the day - I am no longer convinced that it occurs in the socket module. I  originally thought it was because of the timing of the send/receive cycle of my program, but that was proving less and less an issue as I tweaked various settings. The only think that  made a significant difference was changing when and how often a pyplot figure was being saved as a jpeg. This is simple speculation due to  correlation, of course, but after some searching it appears that segfaults are not uncommon when messing with matplotlib. This would certainly explain why the video stream does not have this  bug. I believe it has something to do with the fact that pyplot implements it's own threading, and it might be interfering with the threading in my program. 

I am going to try out some more stuff tomorrow. If I can't fix it by Thursday, I will put together the poster  regardless. Worst case scenario is that I scrap it all and switch to a different plotting module, but that may be risky given the poster deadline this weekend. 

##### July 23rd / 24th, 2020:

I had quite a lot of trouble setting up the EEG streaming on the Pi. It took me awhile to figure out (and through some help on the OpenBCI forums), that I had to compile the python BrainFlow module from source in order to be able to run it on the Pi's 32 bit system. Once I got over that hurdle, I was able to set up the stream from the EEG device to the Pi, and then incorporate that into my streaming program. I was able to stream the EEG data to the remote server with relative ease (thanks to me preparation with the Sense Hat data), however I encountered a bug that I mentioned on  the 16th: When the plot image is too large, the browser seems to cut off the bottom of it. I cannot for the life of me figure out what is causing this. The plt.savefig method seems to be working fine - the full plot can be saved to an image file on the server. I really need to fix this because I can't ignore it by reducing the image size like I did with the Sense data stream. There is simply too much data, and I need to see the full image. 

##### July 22nd, 2020:

Today I put together the OpenBCI EEG kit and did some tests with the bluetooth stream on my laptop. I had trouble getting the headset to fit correctly - I have quite a lot of hair so I had to mess with the headset a bit to get it to fit. I got it mostly working on my laptop, but have yet to set it up on one of the Pis.

##### July 21st, 2020:

Most importantly, I finally got the "chunked" data method working for the Sense Stream. However, I ran into a segfault about halfway through the day and didn't get much done beyond that. I believe it's coming from the socket module, which is a C extension. It seems to happen when the rate at which Sense data requests are sent to the server get above some threshold. I have no idea why this would be the case because I have the 24 FPS video stream running at the same time. Regardless, the server can't handle generating plot images at a very high rate, so I've sort of avoided both issues with the chunking method. In the StreamHandler Client class, the self.frames attribute controls how many data points are to be sent per request. There is also a time.sleep(0.001) inside the data collection loop to slow it down, but I would really prefer a way to get around the segfault without that. Tomorrow I am going to start putting the EEG kit together.

##### July 20th, 2020:

Today I was able to restructure my Server Handler classes so that each new connection can specify which custom handler should be used for it. I have been thinking about doing this for awhile, and I am glad I finally did it. This allows the user to create a completely separate class in ingestion_lib.py to match the class in collection_lib.py. The INIT request method can now be fully overwritten to include any initial data from the pi. Also, the special HTML() function can now be defined, which returns the HTML for the display page. This is so that each stream type can have a different custom page layout.

This restructure took some doing, but I was able to get it to work by first handling the INIT request on a basic InitServerHandler class which grabs the new Handler class name from the INIT requests and passes the request over to that class. This InitServerHandler class also has a GET method to handle browser requests. 

Tomorrow I will work on figuring out how to chunk the data sent from the pi so that I can increase the amount of data sent without increase the number of images generated, which is very costly.

##### July 17th, 2020:

No luck on the bug from yesterday. I can't figure out where the image is being truncated - it could be anywhere from pyplot.savefig() to being loaded into the browser. I also rewrote my custom graph and matplotlib Axis wrapper class to accommodate different plot layouts, which I hope will be sufficient when we add EEG data. I also tried to make the framerate a little more flexible, but I'm worried that the speed at which EEG data will be streamed is just too high; I may have to send data in chunks. Unless I can find a quicker way to render a plot into a jpeg image, the browser stream is not going to be very fast at all. I suppose that doesn't really matter in the long run since it's just there for observation purposes. With that in mind, I have been trying to find a way for the program to automatically adjust for slow connections. Possibly a flexible framerate? The problem with that is it would require ignoring some number of requests and keeping track of which ones. This is yet another case where the multipart stream seems like a better idea, but I still want to keep my options open.

##### July 16th, 2020:

I got a preliminary version of the SenseHat streaming to work. It's not pretty, but it works well enough. I'll try to polish it up tomorrow. I'd like to write a more general version of this in preparation for the EEG streaming, so I'll work on that if I have time as well.  There is also a minor mystery with pyplot's savefig() function. For some reason when the image being save exceeds 2^16 bytes, the image being sent to the browser gets cut off. I have no explanation as of yet.

##### July 15th, 2020:

Unfortunately that tangle of threading issues I mentioned yesterday has turned into a rather knotted mess. It seems that I had been relying on some rather circumstantial structuring when I had only one type of client handler class to worry about. Since adding the SenseHat handler class, I have been struggling to keep my threads in order and to make sure each handler exits properly. Before, the main thread simply ran the handler's run() method, then waited until an exit condition (keyboard interrupt or disconnection) was caught, then properly closed the socket and terminated nicely. Now, however, I cannot use the main thread to run both connection as they must run concurrently, so I have had to restructure everything such that the Client class can be handed multiple handler classes and create a connection on each. Now the main thread will run both handlers on new threads, then wait for an exit condition to be called. The main problem I am trying to solve right now is how to notify the main thread of said exit condition since it is no longer in the scope of the handlers themselves. My solutions so far have not worked.

I also spent some time putting together a small bit of user interfacing. My idea is that the first time collection.py is run, you will be prompted for the server ip, port, client name, and which Handler classes this particular client will be running. This information will be stored in the config.json file and used on subsequent calls. It took a bit of digging around in python documentation to find out how to pick out the names of particular classes in another file, but I'm happy with how it turned out. My goal was to keep any and all user editing confined to collection_lib.py and ingestion_lib.py. I didn't want for users to have to go into collection.py to add their new class to anything, so it automatically detects new classes added to collection_lib.py. I am considering doing something similar to this and the threading changes I mentioned previously to the ingestion side of things. This would yield the benefit of being able to split of server handlers into separate classes as well, and allow each connection to specify what data it will be transmitting. 

##### July 14th, 2020:

Today I spent most of my time fiddling around with matplotlib and working out how to implement the Handling option #2 that I detailed from yesterday. I wrote a class that implements a graph that can be added to without needing to store old data anywhere else. I haven't yet implemented discarding data that won't be shown, but I'll worry about that after I get it working inside my program. At the moment I'm trying to untangle some threading issues that I've run into - mainly error catching within the graphing class.

#####  July 13th, 2020:

Brainstorming day. Dr. Ghassemi instructed me to begin working on streaming audio and SenseHat data. I first looked into audio, but found that I might need additional hardware - a microphone or something similar. I also have no idea how I would get audio to play in the browser without a few more modules (to handle sycing with the video). Eventually I decided to put the question of audio aside for now. I then started to experiment with the SenseHat module to get a feel for how I might integrate it into my program. In principle it should be easy to make a complete sensor reading at some given frequency and send them in the a data stream, but I need to come up with a game plan before I start working on it. I did some research and have a few implementation ideas:

###### Initiating the stream:

The following options are mostly different in how to set an example for a new user of this program. I want adding a new data stream to be intuitive and only require code in a single file on the server and client.

1) write each Pi to automatically check for an installed SenseHat, and start streaming SenseHat information in separate requests along with the video stream on the same socket, with the method to handle SenseHat data in the main Handler class in collection_lib.py

2) Implement a separate SenseHat streaming method, and leave it up to the user whether to call it on the START signal from the server. 

3) Create a separate Handler class in collection_lib.py that handles only SenseHat data, and run that class in collection.py after the Video Handler. This would also mean that the SenseHat stream would be a completely separate socket connection from the video stream, so it might then be advisable for the server to be able to detect that it's coming from the same device so it could be displayed on the same page as the video  (wouldn't be hard - just have to look at the connecting IP address). I am leaning toward this option, as it would benefit the most from parallelism on both server and client so it might be the first one I try. I think it would also result in the most organized code.

###### Handling the data on the server:

These are separate options regardless of the options above. The main problem for either option is that converting a python plot to a jpeg image for each frame could be costly. It certainly won't be streaming at 10 FPS, much less 24.

1) Store each new data 'frame' to a buffer that keeps some specific length of history, enough to be plotted into and converted into a jpeg image to be streamed to a browser. The problem with this option is that I need to figure out where to store the data that needs to be re-displayed in the browser as time progresses, and the process storing and shifting this data around could be costly. I am debating whether to make the user handle this in collection_lib.py or write a default procedure in lib.py for any kind of pure data stream.

2) Possibly find some method to update and existing plot with new data, not needing to keep any old data. The problem with this method is that I'm not sure there's a nice way to do it using matplotlib. It would, however, eliminate the need to re-plot all the old data each time, which is much more desirable of course.

I began experimenting with ways to implement initiating option #3 with handling option #1, but I'm not liking it so far. I will be doing further research into handling option #2 tomorrow.

##### July 10th, 2020:

I did it. I solved python.

I got the server's CPU usage with one Pi down to 3%, and it scales exactly as expected up to 15% with 5 Pis. It turns out that I was correct in my assessment of by buffer system, and that using the sockets as file objects eliminated the remaining inefficiencies that I had. I am only disappointed that it took me so long to figure it out. Additionally, it seems even though CPU usage is very low now, the lag problem is completely independent; my guess is that 5 pis (and thus 10 streams) at 24 FPS and a resolution of 640x480 is too much to handle on one core. To test this I tried reducing the resolution and framerate, and sure enough all 5 were able to stream with no lag when both were reduced enough. I believe this problem may only be able to be solved using multiprocessing. Again, using a multipart stream instead of separate requests does not seem to make an impact on lag and only a small impact on CPU usage (~2-3%). However I am not ready to completely switch over just yet, as I am not sold on the benefits outweighing the cost, which is that during a multipart stream, nothing else can be sent from the Pi to the server. Maybe it can be that way, but there's a possibility that down the line I might want a Pi to sent variable requests to the server. Who knows.



##### July 9th, 2020:

I've come to the conclusion that my bytes buffers are the cause of all the CPU usage, or at the very least the cause of the lag that I'm seeing. I did a bunch of research on efficient methods of dealing with byte streams, and it looks like the method I was using is just about the least efficient possible. 

I've tried using an io.BytesIO() object, but the trouble there is that there's no clean way to discard data once it's been read. My solution was to inherit the class and implement a maximum size which, when exceeded, triggers a re-allocation - the current remaining bytes get moved to the front and overwrite the old data. I didn't see a big difference, so I scrapped that and moved on.

I also found that the socket object allows you to make a read and writable file object from it, which (I assume) means I wouldn't need an external buffer. The only problem is that reading individual lines becomes a little tricky because it doesn't have a peek() method. I started to figure out a workaround tonight, and I'll continue that tomorrow morning.

##### July 8th, 2020:

I implemented the threading condition on reading from the stream as well as reading from the buffer, and it made a big difference. I am pretty confident that this was the main issue because all of the strange behavior that I could not explain before is gone, for example that changing the framerate or resolution of the images did not affect performance. Now framerate and resolution are the main factors affecting performance, as they should be. I also noticed that increasing the maximum size that the server is allowed to read from the stream at once decreased usage by ~10%, which makes perfect sense. Fewer reads, less time running. To be clear, the CPU usage is still not ideal - a single stream to the server puts it at 80% usage, but this is significantly better than the maxed-out 200% that it was before. Additionally, the Pi that is streaming the data runs at ~10% usage as opposed to ~90% before. There is clearly still room for improvement, but whatever it is, it will be in making the data ingestion process on the server more efficient (for which I already have a few ideas), rather than the program's overall running efficiency. I am going to mess around with it a little more before moving on - hopefully the next step is to start building the EEG kit!

I also rewrote the error-detection system I had in place using threading conditions, which I think is much cleaner than before. 

##### July 7th, 2020:

I finished implementing the multipart stream from the client. CPU usage didn't change as much as I had hoped, but it was noticeable. I still saw the same behavior of additional Pis connecting only changing the CPU usage by a small amount. I then went ahead and switched over to blocking sockets and rewrote the pull/push loop to be on separate threads. I did not notice any change in CPU usage. I believe the problem may actually be with my pull/push loop itself - I may need to manually slow it down while it's not handling any requests. I will be doing this with a threading condition object on the in_buffer, and any process that needs to read from it must wait until there is content. This will require that each pull from the socket notify all waiting conditions.

I also downloaded SuperPuTTY for my laptop, and am extremely happy with it. It allows me to start up my ssh sessions with all the Pis and the Lightsail instance all at once, and I can easily organize the terminal windows however I want. It's built-in file transfer system using PSCP has a GUI that allows me to easily write code from my laptop, then deploy it to the server for testing. No more code deployment through git :)

##### July 6th, 2020

I have two ideas about what I could do to speed things up:

1) Use blocking sockets instead of non-blocking sockets. It's possible that one of the main inefficiencies is that my program runs in a loop until it receives data from the stream, which could be contributing to CPU usage. However it's also possible that blocking sockets just do that anyway to block - only way to find out would be to test it.

2) Rewrite my program so that the client sends image data in a multipart stream, just like how the server sends images to a browser. Currently, images are sent individually in separate requests, each being run on a separate thread on the server (this is intended behavior because I want the server to handle new requests on new threads). However, I think that starting a new thread for each image is likely very costly, especially since it happens 24 times each second at the current framerate. 

I decided to try working on option 2, since I think it is more likely to be the culprit. It turned out to be much harder than I thought, however, as rewriting my code in this manner completely destroys the nice "user experience" I was going for with my class structure. After much deliberation, I decided to just scrap the nice structure I had and try to get the multipart stream working. If it significantly reduces CPU load, I will then try to work out how to rebuild the class structure nicely. If it doesn't, I can revert to my last commit and try option 1. Hopefully I will finish reworking it by tomorrow and will know by then.

##### July 3rd, 2020

Dr. Ghassemi brought 4 Pis to me today, and I went to work setting them up. I had some of the same setup problems as with the first pi - evidently there was a Raspbian update that went out in November last year that caused upgrades to render the file manager non-functional. I had to do a full-upgrade on each of the Pis. After that I had some trouble ssh-ing into them due to a sneaky newline character at the end of the public key files. Took me longer to find than I'd like to admit. After everything was set up, I started up my program and tried adding a second Pi to the stream - it worked on the first try. However I did notice that the CPU usage on the Lightsail instance only went up by about 3%, even when I added the rest of the Pis. I'm not sure what this means, but it might indicate that something about a different part of my program is just really inefficient... I'll have to look further into it. Also At 3 Pis, there was some lag, and with 4 and 5 the feeds just got further and further behind because they couldn't keep up. I'll do some more testing on Monday to see if I can speed that up.

##### July 2nd, 2020:

Today wasn't all that productive in terms of writing as I spent most of it looking into python's multiprocessing module. It appears to be syntactically similar to the threading module, but with some restriction. For example, you can only share objects between processes that are picklable, which excludes some custom classes. There are options to give them the ability to be pickled, but I'm still figuring that out. There doesn't seem to be many examples of socket servers run on multiple cores, and none that I found were as complex as the one I am trying to write. This may be a difficult journey ahead. In the mean-time, Dr. Ghassemi will bring me more RasPis to work with and test my program with streaming multiple video feeds at once. I am a little worried, though, because I noticed that my program was using 99.3% of the AWS server's single thread. I bought it up with Dr. Ghassemi, and he said he was happy to upgrade - I suggested that we just move up to a server with maybe 2 cores. If we want to go all-out, the most cost-efficient option would be to build out own machine on campus.

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



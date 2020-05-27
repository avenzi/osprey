## Aven Zitzelberger's Lab Notebook

### Project Description:
You will work to develop and run experiments within a Psychophysics Lab. The lab is a sensor embedded room (many cameras, microphones, temperature sensors, etc.) where individual activity is characterized and streamed to a centralized server for research and analysis. For this project specifically, you will build (or aquire) an Electroencephalograph (EEG) headset and extend this repository to live stream EEG data to the sensor data hub. You will then develop machine learning models that use the EEG data stream to predict human activities as measured by the other sensors.

### Contact Information
* Mohammad Ghassemi, ghassem3@msu.edu, 617-599-6010
* Aven Zitzelberger, zitzelbe@msu.edu, 248-404-5522, 919 East Shaw Ln. (East Holmes Hall)

##### Previous Team 
* "Seeger, Ben" <seegerbe@msu.edu>
* "Johnson, Ryan" <john3842@msu.edu>,
* "Devolder, Rainier" <devolde2@msu.edu>,
* "Marderosian, Merryn" <mardero6@msu.edu>,
* "Shu, Lianghao" <shulian1@msu.edu>,
* "Whitacre, Taylor Richard" <whitacr5@msu.edu>,



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
May 27th, 2020:  I've been trying to reach the website with UFW running with no success. I first did a trial with UFW on port 80 to make sure it was allowing the port properly, then tried with 8000: With UFW enabled, only default settings, my test program was not able to get through (as expected). After running "sudo ufw allow 80", my test program was able to get through (as expected). Then I set my test program to use port 8000, and it was not able to get through (as expected). After running "sudo ufw allow 8000", my test program was not able to get through (unexpected). It seems that using UFW did not have an effect on the connection issue with port 8000. Also there's something I noticed - Gunicorn says that it's listening at *.5000. Where as everywhere else in the code, port 8000 is specified. I tried allowing port 5000 as well, but that didn't help. I have been consulting with Ben, and he cannot say why this is happeneing. He said he may have to look at the code himself.

May 26th, 2020:  Today I've managed to write a program that is able to sent a stream of images captured from the pi to the remote server. I have moved all of my "experimenting" scripts to the directory "testing" in the root directory. I wasn't able to save the images on the server, but I did confirm that they were being sent. I've been trying to figure out a way to view the images on the server, but I have been having a lot of trouble with X server authentication and couldn't get it to work. I see why a web app is the preferred method. My goal with this was to write my own program to stream video to the capstone's database and use their web app to view it, however I have absolutely no idea how long it would take me to figure that out. I've learned a lot in the last two days, but not quite enough to do it from scratch I'm afraid. Ben has been replying to my emails and given me some useful information, however. He said that the team used UFW to manage the ports they needed to go through. My goal for tomorrow will be to follow the steps he layed out and see where it takes me - looks promising so far.


May 25th, 2020: I was able to confirm that the data from the collection layer is not being sent to the ingestion layer. After fiddling around with the python socket library for awhile, I was able to write a program that can communicate between the raspberry pi and the remote server. They are in the root directory: testing_server.py and testing_client.py. I noticed, however, that I was not able to use ports other than the default ports, so I used TCP port 80 for my script. I suspect that one of the reasons the data-hub is unable to connect is because they may be using a port that is unavailable. I made an attempt to change the port they were using (8000 for video, it looks like), however it did not help. There might be a particular reason for using port 8000, in which case I will need to contact the IT department and ask if they would forward that port on the MSU network - they would undoubtedly require confirmation from Dr. Ghassemi. I have sent another email to the team asking about this. One team member has replied, saying only that he is unable to help.


May 22nd, 2020: Still no response from the team. I was able to track down some of the errors to the pyaudio library, and some others seem to be related to the Sense HAT software. I disabled the audio and Sense HAT programs, leaving only video, and was able to get rid of all the errors I was seeing. However I still don't know if that ultimately affects anything as there is no instruction on what should happen after I run the main programs, as I mentioned in my last email to the team. I would like to test one thing at a time - my next step will be to see if the data-collection layer is working properly.

May 21st, 2020: I have successfully completed the steps in the instructions to set up the data-ingestion layer on the Lightsail instance, but it seems to fail to start. I have no idea what it should look like when it does start, actually. I also was able to finally get the ffmpeg configuration to run without errors on the Pi by installing LAME from sourceforge (https://sourceforge.net/projects/lame/files/lame/3.100/). I haven't heard back yet from the team, and I sent them another email. I mentioned that I thought the extra installs I had to perform should be in the instructions, and asked about the data-ingestion layer problems. I don't think I can proceed further without help from the team, but I will continue to look for solutions. And by that I mean I will read documentation and google error messages until the stackoverflow logo is burned into my retinas.

May 20th, 2020: After receiving a solution from one of the previous team members, I continued with the rest of the setup. Very few steps given in the instructions worked as intended, and numerous packages had to be installed in alternative ways. I emailed the previous group to ask whether my process was adequate or if it might cause further problems. I also asked whether a Sense HAT was necessary for the program to work. Dr. Ghassemi created an AWS Lightsail instance on which I will initialize the data-ingenstion layer - I'll begin working on that tomorrow.

May 19th, 2020: I received the go-ahead from Dr. Ayres to submit our project proposal to the MSGC, along with some additional specifications which I am currently working on. I have also received the raspberry pi. I initially had some issues getting it to recognize MSU's network, but I eventually got it to work via ethernet. I also encountered a problem causing the file system to crash after restarting the system, but I believe I have it working after a full-upgrade. I now have another problem installing MySQL due to my Raspbian Buster installation not being supported. I have found no solution and will contact Dr. Ghassemi.

May 18th, 2020: I have not received the raspberry pi yet. I have been going over the code given to me by Dr. Ghassemi.

May 16th, 2020: I received the first amazon package - the keyboard and mouse. The raspberry pi and camera was due to arrive, but appears to have been delayed. 

May 15th, 2020: I received the email from Dr. Ayres, and submitted the proposal to the D2L Dropbox as instructed.

May 14th, 2020:
I continued work on the application. Dr. Ghassemi gave me feedback and revised it, after which I emailed Dr. Ayres for information on how to apply.

May 13th, 2020:
Dr. Ghassemi ordered a bundle from OpenBCI which includes the items I listed plus some wet electrode equipment. He also informed me of an opportunity for us to apply for the NASA Michigan Space Grant Consortium. I began work on the application, and found an interesting paper from 2018 about similar research (https://ieeexplore.ieee.org/document/8396819).

May 12th, 2020:
Sent an application to join the OpenBCI forums, and emailed OpenBCI asking whether their software is capable of simultaneously steaming over 16 channels of data at once. I received a response to both today. Evidently the answer to my quetion was definitely 'No', but I was accepted into their forum. 
I suggested to Dr. Ghassemi that we still purchase the 16 channel head set, as it would give us the option of both monitoring the brain fully, or various muscle groups with fewer brain channels. 
Received an update from Amazon saying that the keyboard and mouse has been shipped.

May 11th, 2020:
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



# MSU Capstone: Spring 2020



### Specific Tasks

1. Create a free [AWS Lightsail](https://aws.amazon.com/s/lp/epid1014-b/?trk=ps_a131L000005Of2gQAC&trkCampaign=ACQ_Amazon_Lightsail&sc_channel=ps&sc_campaign=acquisition_US&sc_publisher=google&sc_category=lightsail&sc_country=US&sc_geo=NAMER&sc_outcome=acquisition&sc_medium=ACQ-P|PS-GO|Brand|Desktop|SU|Compute|Lightsail|US|EN|Text|Lightsail&sc_content=lightsail_bmm&s_kwcid=AL!4422!3!301788508043!b!!g!!%2Blightsail&ef_id=EAIaIQobChMI37fkxPj25gIVRtbACh3l_g6BEAAYASAAEgIdkfD_BwE:G:s) instance or configure one of your machines as a web-server to start with.
2. Create a very simple [Flask App](https://pythonspot.com/flask-web-app-with-python/) that allow people to access the web-server. A nice [flask app example](https://github.com/miguelgrinberg/microblog) is here.
3. Capture [audio](https://github.com/miguelgrinberg/socketio-examples/blob/master/audio/audio.py) and video from users that access the page.
4. [Stream the video](https://blog.miguelgrinberg.com/post/flask-video-streaming-revisited) that is captured onto the FlaskApp page. [This repo](https://github.com/miguelgrinberg/flask-video-streaming/tree/v1) has an example about how to do that.
5. Allow multiple cameras video to be streamed at once. Send alone the GPS coordinates as well.
6. Enable other sensors (temperature and humidity) stream to the site as well. [See here for example.](https://blog.miguelgrinberg.com/post/micropython-and-the-internet-of-things-part-i-welcome) Make sure you let me know what I should order.



### Project Description

The laboratory for the study of human dynamics will be based out of Engineering 3155. To the naked eye, the laboratory will look like a newly renovated meeting space but underneath the surface, the room will be equipped with a comprehensive array of sensor technologies that will monitor the behavior of the individuals within it. These sensors are to include, but are not necessarily limited to: (1) cameras, (2) microphones, (3) thermal sensors and (4) position sensors. 

You goal will be to develop the computational infrastructure and software that will allow for data from the sensors to be streamed to a server, stored, and analyzed by researchers.

### Project Expectations

<u>Weekly Meeting:</u> Capstone team will meet every Thursday in Prof. Ghassemi's office, Engineering Building #3147

<u>[Project Notebook](notebook.md):</u> You will be expcted to commit a one paragraph update, in advance of our weekly meeting, describing what the team has been working on for that week. You can find that notebook in this repo.

<u>Thoughtfully Comment Your Code:</u> All code is expected to be thoughtfully commented. Your code must be both readable and usable by others in the laboratory, and the general community.  You goal should be to write software that can be extended with minimal effort.  Below we provide an illustrative example of how to comment your code.

```python
###############################################
# My Function   : <DESCRIPTION OF FUNCTION> 
# Input         : <data type> - <description>
# Outputs       : <data type> - <description>
###############################################
def my_function(input_arg = 'standard_input' ):
	#------------------------------------------
	# Desciption of A Code Block
	#------------------------------------------
	# Description of line
	a = function_1(x = input_arg)
	
	#------------------------------------------
	# Desciption of Another Code Block
	#------------------------------------------
	# Description of Line
	d = function_4(x = c)
	
	return d
```

### Capstone Team

**Devolder, Rainier:      <devolde2@msu.edu>**;
Seger, Ben:                <seegerbe@msu.edu>;
Whitacre, Taylor R.:     <whitacr5@msu.edu>;
Shu, Lianghao:             <shulian1@msu.edu>;
Marderosian, Merryn (KEY):  <mardero6@msu.edu>
Rainier (KEY)

### Other Resources:

* [Audio and Video Streaming Using a Pi](https://kamranicus.com/guides/raspberry-pi-3-baby-monitor)







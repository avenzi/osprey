// # TODO: actual buffering, clearing out the buffer every once in a while
// # TODO: drift detection, scrubbing
class MotionJPGVideoPlayer {
    constructor(session_id, sensor_id) {
        this.session_id = session_id;
        this.sensor_id = sensor_id;
        this.fps = 16;
        this.ms_play_interval = 1000 / this.fps;
        this.current_frame = 1;
        this.immediately_play_next_frame = false;
        this.buffered_images = {};
        this.frame_times = {};
        this.fetching = false;
        this.frame_to_fetch = 1;
        this.paused = false;
        this.playing = false;
        this.last_fetch_time = Date.now() - 100;

        this.img = document.getElementById(`session-video-${this.session_id}-${this.sensor_id}`);
        this.slider = document.getElementById('playback-slider');
        this.play_button = document.getElementById('play-button');
        this.last_frame_number = this.img.getAttribute('last-frame-number');

        this._start_play_interval();
        this._buffer_interval();
    }

    // should only be called once
    _start_play_interval() {
        var that = this;
        window.setInterval(function() {
            if (that.paused === true || that.playing === false) {
                return;
            }

            if (that.current_frame > that.last_frame_number) {
                if (!that.paused) {
                    that.pause();
                }
                return;
            }

            var current_time = Date.now();
            var ms_passed = current_time - that.last_frame_time;
            
            if (ms_passed >= that.ms_play_interval) {
                //console.log("ms_passed: " + ms_passed);

                if (that.buffered_images[that.current_frame] != null) {
                    that.update_slider_position();
                    that.last_frame_time = current_time;
                    that.display_frame(that.current_frame);
                } else {
                    console.log(that.current_frame + " does not exist");
                    that.current_frame = that.current_frame - 1;
                }
                that.current_frame = that.current_frame + 1;
            }
        }, 1);
    }

    _buffer_interval() {
        var that = this;
        window.setInterval(function() {
            var now = Date.now();
            if (!that.fetching || (now - that.last_fetch_time > 1000)) {
                that.last_fetch_time = now;
                that.fetching = true;
                
                that.request_frame(that.frame_to_fetch);
                that.frame_to_fetch = that.frame_to_fetch + 1;
            }
        }, 1);
    }

    display_frame(frame_number) {
        //console.log(this.buffered_images[frame_number]);
        //console.log(this.buffered_images);
        this.img.src = "data:image/jpg;base64," + this.buffered_images[frame_number];
    }

    set_next_frame_to_fetch(frame_number) {
        this.frame_to_fetch = frame_number;
    }

    request_frame(frame_number) {
        // check if we've retrieved the last frame
        if (frame_number > this.last_frame_number) {
            return;
        }

        // check to make sure the frame isn't already stored
        if (this.buffered_images[frame_number] != null) {
            this.fetching = false;
            return;
        }

        var frame_request_url = VIDEO_REQUEST_URL
            .replace("FRAME", frame_number)
            .replace("SESSION", this.session_id)
            .replace("SENSOR", this.sensor_id);

        var that = this;
        fetch(frame_request_url).then(response => {
            that.frame_times[frame_number] = response.headers.get('frame-time')
            return response.arrayBuffer();
        }).then(function(buffer) {
            //console.log(buffer);
            that.receive_frame(buffer, frame_number);
            that.fetching = false;
        });
    }

    receive_frame(buffer, frame_number) {
        function jpg_to_base64( buffer ) {
            var binary = '';
            var bytes = new Uint8Array( buffer );
            var len = bytes.byteLength;
            for (var i = 0; i < len; i++) {
                binary += String.fromCharCode( bytes[ i ] );
            }
            return window.btoa( binary );
        }
        var base64 = jpg_to_base64(buffer);

        this.buffered_images[frame_number] = base64;

        if (this.immediately_play_next_frame && this.hold_frame == frame_number) {
            this.immediately_play_next_frame = false;
            this.display_frame(this.hold_frame);
        }

        // Debug
        //var ms_since_start = Date.now() - this.buffering_start_time;
        //var ratio = this.frames_buffered / (ms_since_start / 1000);
        //console.log("ratio: " + ratio.toString());
    }

    play() {
        this.set_active();
        this.playing = true;
        this.paused = false;
        this.last_frame_time = Date.now() + (1000 / this.fps) + 5;

        //console.log("Entered play");
        //console.log(this.buffered_images);
    }

    pause() {
        this.paused = true;
        this.playing = false;
    }

    set_active() {
        //this.slider.setAttribute('max', this.last_frame_number);
    }

    scrub(ratio) {
        var frame_number = Math.floor(this.last_frame_number * ratio);
        if (frame_number == 0) frame_number = 1;
        if (frame_number > this.last_frame_number) frame_number = this.last_frame_number;

        this.pause();
        this.current_frame = frame_number;
        this.set_next_frame_to_fetch(frame_number);

        if (this.buffered_images[frame_number] != null) {
            this.display_frame(frame_number);
        } else {
            this.immediately_play_next_frame = true;
            this.hold_frame = frame_number;
        }
    }

    update_slider_position() {
        //this.slider.value = this.frame_times[this.current_frame];
    }
}

class AudioPlayer {
    constructor(session_id, sensor_id) {
        this.sensor_id = sensor_id;
        this.session_id = session_id;

        this.mp3_degapper = new MP3Degapper();

        this.audio_element = document.getElementById(`audio-${this.sensor_id}`);
        this.media_source = new MediaSource();
        var that = this;
        this.media_source.addEventListener('sourceopen', function() {
            that.source_buffer = that.media_source.addSourceBuffer('audio/mpeg');

            // gets called when we're done updating the SourceBuffer (after appending a segment)
            that.source_buffer.addEventListener('updateend', function() {
                //console.log("entered updateend callback");
                //current_segment_number = current_segment_number + 1;

                //if (current_segment_number <= 7) {
                //requestSegment(current_segment_number); 
                //}
            });
        });

        this.audio_element.src = URL.createObjectURL(this.media_source);

        // controls
        this.paused = false;
        this.playing = false;

        // playback
        this.current_segment = 1;
        // TODO: actually know what the last segment number is
        this.last_segment_number = 999;

        // buffering
        this.fetching = false;
        this.segment_to_fetch = 1;
        this.last_fetch_time = Date.now() - 100;

        this._buffer_interval();
    }

    _buffer_interval() {
        var that = this;
        window.setInterval(function() {
            var now = Date.now();
            if (that.segment_to_fetch > 27) {
                return;
            }

            if (!that.fetching || (now - that.last_fetch_time > 1000)) {
                that.last_fetch_time = now;
                that.fetching = true;
                
                that.request_segment(null, that.segment_to_fetch);
                that.segment_to_fetch = that.segment_to_fetch + 1;
            }
        }, 10);
    }

    request_segment(time, segment_number) {
        // check if we've retrieved the last frame
        if (segment_number > this.last_segment_number) {
            return;
        }

        if (time === null) {
            time = -1;
        }
        if (segment_number === undefined || segment_number === null) {
            segment_number = -1;
        }

        var segment_request_url = AUDIO_REQUEST_URL
            .replace("TIMESTAMP", time)
            .replace("SEGMENT", segment_number)
            .replace("SESSION", this.session_id)
            .replace("SENSOR", this.sensor_id);

        //console.log("segment request url: " + segment_request_url);

        var that = this;
        fetch(segment_request_url).then(response => {
            //that.frame_times[segment_number] = response.headers.get('frame-time')
            that.last_fetched_segment_number = response.headers.get('segment-number');
            that.last_fetched_segment_time = response.headers.get('segment-time');
            return response.arrayBuffer();
        }).then(function(buffer) {
            //console.log(buffer);
            //console.log(that.last_fetched_segment_number);
            //console.log(that.last_fetched_segment_time);
            //console.log(buffer);
            that.receive_frame(buffer, that.last_fetched_segment_number, that.last_fetched_segment_time);
            that.fetching = false;
        });
    }

    play() {
        this.audio_element.play();
    }

    pause() {
        this.audio_element.pause()
    }

    scrub(time) {
        this.pause();
        var playback_time = Math.floor((time - SESSION_START_TIME) / 1000);
        this.audio_element.currentTime = playback_time; // how many seconds into playback
    }

    receive_frame(buffer, segment_number, segment_time) {
        var index = segment_number - 1;
        //console.log(index);
        // buffer conversion to gapless mp3
        //this.source_buffer.mode = 'sequence';
        // Parsing gapless metadata is unfortunately non trivial and a bit messy, so
        // we'll glaze over it here; see the appendix for details.
        // ParseGaplessData() will return a dictionary with two elements:
        //
        //    audioDuration: Duration in seconds of all non-padding audio.
        //    frontPaddingDuration: Duration in seconds of the front padding.
        //
        var gapless_metadata = this.mp3_degapper.degap_buffer(buffer);

        // Each appended segment must be appended relative to the next.  To avoid any
        // overlaps, we'll use the end timestamp of the last append as the starting
        // point for our next append or zero if we haven't appended anything yet.
        var appendTime = index > 0 ? this.source_buffer.buffered.end(0) : 0;

        // Simply put, an append window allows you to trim off audio (or video) frames
        // which fall outside of a specified time range.  Here, we'll use the end of
        // our last append as the start of our append window and the end of the real
        // audio data for this segment as the end of our append window.
        this.source_buffer.appendWindowStart = appendTime;
        this.source_buffer.appendWindowEnd = appendTime + gapless_metadata.audioDuration;

        // The timestampOffset field essentially tells MediaSource where in the media
        // timeline the data given to appendBuffer() should be placed.  I.e., if the
        // timestampOffset is 1 second, the appended data will start 1 second into
        // playback.
        //
        // MediaSource requires that the media timeline starts from time zero, so we
        // need to ensure that the data left after filtering by the append window
        // starts at time zero.  We'll do this by shifting all of the padding we want
        // to discard before our append time (and thus, before our append window).
        this.source_buffer.timestampOffset =
            appendTime - gapless_metadata.frontPaddingDuration;

        // When appendBuffer() completes, it will fire an updateend event signaling
        // that it's okay to append another segment of media.  Here, we'll chain the
        // append for the next segment to the completion of our current append.
        /*
        if (index == 0) {
            sourceBuffer.addEventListener('updateend', function() {
            if (++index < SEGMENTS) {
                GET('sintel/sintel_' + index + '.mp3',
                    function(data) { onAudioLoaded(data, index); });
            } else {
                // We've loaded all available segments, so tell MediaSource there are no
                // more buffers which will be appended.
                mediaSource.endOfStream();
                URL.revokeObjectURL(audio.src);
            }
            });
        }
        */

        // appendBuffer() will now use the timestamp offset and append window settings
        // to filter and timestamp the data we're appending.
        //
        // Note: While this demo uses very little memory, more complex use cases need
        // to be careful about memory usage or garbage collection may remove ranges of
        // media in unexpected places.
        this.source_buffer.appendBuffer(buffer);


        /*
        this.buffered_images[frame_number] = base64;

        if (this.immediately_play_next_frame && this.hold_frame == frame_number) {
            this.immediately_play_next_frame = false;
            this.display_frame(this.hold_frame);
        }
        */

        // Debug
        //var ms_since_start = Date.now() - this.buffering_start_time;
        //var ratio = this.frames_buffered / (ms_since_start / 1000);
        //console.log("ratio: " + ratio.toString());
    }


    set_active() {
        //this.slider.setAttribute('max', this.last_frame_number);
    }
}

class MP3Degapper {
    SECONDS_PER_SAMPLE = 1 / 44100;

    constructor() {
        
    }

    // Since most MP3 encoders store the gapless metadata in binary, we'll need a
    // method for turning bytes into integers.  Note: This doesn't work for values
    // larger than 2^30 since we'll overflow the signed integer type when shifting.
   read_int(buffer) {
        var result = buffer.charCodeAt(0);
        for (var i = 1; i < buffer.length; ++i) {
            result <<= 8;
            result += buffer.charCodeAt(i);
        }
        return result;
    }

    degap_buffer(arrayBuffer) {
        // Gapless data is generally within the first 512 bytes, so limit parsing.
        var byteStr = new TextDecoder().decode(arrayBuffer.slice(0, 512));

        var frontPadding = 0, endPadding = 0, realSamples = 0;

        var iTunesDataIndex = byteStr.indexOf('iTunSMPB');
        if (iTunesDataIndex != -1) {
            var frontPaddingIndex = iTunesDataIndex + 34;
            frontPadding = parseInt(byteStr.substr(frontPaddingIndex, 8), 16);

            var endPaddingIndex = frontPaddingIndex + 9;
            endPadding = parseInt(byteStr.substr(endPaddingIndex, 8), 16);

            var sampleCountIndex = endPaddingIndex + 9;
            realSamples = parseInt(byteStr.substr(sampleCountIndex, 16), 16);
        }


        var xingDataIndex = byteStr.indexOf('Xing');
        if (xingDataIndex == -1) xingDataIndex = byteStr.indexOf('Info');
        if (xingDataIndex != -1) {
            // parsing the Xing
            var frameCountIndex = xingDataIndex + 8;
            var frameCount = this.read_int(byteStr.substr(frameCountIndex, 4));

            // For Layer3 Version 1 and Layer2 there are 1152 samples per frame.
            var paddedSamples = frameCount * 1152;

            xingDataIndex = byteStr.indexOf('LAME');
            if (xingDataIndex == -1) xingDataIndex = byteStr.indexOf('Lavf');
            if (xingDataIndex != -1) {
            // See http://gabriel.mp3-tech.org/mp3infotag.html#delays for details of
            // how this information is encoded and parsed.
            var gaplessDataIndex = xingDataIndex + 21;
            var gaplessBits = this.read_int(byteStr.substr(gaplessDataIndex, 3));

            // Upper 12 bits are the front padding, lower are the end padding.
            frontPadding = gaplessBits >> 12;
            endPadding = gaplessBits & 0xFFF;
            }

            realSamples = paddedSamples - (frontPadding + endPadding);
        }

        return {
            audioDuration: realSamples * this.SECONDS_PER_SAMPLE,
            frontPaddingDuration: frontPadding * this.SECONDS_PER_SAMPLE
        };
    }


    
}

var video_players = [];
var audio_players = [];
var playing = false;
var play_start_time = 0;
var active_video_player = null;
var active_audio_player = null;
var scrubbed = false;

document.addEventListener("DOMContentLoaded", async function() {
    var slider = document.getElementById('playback-slider');

    if (SESSION_ID != -1) {

        //console.log(SESSION_SENSORS);
        SESSION_SENSORS.forEach(function(session_sensor, index) {
            sensor_id = session_sensor[0];
            ip = session_sensor[1];
            sensor_type = session_sensor[4];

            if (sensor_type == "PiCamera") {
                var video_player = new MotionJPGVideoPlayer(SESSION_ID, sensor_id);

                // TODO: swap on button press
                if (active_video_player == null) {
                    active_video_player = video_player;
                    active_video_player.set_active();
                }
                video_players.push(video_player);

                setTimeout(function(){
                    active_video_player.display_frame(1);
                }, 2500);
            } else if (sensor_type == "Microphone") {
                var audio_player = new AudioPlayer(SESSION_ID, sensor_id);

                active_audio_player = audio_player;
                active_audio_player.set_active();
                audio_players.push(audio_player);
            }
        });
    }

    // play/pause the players
    document.getElementById("play-button").addEventListener("click", function(event) {
        playing = !playing;

        if (playing) { // pressed to play
            for (let active_video_player of video_players) {
                if (active_video_player !== null) {
                    active_video_player.play();
                }
            }

            if (active_audio_player !== null) {
                active_audio_player.play();
            }

            play_start_time = Date.now();
            slider_start_time = slider.value;

            document.getElementById("play-button").classList.remove("paused");
        } else { // pressed to pause
            for (let active_video_player of video_players) {
                if (active_video_player !== null) {
                    active_video_player.pause();
                }
            }

            if (active_audio_player !== null) {
                active_audio_player.pause();
            }

            document.getElementById("play-button").classList.add("paused");
        }
    });

    function msToTime(duration) {
        var milliseconds = parseInt((duration % 1000) / 100),
          seconds = Math.floor((duration / 1000) % 60),
          minutes = Math.floor((duration / (1000 * 60)) % 60),
          hours = Math.floor((duration / (1000 * 60 * 60)) % 24);
      
        hours = (hours < 10) ? "0" + hours : hours;
        minutes = (minutes < 10) ? "0" + minutes : minutes;
        seconds = (seconds < 10) ? "0" + seconds : seconds;
      
        return hours + ":" + minutes + ":" + seconds + "." + milliseconds;
      }

    // update the scrubber based on time passed
    window.setInterval(function() {
        if (this.playing) {
            var delta = Date.now() - play_start_time;
            slider.value = "" + (parseInt(slider_start_time) + delta);
        }

        var slider_value_numeric = parseInt(slider.value);
        var session_start_time = parseInt(SESSION_START_TIME);
        var elapsed_ms = slider_value_numeric - session_start_time;
        var elapsed_time = msToTime(elapsed_ms);

        var archive_date = new Date(slider_value_numeric);

        $("#elapsed-time").html("Elapsed Time: " + elapsed_time);
        $("#archive-time").html("Archive Time: " + archive_date.toLocaleString());
    }, 50);

});

function on_slider_input(time_ms) {
    playing = false;
    if (playing) { // pressed to play
        //console.log("STARTED PLAYING");
    } else { // pressed to pause
        document.getElementById("play-button").classList.add("paused");
    }
    //console.log(val);
    var time = parseInt(time_ms);
    var ratio = (time - SESSION_START_TIME) / (SESSION_END_TIME - SESSION_START_TIME);

    for (let active_video_player of video_players) {
        if (active_video_player !== null) {
            // assumes video recording over exactly entire duration of the session (refactor to use timestamp searching for sync reasons)
            active_video_player.scrub(ratio);
        }
    }

    if (active_audio_player != null) {
        active_audio_player.scrub(time);
    }
}

function sensor_selection_clicked(sensor_id, sensor_type) {
    var box = document.getElementById(`sensor-box-${sensor_id}-${sensor_type}`);
    var checkbox = document.getElementById(`checkbox-${sensor_id}-${sensor_type}`);
    var hidden = $(box).hasClass('hide');

    if (hidden) {
        $(box).removeClass('hide');
        $(checkbox).attr('checked', true);
    } else {
        $(box).addClass('hide');
        $(checkbox).removeAttr('checked');
    }
}



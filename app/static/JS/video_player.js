/**
 * @fileoverview This file implements a MJPG video player and performs
 * fetching, buffering, and playback control.
 */

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
        this.slider = document.getElementById("playback-slider");
        this.play_button = document.getElementById("play-button");
        this.last_frame_number = this.img.getAttribute("last-frame-number");

        this._start_play_interval();
        this._buffer_interval();
    }

    // Decides when to play a new frame
    _start_play_interval() {
        var that = this;
        window.setInterval(function() {
            // Check playback controls variables
            if (that.paused === true || that.playing === false) {
                return;
            }

            // Avoid playing past the last frame
            if (that.current_frame > that.last_frame_number) {
                if (!that.paused) {
                    that.pause();
                }
                return;
            }

            var current_time = Date.now();
            var ms_passed = current_time - that.last_frame_time;
            
            // Determine how often to play a new frame from the FPS
            if (ms_passed >= that.ms_play_interval) {
                if (that.buffered_images[that.current_frame] != null) {
                    that.last_frame_time = current_time;
                    that.display_frame(that.current_frame);
                } else {
                    that.current_frame = that.current_frame - 1;
                }
                that.current_frame = that.current_frame + 1;
            }
        }, 1);
    }

    // Requests video frames from the server
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
        // Replace the conetnts of the image with the new base64 JPG bytes
        this.img.src = "data:image/jpg;base64," + this.buffered_images[frame_number];
    }

    set_next_frame_to_fetch(frame_number) {
        this.frame_to_fetch = frame_number;
    }

    request_frame(frame_number) {
        // Check if the last frame has been retrieved
        if (frame_number > this.last_frame_number) {
            return;
        }

        // Check to make sure the frame is not already stored
        if (this.buffered_images[frame_number] != null) {
            this.fetching = false;
            return;
        }

        var frame_request_url = VIDEO_REQUEST_URL
            .replace("FRAME", frame_number)
            .replace("SESSION", this.session_id)
            .replace("SENSOR", this.sensor_id);

        var that = this;
        // Fetch the frame
        fetch(frame_request_url).then(response => {
            that.frame_times[frame_number] = response.headers.get("frame-time")
            return response.arrayBuffer();
        }).then(function(buffer) {
            that.receive_frame(buffer, frame_number);
            that.fetching = false;
        });
    }

    receive_frame(buffer, frame_number) {
        function jpg_to_base64( buffer ) {
            var binary = "";
            var bytes = new Uint8Array( buffer );
            var len = bytes.byteLength;
            for (var i = 0; i < len; i++) {
                binary += String.fromCharCode( bytes[ i ] );
            }
            return window.btoa( binary );
        }
        // Convert the raw jpg bytes to base64
        var base64 = jpg_to_base64(buffer);

        this.buffered_images[frame_number] = base64;
        if (this.immediately_play_next_frame && this.hold_frame == frame_number) {
            this.immediately_play_next_frame = false;
            this.display_frame(this.hold_frame);
        }
    }

    // Resume playback of the video
    play() {
        this.playing = true;
        this.paused = false;
        this.last_frame_time = Date.now() + (1000 / this.fps) + 5;
    }

    // Pause the playback of the video
    pause() {
        this.paused = true;
        this.playing = false;
    }

    // Navigating to a certain part of the video (scrubbing)
    scrub(progress) {
        var frame_number = Math.floor(this.last_frame_number * progress);
        if (frame_number == 0) frame_number = 1;
        if (frame_number > this.last_frame_number) frame_number = this.last_frame_number;

        // Pause the video when a user scrubs
        this.pause();
        this.current_frame = frame_number;
        this.set_next_frame_to_fetch(frame_number);

        if (this.buffered_images[frame_number] != null) {
            this.display_frame(frame_number);
        } else {
            // Immediately show the next frame after scrubbing
            this.immediately_play_next_frame = true;
            this.hold_frame = frame_number;
        }
    }
}
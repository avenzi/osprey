/**
 * @fileoverview This file implements an MP3 audio player class that plays independent mp3 files
 * gaplessly in sequence.
 */

class AudioPlayer {
    constructor(session_id, sensor_id) {
        this.sensor_id = sensor_id;
        this.session_id = session_id;

        this.mp3_degapper = new MP3Degapper();

        this.audio_element = document.getElementById(`audio-${this.sensor_id}`);
        this.media_source = new MediaSource();
        var that = this;
        this.media_source.addEventListener('sourceopen', function() {
            // Set the MediaSource's source buffer upon being opened
            that.source_buffer = that.media_source.addSourceBuffer('audio/mpeg');
        });
        this.audio_element.src = URL.createObjectURL(this.media_source);

        // Playback control variables
        this.paused = false;
        this.playing = false;
        this.current_segment = 1;
        this.last_segment_number = this.audio_element.getAttribute('last-segment-number');

        // Buffering control variables
        this.fetching = false;
        this.segment_to_fetch = 1;
        this.last_fetch_time = Date.now() - 100;

        this._buffer_interval();
    }

    _buffer_interval() {
        var that = this;
        window.setInterval(function() {
            var now = Date.now();

            if (!that.fetching || (now - that.last_fetch_time > 1000)) {
                that.last_fetch_time = now;
                that.fetching = true;
                
                that.request_segment(null, that.segment_to_fetch);
                that.segment_to_fetch = that.segment_to_fetch + 1;
            }
        }, 10);
    }

    request_segment(time, segment_number) {
        // Check if we've retrieved the last frame
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

        var that = this;

        // Fetch the audio segment
        fetch(segment_request_url).then(response => {
            that.last_fetched_segment_number = response.headers.get('segment-number');
            that.last_fetched_segment_time = response.headers.get('segment-time');
            return response.arrayBuffer();
        }).then(function(buffer) {
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

        // degap_buffer will return a dictionary with two elements:
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
        
        // MediaSource requires that the media timeline starts from time zero, so we
        // need to ensure that the data left after filtering by the append window
        // starts at time zero.  We'll do this by shifting all of the padding we want
        // to discard before our append time (and thus, before our append window).
        this.source_buffer.timestampOffset =
            appendTime - gapless_metadata.frontPaddingDuration;

        // appendBuffer() will now use the timestamp offset and append window settings
        // to filter and timestamp the data we're appending.
        this.source_buffer.appendBuffer(buffer);
    }


}
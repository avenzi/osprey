// # TODO: actual buffering, clearing out the buffer every once in a while
// # TODO: drift detection, scrubbing
class MotionJPGVideoPlayer {
    constructor(session_id, sensor_id) {
        this.session_id = session_id
        this.sensor_id = sensor_id;
        this.fps = 24;
        this.current_frame = 1;
        this.numbers_of_frames_to_buffer = 24;
        this.buffered_images = [];

        this.img = document.getElementById(`session-video-${this.session_id}-${this.sensor_id}`);
    }

    start_buffering() {
        this.request_frame(1);
    }

    request_frame(frame_number) {
        var frame_request_url = VIDEO_REQUEST_URL
            .replace("FRAME", frame_number)
            .replace("SESSION", this.session_id)
            .replace("SENSOR", this.sensor_id);

        var that = this;
        fetch(frame_request_url).then(response => {
            //console.log(response);
            return response.arrayBuffer()
        }).then(function(buffer) {
            function to64( buffer ) {
                var binary = '';
                var bytes = new Uint8Array( buffer );
                var len = bytes.byteLength;
                for (var i = 0; i < len; i++) {
                    binary += String.fromCharCode( bytes[ i ] );
                }
                return window.btoa( binary );
            }
            var base64 = to64(buffer);

            that.buffered_images.push(base64);
            that.request_frame(frame_number + 1);
        });
    }

    play() {
        var that = this;
        window.setInterval(function() {
            if (that.buffered_images[that.current_frame] != null) {
                that.img.src = "data:image/jpg;base64," + that.buffered_images[that.current_frame];
            } else {
                console.log(that.current_frame + " does not exist");
                that.current_frame = that.current_frame - 1;
            }

            that.current_frame = that.current_frame + 1;
        }, 1000 / this.fps);
    }
}

document.addEventListener("DOMContentLoaded", function() {
    if (SESSION_ID != -1) {
        var player = new MotionJPGVideoPlayer(SESSION_ID, 1);
        player.start_buffering();

        window.setTimeout(function(){
            player.play();
        }, 2000);
    }
});


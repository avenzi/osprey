/**
 * @fileoverview This file contains logic to "degap" an MP3 file, which
 * removes the padding from the audio data.
 */

document.addEventListener("DOMContentLoaded", async function() {
    var slider = document.getElementById('playback-slider');

    if (SESSION_ID != -1) {
        // Initialize the sensor data players
        SESSION_SENSORS.forEach(function(session_sensor) {
            sensor_id = session_sensor[0];
            ip = session_sensor[1];
            sensor_type = session_sensor[4];

            if (sensor_type == "PiCamera") {
                var video_player = new MotionJPGVideoPlayer(SESSION_ID, sensor_id);
                if (active_video_player == null) {
                    active_video_player = video_player;
                }
                video_players.push(video_player);
                setTimeout(function(){
                    active_video_player.display_frame(1);
                }, 2500);
            } else if (sensor_type == "Microphone") {
                var audio_player = new AudioPlayer(SESSION_ID, sensor_id);
                active_audio_player = audio_player;
                audio_players.push(audio_player);
            } else if (sensor_type == "SenseHat") {
                var sense_player = new SenseHatPlayer(SESSION_ID, sensor_id);
                sense_players.push(sense_player);
            }
        });
    }

    /* Handles the resumption and pausing of the playback */
    document.getElementById("play-button").addEventListener("click", function(event) {
        playing = !playing;

        if (playing) {
            // Resume the active media players when playback is continued
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
        } else {
            // Pause the active media players when playback is paused
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

    /* Formats a duration of time for display */
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

    /* Updates the scrubber based on time passed */
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

    /* Updates the eventlog based on the current time of the playback */
    function update_eventlog() {
        $.get(`/retrieve_eventlog/${parseInt(slider.value)}/4/${SESSION_START_TIME}`, function(data) {
            $("#eventLog").html(data);
        }).always(function() {
            setTimeout(doPoll, 850);
        });
    }
    update_eventlog();
});

/* Handles when the user scrubs to a certain point in the playback */
function on_slider_input(time_ms) {
    playing = false;
    if (!playing) {
        document.getElementById("play-button").classList.add("paused");
    }
    
    var time = parseInt(time_ms);
    var ratio = (time - SESSION_START_TIME) / (SESSION_END_TIME - SESSION_START_TIME);

    for (let active_video_player of video_players) {
        if (active_video_player !== null) {
            active_video_player.scrub(ratio);
        }
    }

    if (active_audio_player != null) {
        active_audio_player.scrub(time);
    }
}

/* Handles when the user selects a sensor to display or hide */
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

var video_players = [];
var audio_players = [];
var sense_players = [];
var playing = false;
var play_start_time = 0;
var active_video_player = null;
var active_audio_player = null;
var scrubbed = false;



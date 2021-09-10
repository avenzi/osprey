function log(msg) {
    // logs a message to console and to the log div
    console.log(msg)
    $('.logs p').prepend(`> ${msg}<br>`);
}

function error(msg) {
    // logs an error message to console and to the log div
    console.log(msg)
    $('.logs p').prepend(`> <span style="color:red;font-weight:bold;">${msg}</span><br>`);
}

function get_group() {
    // Gets the group ID of the current page
    params = new URLSearchParams(document.location.search);
    return params.get('group')
}

function start_stream(info) {
    // start the video stream.
    // info keys are names of streams, the value is an object with data for that stream.
    var video_socket = io('/video_stream');  // where to receive the video frames

    var video_info = info['Video']
    var audio_info = info['Audio']

    video_socket.on('connect', function() {
        console.log("Video streaming socketIO connected to server");
        data = {}
        if (video_info.id != undefined) {
            data.video = video_info.id;
        }
        if (audio_info.id != undefined) {
            data.audio = audio_info.id;
        }
        video_socket.emit('start', data);
    });

    // original width and height sent from stream
    var stream_width = video_info.width;
    var stream_height = video_info.height;
    var ratio = stream_width/stream_height
    var height = 600; // desired height in browser
    var width = Math.round(ratio*height)  // set width to maintain aspect ratio

    var vid = document.getElementById("video_stream");
    vid.setAttribute("width", width);
    vid.setAttribute("height", height);
    vid.onplay = skip  // call skip() on play

    info.speed += 0.1  // add 10% to playback speed to keep it updated
    vid.playbackRate = video_info.speed;  // set playback speed
    vid.defaultPlaybackRate = video_info.speed  // gotta set this too or it doesn't work

    $('button.skip').on('click', skip)
    function skip() {  // called onplay to skip to live
        // for some reason this doesn't work in Microsoft Edge
        vid.currentTime = Math.floor(vid.duration);
    }

    var jmuxer = new JMuxer({
        node: 'video_stream',
        mode: 'audio',  // video and audio
        //flushingTime: 0,
        //fps: info.framerate,

        debug: true
    });

    // feed received bytes data into jmuxer
    video_socket.on('data', (data) => {
        console.log(data.video.byteLength, data.audio.byteLength)
        //jmuxer.feed({video: new Uint8Array(data.video), audio: new Uint8Array(data.audio)});
        jmuxer.feed({audio: new Uint8Array(data.audio, duration: 1000});
    });
}

$(document).ready(function() {
    var server_socket = io('/browser');  // communication with server
    var group = get_group()  // group ID for this page
    console.log("ID: "+group)

    server_socket.on('connect', function() {
        log("SocketIO connected to server");
    });

    server_socket.on('disconnect', function() {
        log("SocketIO disconnected from server");
    });

    server_socket.on('log', function(msg) {
        //log(msg);
    });

    server_socket.on('error', function(msg) {
        //error(msg)
    });

    // request the meta data for all streams in this group
    server_socket.emit('info', group)
    server_socket.on('info', function(info) {
        // info keys are names of streams, the value is an object with data for that stream.
        start_stream(info);
    });

    // request time update every second
    setInterval(function() {
        server_socket.emit('stream_time', group);
    }, 1000);

    server_socket.on('stream_time', function(data) {
        $("div.stream_time").html(data);
    });


});
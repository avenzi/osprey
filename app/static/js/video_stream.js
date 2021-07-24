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
    // given the stream info, start the video stream with that data
    var video_socket = io('/video_stream');  // where to receive the video frames

    video_socket.on('connect', function() {
        console.log("Video streaming socketIO connected to server");
        video_socket.emit('start', info.id);
    });

    // original width and height sent from stream
    var stream_width = info.width;
    var stream_height = info.height;
    var ratio = stream_width/stream_height
    var height = 600; // desired height in browser
    var width = Math.round(ratio*height)  // set width to maintain aspect ratio

    var vid = document.getElementById("stream");
    vid.setAttribute("width", width);
    vid.setAttribute("height", height);
    vid.onplay = skip  // call skip() on play

    info.speed += 0.1  // add 10% to playback speed to keep it updated
    vid.playbackRate = info.speed;  // set playback speed
    vid.defaultPlaybackRate = info.speed  // gotta set this too or it doesn't work

    $('button.skip').on('click', skip)
    function skip() {  // called onplay to skip to live
        // for some reason this doesn't work in Microsoft Edge
        vid.currentTime = Math.floor(vid.duration);
    }

    var jmuxer = new JMuxer({
        node: 'stream',
        mode: 'video',
        flushingTime: 0,
        fps: info.framerate,
        debug: false
    });

    // feed received frame data into jmuxer
    video_socket.on('data', (frame) => {
        jmuxer.feed({video: new Uint8Array(frame)});
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

    // request the meta data for the stream 'Raw' in this group
    server_socket.emit('info', {group: group, stream:'Raw'})

    // request time update every second
    setInterval(function() {
        server_socket.emit('stream_time', group);
    }, 1000);

    server_socket.on('stream_time', function(data) {
        $("div.stream_time").html(data);
    });

    server_socket.on('info', function(data) {
        console.log("RECEIVED INFO:");
        console.log(data);
        start_stream(data);
    });
});
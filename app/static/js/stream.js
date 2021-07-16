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

$(document).ready(function() {
    var namespace = '/browser';  // namespace for talking with server
    var socket = io(namespace);

    socket.on('connect', function() {
        log("SocketIO connected to server");
    });

    socket.on('disconnect', function() {
        log("SocketIO disconnected from server");
    });

    socket.on('log', function(msg) {
        //log(msg);
    });

    socket.on('error', function(msg) {
        //error(msg)
    });

    // request update every second
    setInterval(function() {
        socket.emit('stream_time');
    }, 1000);

    socket.on('stream_time', function(data) {
        // data is an object with time info
        elapsed = data.elapsed;
        total = data.total

        if (total !== undefined) {  // given a total time
            display = `${elapsed} / ${total}`;
        } else if (elapsed !== undefined) {  // only elapsed time given
            display = elapsed;
        } else {  // no info given
            display = "[Time info unavailable]";
        }

        $("div.stream_time").html(display);

    });
});
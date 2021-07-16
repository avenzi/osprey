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

function get_id() {
    // Gets the group ID of the current page
    params = new URLSearchParams(document.location.search);
    return params.get('group')
}

function get_plot() {
    // todo: Use SocketIO instead just for consistency's sake?
    var req = new XMLHttpRequest();
    req.onreadystatechange = function() {
        if (req.readyState == 4 && req.status == 200)
            embed_plot(req.responseText);  // once data is received, embed the plot
    }
    url = window.location.pathname
    query = '?group=' + get_id()
    req.open("GET", url+'/plot_layout'+query, true);
    req.send(null);   // send GET request for plot JSON
    console.log('sent request: '+url+'/plot_layout'+query)
}

function embed_plot(text) {
    json = JSON.parse(text)
    window.Bokeh.embed.embed_item(json, 'streamplot');  // embed received JSON into div with id='streamplot'
    console.log("Embedded initial plot")
}

function check_bokeh() {
    if (window.Bokeh !== undefined) {
        get_plot();
    } else {
        attempts = 0;
    timer = setInterval(attempt_load, 10, attempts)
    }
}

function attempt_load(attempts) {
    console.log("Failed to load - trying again ("+attempts+")")
    if (window.Bokeh !== undefined) {
        clearInterval(timer);
        get_plot();
    } else {
        attempts++;
        if (attempts > 100) {
            clearInterval(timer);
            console.log("Bokeh: ERROR: Unable to run BokehJS code because BokehJS library is missing");
        }
    }
}

$(document).ready(function() {
    var namespace = '/browser';  // namespace for talking with server
    var socket = io(namespace);
    var id = get_id()  // group ID for this page
    console.log("ID: "+id)

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

    // set up bokeh
    if (document.readyState != "loading") Bokeh.safely(check_bokeh);
    else document.addEventListener("DOMContentLoaded", Bokeh.safely(check_bokeh));

    // request time update every second
    setInterval(function() {
        socket.emit('stream_time', id);
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
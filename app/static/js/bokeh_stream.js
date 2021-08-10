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
    // sends a request to the server for the Bokeh plot page
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
    // Use bokeh to embed the plot into the page
    json = JSON.parse(text)
    window.Bokeh.embed.embed_item(json, 'streamplot');  // embed received JSON into div with id='streamplot'
    console.log("Embedded initial plot")
}

function check_bokeh() {
    // verify that bokeh is functioning in the page
    if (window.Bokeh !== undefined) {
        get_plot();
    } else {
        attempts = 0;
    timer = setInterval(attempt_load, 10, attempts)
    }
}

function attempt_load(attempts) {
    // attempt to load the bokeh plot
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

function add_method(current_value) {
    // add a new dropdown menu to the top of the page with a given list of methods
    // to select another custom function to add to the pipeline.
    // If current_value is given, set that as the selected option.
    select = $(`<select class="function_select" onchange="function_select_change(this);">\
                   <option value="">--Select a function--</option>\
                </select>
    `).appendTo("div.custom_functions div.menus");

    // set current value, if given
    if (current_value != undefined) {
        select.value = current_value
    }

    // add an option for each method in the new select menu
    for (func of functions) {
        select.append(`<option value="${func}">${func}</option>`)
    }

    // assign an order number to the select menu
    order = pipeline.length
    select.data('order', order);

    console.log("NEW MENU: "+order+"  "+select.value);
}

function function_select_change(select) {
    // called when a method is selected in a dropdown menu.
    // adds selected value to pipeline in the right spot
    order = select.data('order');
    name = select.value;
    pipeline[order] = name
    console.log(`order: ${order}, val: ${value}`)
    console.log(pipeline)
    socket.emit('update_pipeline', {group: id, pipeline: pipeline})
}

var functions = [];  // list of function names available
var pipeline = [];   // list of function names in the current pipeline


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
        $("div.stream_time").html(data);
    });

    // Custom function interface


    // request a list of the available function names and
    //  a list of the currently selected functions for this page
    socket.emit('custom_functions', id);
    socket.on('custom_functions', function(data) {  // receive this info
        functions = data.functions;
        console.log("new funcs: " + functions)
        $("div.custom_functions div.menus").empty()  // clear current selections
        for (selected of data.selected) {  // for each selected function
            add_method(selected)
        }
    });

    // add functionality to the + button, adds another dropdown menu
    $("div.custom_functions button.add").on('click', add_method)
});
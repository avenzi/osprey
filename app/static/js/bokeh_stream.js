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

function add_method() {
    // add a new dropdown menu to the top of the page with a given list of methods
    // to select another custom function to add to the pipeline.
    // When an option is selected, call update_selection and pass in the jQuery rep of the select menu
    dropdown = $(`<select class="function_select" onchange="update_selection($(this));">\
                   <option value="">--Select a function--</option>\
                </select>
    `).appendTo("div.custom_functions div.menus");

    // add an option for each method in the new select menu
    for (func of functions) {
        dropdown.append(`<option value="${func}">${func}</option>`)
    }

    order = selected.length
    selected.push('')  // add an empty spot to the storage array
    dropdown.data('order', order);  // assign order number to this dropdown menu
    return dropdown  // return this element
}

function set_method(dropdown, name) {
    // set the currently selected option for a given jQuery select element
    console.log("Set Current Value")
    console.log(name)

    order = dropdown.data('order');
    dropdown.val(name)
    selected[order] = name  // store value in right spot
}

function update_selection(dropdown) {
    // called when a method is selected in a dropdown menu.
    // adds selected value to pipeline in the right spot
    order = dropdown.data('order');
    name = dropdown.val();
    selected[order] = name  // store value in right spot
    socket.emit('update_pipeline', {group: id, selected: selected})  // send info to server
}

var namespace = '/browser';  // namespace for talking with server
var socket = io(namespace);

var id = get_id()  // group ID for this page
console.log("ID: "+id)

var functions = [];  // list of function names available
var selected = [];   // list of function names currently selected for this page


$(document).ready(function() {
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

    // Custom function interface:
    // request a list of the available function names and
    //  a list of the currently selected functions for this page
    socket.emit('custom_functions', id);
    socket.on('custom_functions', function(data) {  // receive this info
        // data.available is a list of function names that are available to select
        // data.selected is a list of function names that are currently selected
        console.log("available funcs: " + data.available)
        functions = data.available
        $("div.custom_functions div.menus").empty()  // clear current selections
        for (name of data.selected) {  // iterate over selected functions
            dropdown = add_method()  // add a new select menu
            set_method(dropdown, name)  // set it's value
        }
    });

    // add functionality to the + button, adds another dropdown menu
    $("div.custom_functions button.add").on('click', add_method)
});
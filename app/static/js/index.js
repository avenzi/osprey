function log(msg) {
    // logs a message to console and to the log div
    console.log(msg)
    $('.logs > p').prepend('> ' + msg + '<br>');  // append a message to the log
}


$(document).ready(function() {
    var namespace = '/browser';  // namespace for talking with server
    var socket = io(namespace);
    var selected_file = ""  // currently selected file

    socket.on('connect', function() {
        log("SocketIO connected to server");
    });

    socket.on('disconnect', function() {
        log("SocketIO disconnected from server");
    });

    socket.on('log', function(msg) {
        log(msg);
    });

    socket.on('error', function(msg) {
        log(`<span style="color:red;font-weight:bold;">${msg}</span>`)
    });

    socket.on('update_pages', function(data) {
        // data is a list of dictionaries with info on each stream
        console.log("getting update");
        $('.streams ul').empty()
        data.forEach(function(info) {
            $('.streams ul').append(`<li><a href='/stream?group=${info['name']}'>${info['name']}</a></li>`);
        });
    });

    socket.on('update_files', function(data) {
        // data is a list of file names
        console.log("getting data directory update");
        selected_file = ""  // clear selected file
        $('.files ul').empty()
        data.forEach(function(filename) {
            $('div.files ul').append(`<li>${filename}</li>`);
        });

        // each file name will set the selected_file variable with its own filename
        $('div.files li').on('click', function(event) {
            $("div.files li.selected").removeClass('selected');  // unset selected form prev
            $(event.target).addClass('selected')  // set selected
            selected_file = $(event.target).text();  // set currently selected file
        });
    });

    socket.on('update_buttons', function(data) {
        // data is a list of dictionaries with updated values of some buttons
        console.log("getting button update");
        data.forEach(function(info) {
            console.log(info);
        });
    });


    var name_dialog = $('.name_dialog').dialog({
        autoOpen: false,
        height: 400,
        width: 350,
        modal: true,
        buttons: {
            "Ok": function() {
                console.log("SEND NAME OK: "+$('#file_name').val())
                $(this).dialog("close");
            },
            "Cancel": function() {
                $(this).dialog("close");
            }
        },
        close: function() {
            name_form[0].reset();
            //name.removeClass("ui-state-error");
        }
    });

    var confirm_dialog = $('.confirm_dialog').dialog({
        autoOpen: false,
        height: 400,
        width: 350,
        modal: true,
        buttons: {
            "Ok": function() {
                console.log("SEND CONFIRM OK")
                $(this).dialog("close");
            },
            "Cancel": function() {
                $(this).dialog("close");
            }
        }
    });

    var error_dialog = $('.error_dialog').dialog({
        autoOpen: false,
        height: 400,
        width: 350,
        modal: true,
        buttons: {
            "Ok": function() {
                console.log("ERROR OK")
                $(this).dialog("close");
            }
        }
    });

    name_dialog.find("form").on("submit", function(event) {
        event.preventDefault();
        console.log("PREVENTED DEFAULT");
    });

    // each command button emits an event to the server
    $('div.stream_commands button.command').on('click', function(event) {
        socket.emit(event.target.value);
    });

    $('div.file_commands button.load').on('click', function(event) {
        socket.emit(event.target.value, selected_file);
    });

    $('div.file_commands button.rename').on("click", function() {
        name_dialog.dialog("open");
    });

    $('div.file_commands button.delete').on('click', function(event) {
        confirm_dialog.dialog("open");
    });
});
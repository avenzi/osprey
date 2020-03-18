$(document).ready(function () {
    $('#defaultChecked1').click(function(e) {
        if ($(this).is(':checked')) {
            console.log("checked")
        }
        else {
            console.log("unchecked")
        }
        e.stopImmediatePropagation();
    });

    $('#audCheck').click(function(e) {
        (function doPoll() {
            console.log("clicked");
            date = new Date();
            req1 = $.post('update_audio', {status : 'ON', date : date}, function(data){
                $('#decibels').text("Current dB: " + data.decibels);
            })
            if ($('#audCheck').is(':checked')) {
                req1.always(function(){
                    console.log("checked");
                    setTimeout(doPoll, 500);
                });
            }
            else {
                console.log("unchecked");
                date = new Date();
                req2 = $.post('update_audio', {status : 'OFF', date : date});
                $('#decibels').text('Current dB: --.-');
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });

    $('#tempCheck').click(function(e) {
        console.log("clicked")
        (function doPoll() {

            if ($('#tempCheck').is(':checked')) {
                //req1 = $.post('update_eventlog_temperature', {status : 'ON'}, function(data){
                    //$('#eventLog').append(data);
                //})
                //.done()
                always(function(){
                    console.log("checked")
                    setTimeout(doPoll, 6000);
                });
            }
            else {
                //req2 = $.post('update_eventlog_temperature', {status : 'OFF'});
                //req1.abort();
                console.log("unchecked")
            }
        }());
        e.stopImmediatePropagation();
    });
});
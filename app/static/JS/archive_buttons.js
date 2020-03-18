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
        console.log("clicked")
        (function doPoll() {

            if ($('#audCheck').is(':checked')) {

                //req1 = $.post('update_eventlog_audio', {status : 'ON'}, function(data){
                    //$('#eventLog').append(data);
                //})
                //.done()
                always(function(){
                    console.log("checked")
                    setTimeout(doPoll, 6000);
                });
            }
            else {
                //req2 = $.post('update_eventlog_audio', {status : 'OFF'});
                //req1.abort();
                console.log("unchecked")
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
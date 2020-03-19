$(document).ready(function () {
    //archive video
    $('#defaultChecked1').click(function(e) {
        if ($(this).is(':checked')) {
            var httpRequest = new XMLHttpRequest();
            httpRequest.open('GET', 'start', true);
            httpRequest.onreadystatechange = function(e) {
                if (httpRequest.readyState == 4) {
                    if (httpRequest.status == 200) {
                        console.log('SUCCESS');
                    }
                    else console.log('HTTP ERROR');
                }
            }
            httpRequest.send();
        }
        else {
            var httpRequest = new XMLHttpRequest();
            httpRequest.open('GET', 'stop', true);
            httpRequest.onreadystatechange = function(e) {
                if (httpRequest.readyState == 4) {
                    if (httpRequest.status == 200) {
                        console.log('SUCCESS');
                    }
                    else console.log('HTTP ERROR');
                }
            }
            httpRequest.send();
        }
        e.stopImmediatePropagation();
    });

    // archive audio
    $('#audCheck').click(function(e) {
        (function doPoll() {
            console.log("clicked");
            date = new Date();
            req1 = $.post('update_audio', {status : 'ON', date : date}, function(data){
                $('#decibels_archives').text("Current dB: " + data.decibels);
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
                $('#decibels_archives').text('Current dB: --.-');
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });

    // archive temp
    $('#tempCheck').click(function(e) {
        (function doPoll() {
            console.log("clicked");
            date = new Date();
            req1 = $.post('update_sense', {status : 'ON', date : date}, function(data){
                $('#roomTemperature_archives').text(data.roomTemperature);
                $('#airPressure_archives').text(data.airPressure);
                $('#airHumidity_archives').text(data.airHumidity);
            })
            if ($('#tempCheck').is(':checked')) {
                console.log("checked");
                req1.always(function(){
                    setTimeout(doPoll, 500);
                });
            }
            else {
                console.log("unchecked");
                date = new Date();
                req2 = $.post('update_sense', {status : 'OFF', date : date});
                $('#roomTemperature_archives').text('--.-');
                $('#airPressure_archives').text('--.-');
                $('#airHumidity_archives').text('--.-');
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });
});
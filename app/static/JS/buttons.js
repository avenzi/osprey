$(document).ready(function () {

    $('#videoSwitch1').click(function() {
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


    $('#audioSwitch1').click(function(e) {
        (function doPoll() {
            date = new Date();
            req1 = $.post('update_audio', {status : 'ON', date : date}, function(data){
                $('#decibels').text("Current dB: " + data.decibels);
            })
            if ($('#audioSwitch1').is(':checked')) {
                req1.always(function(){
                    setTimeout(doPoll, 5000);
                });
            }
            else {
                date = new Date();
                req2 = $.post('update_audio', {status : 'OFF', date : date});
                $('#decibels').text('Current dB: --');
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });


    $('#senseSwitch1').click(function(e) {
        (function doPoll() {
            date = new Date();
            req1 = $.post('update_sense', {status : 'ON', date : date}, function(data){
                $('#roomTemperature').text(data.roomTemperature);
                $('#skinTemperatureSub1').text(data.skinTemperatureSub1);
                $('#skinTemperatureSub2').text(data.skinTemperatureSub2);
            })
            if ($('#senseSwitch1').is(':checked')) {
                req1.always(function(){
                    setTimeout(doPoll, 5000);
                });
            }
            else {
                date = new Date();
                req2 = $.post('update_sense', {status : 'OFF', date : date});
                $('#roomTemperature').text('--.-');
                $('#skinTemperatureSub1').text('--.-');
                $('#skinTemperatureSub2').text('--.-');
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });


    $('#videoCheck').click(function(e) {
        if ($(this).is(':checked')) {
            //alert('Checked')
        }
        else {
            //alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });
    

    $('#audioCheck').click(function(e) {
        (function doPoll() {

            if ($('#audioCheck').is(':checked')) {

                req1 = $.post('update_eventlog_audio', {status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    setTimeout(doPoll, 6000);
                });
            }
            else {
                req2 = $.post('update_eventlog_audio', {status : 'OFF'});
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });


    $('#temperatureCheck').click(function(e) {
        (function doPoll() {

            if ($('#temperatureCheck').is(':checked')) {
                req1 = $.post('update_eventlog_temperature', {status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    setTimeout(doPoll, 6000);
                });
            }
            else {
                req2 = $.post('update_eventlog_temperature', {status : 'OFF'});
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });


    $('#triggerSettingsSubmit').click(function(e) {
        var audio_input = $('#audioInput').val();
        var temperature_input = $('#temperatureInput').val();
        req = $.post('update_triggersettings', {audio_input : audio_input, temperature_input : temperature_input});
        e.stopImmediatePropagation();
    });


    $('#algorithmModalButton').click(function(e) {
        $.get('file_upload', function(data){
            $('#availableAlgorithms').html(data);
        });
        // e.stopImmediatePropagation();
    });


    $('#uploadFileSubmit').click(function(e) {
        formData = new FormData();
        for (file of document.getElementById('uploadFileInput').files) {
            formData.append('file', file);
        }
        $.ajaxSetup({
            // Preventing TypeError : Illegal Invocation from jQuery trying to transform the FormData object into a string
            processData: false,
            contentType: false
        });
        $.post('file_upload', formData, function(data){
            $('#availableAlgorithms').html(data);
        });
        e.stopImmediatePropagation();
    });

});
$(document).ready(function () {

//    $('#videoSwitch1').click(function() {
//        if ($(this).is(':checked')) {
//            var httpRequest = new XMLHttpRequest();
//           httpRequest.open('GET', 'start', true);
//            httpRequest.onreadystatechange = function(e) {
//                if (httpRequest.readyState == 4) {
//                    if (httpRequest.status == 200) {
//                        console.log('SUCCESS');
//                    }
//                    else console.log('HTTP ERROR');
//                }
//            }
//            httpRequest.send();
//        }
//        else {
//            var httpRequest = new XMLHttpRequest();
//            httpRequest.open('GET', 'stop', true);
//            httpRequest.onreadystatechange = function(e) {
//                if (httpRequest.readyState == 4) {
//                    if (httpRequest.status == 200) {
//                        console.log('SUCCESS');
//                    }
//                    else console.log('HTTP ERROR');
//                }
//            }
//            httpRequest.send();
//        }
//        e.stopImmediatePropagation();
//    });


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

    $('#pressureCheck').click(function(e) {
        (function doPoll() {

            if ($('#pressureCheck').is(':checked')) {
                req1 = $.post('update_eventlog_pressure', {status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    setTimeout(doPoll, 6000);
                });
            }
            else {
                req2 = $.post('update_eventlog_pressure', {status : 'OFF'});
                req1.abort();
            }
        }());
        e.stopImmediatePropagation();
    });

    $('#humidityCheck').click(function(e) {
        (function doPoll() {

            if ($('#humidityCheck').is(':checked')) {
                req1 = $.post('update_eventlog_humidity', {status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    setTimeout(doPoll, 6000);
                });
            }
            else {
                req2 = $.post('update_eventlog_humidity', {status : 'OFF'});
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


    // Algorithms button to take you to the uploads menu within the modal
    // The off() function of the jQuery selector removes the event handler attached to the element so it does not get called more than once
    $('#algorithmModalOpenButton').off().click( function(e) {
        $.get('algorithm_upload', function(data){
            $('#algorithmModalContent').html(data);
        });
    });


    // Back button to take you to the uploads menu within the modal, from the view section
    $('#algorithmModalBackButton').click( function(e) {
        $.get('algorithm_upload', function(data){
            $('#algorithmModalContent').html(data);
        });
    });


    // Posts a file to be uploaded and displays the updated uploads menu within the modal
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
        $.post('algorithm_upload', formData, function(data){
            $.ajaxSetup({
                // Setting variables back to default to allow for JSON parsing
                processData: true,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8'
            });

            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });

    
    // Select button for an uploaded algorithm
    $('.availableAlgorithmsRunButton').click(function(e) {
        $.post('algorithm_handler', {'button' : 'select', 'filename' : this.id}, function(data){
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });


    // View button for an uploaded algorithm
    $('.availableAlgorithmsViewButton').click(function(e) {
        $.post('algorithm_handler', {'button' : 'view', 'filename' : this.id}, function(data) {
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });


    // Delete button for an uploaded algorithm 
    $('.availableAlgorithmsDeleteButton').click(function(e) {
        $.post('algorithm_handler', {'button' : 'delete', 'filename' : this.id}, function(data) {
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });


});

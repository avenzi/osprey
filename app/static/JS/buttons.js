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



   // Code to handle switching between video streams
   // Hide streams 2 and 3 on page load
   $('#stream2').hide();	
   $('#stream3').hide();

   $('#video1').click(function(e) {
	$('#stream2').hide();
	$('#stream1').show();
	$('#stream3').hide();
   });

   $('#video2').click(function(e) {
	$('#stream1').hide();
	$('#stream2').show();
	$('#stream3').hide();
   });
   
   $('#video3').click(function(e) {
	$('#stream1').hide();
	$('#stream2').hide();
	$('#stream3').show();
   });


    $('#audioSwitch1').click(function(e) {
        if ($('#audioSwitch1').is(':checked')){
            intervalIDa = setInterval(function() {
                date = new Date();
                $.post('update_audio', {status : 'ON', date : date}, function(data){
                    $('#decibels').text("Current dB: " + data.decibels);
            });
            }, 1000);
        }
        else {
            clearInterval(intervalIDa);

            // Clear form data after 1.2s to prevent async issues
            setTimeout(function (){
                $('#decibels').text('Current dB: --.-');
            }, 1200);
        }
    });


    // Handle sense Switch Functionality
    // Hide sense cards on page load
    $('#sense1').hide();
    $('#sense2').hide();

    $('#senseSwitch1').click(function() {
        $('#sense1').show();
        if ($('#senseSwitch1').is(':checked')){
            intervalID1 = setInterval(function() {
                date = new Date();
                $.post('update_sense1', {status : 'ON', date : date}, function(data){
                    $('#roomTemperature1').text(data.roomTemperature);
                    $('#airPressure1').text(data.airPressure);
                    $('#airHumidity1').text(data.airHumidity);
                    $('#atm1').text('Atmosphere ('.concat(data.ip, ')'));
                });
            }, 1000)
        }
        else {
            clearInterval(intervalID1);

            // Clear form data after 1.2s to prevent async issues
            setTimeout(function () {
                $('#roomTemperature1').text('--.-');
                $('#airPressure1').text('--.-');
                $('#airHumidity1').text('--.-');
            }, 1200);
        }
    });


    $('#senseSwitch2').click(function() {
        $('#sense2').show();
        if ($('#senseSwitch2').is(':checked')){
            intervalID2 = setInterval(function() {
                date = new Date();
                $.post('update_sense2', {status : 'ON', date : date}, function(data){
                    $('#roomTemperature2').text(data.roomTemperature);
                    $('#airPressure2').text(data.airPressure);
                    $('#airHumidity2').text(data.airHumidity);
                    $('#atm2').text('Atmosphere ('.concat(data.ip, ')'));
                });
            }, 1000);
        }
        else {
            clearInterval(intervalID2);

            // Clear form data after 1.2s to prevent async issues
            setTimeout(function () {
                $('#roomTemperature2').text('--.-');
                $('#airPressure2').text('--.-');
                $('#airHumidity2').text('--.-');
            }, 1200);
        }
    });




    var videoCounter = 0;
    $('#videoCheck').click(function(e) {
        (function doPoll() {

            var initial = 'NO'

            if ($('#videoCheck').is(':checked')) {
                // If the box has just been checked
                if (videoCounter == 0) {
                    initial = 'YES'
                }

                req1 = $.post('update_eventlog', {data_type : 'video', initial : initial, status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    videoCounter ++;
                    setTimeout(doPoll, 1000);
                });
            }

            else {
                req2 = $.post('update_eventlog', {data_type : 'video', initial : initial, status : 'OFF'});
                videoCounter = 0
                req1.abort();
            }

        }());

        e.stopImmediatePropagation();
    });
    

    var audioCounter = 0;
    $('#audioCheck').click(function(e) {
        (function doPoll() {

            var initial = 'NO'

            if ($('#audioCheck').is(':checked')) {
                // If the box has just been checked
                if (audioCounter == 0) {
                    initial = 'YES'
                }

                req1 = $.post('update_eventlog', {data_type : 'audio', initial : initial, status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    audioCounter ++;
                    setTimeout(doPoll, 1000);
                });
            }

            else {
                req2 = $.post('update_eventlog', {data_type : 'audio', initial : initial, status : 'OFF'});
                audioCounter = 0
                req1.abort();
            }

        }());

        e.stopImmediatePropagation();
    });
    

    var temperatureCounter = 0;
    $('#temperatureCheck').click(function(e) {
        (function doPoll() {

            var initial = 'NO'

            if ($('#temperatureCheck').is(':checked')) {
                // If the box has just been checked
                if (temperatureCounter == 0) {
                    initial = 'YES'
                }

                req1 = $.post('update_eventlog', {data_type : 'temperature', initial : initial, status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    temperatureCounter ++;
                    setTimeout(doPoll, 1000);
                });
            }

            else {
                req2 = $.post('update_eventlog', {data_type : 'temperature', initial : initial, status : 'OFF'});
                temperatureCounter = 0
                req1.abort();
            }

        }());

        e.stopImmediatePropagation();
    });


    var pressureCounter = 0;
    $('#pressureCheck').click(function(e) {
        (function doPoll() {

            var initial = 'NO'

            if ($('#pressureCheck').is(':checked')) {
                // If the box has just been checked
                if (pressureCounter == 0) {
                    initial = 'YES'
                }

                req1 = $.post('update_eventlog', {data_type : 'pressure', initial : initial, status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    pressureCounter ++;
                    setTimeout(doPoll, 1000);
                });
            }

            else {
                req2 = $.post('update_eventlog', {data_type : 'pressure', initial : initial, status : 'OFF'});
                pressureCounter = 0
                req1.abort();
            }

        }());

        e.stopImmediatePropagation();
    });


    var humidityCounter = 0;
    $('#humidityCheck').click(function(e) {
        (function doPoll() {

            var initial = 'NO'

            if ($('#humidityCheck').is(':checked')) {
                // If the box has just been checked
                if (humidityCounter == 0) {
                    initial = 'YES'
                }

                req1 = $.post('update_eventlog', {data_type : 'humidity', initial : initial, status : 'ON'}, function(data){
                    $('#eventLog').append(data);
                })
                .done()
                .always(function(){
                    humidityCounter ++;
                    setTimeout(doPoll, 1000);
                });
            }

            else {
                req2 = $.post('update_eventlog', {data_type : 'humidity', initial : initial, status : 'OFF'});
                humidityCounter = 0
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

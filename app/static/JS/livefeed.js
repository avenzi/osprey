$(document).ready(function () {


    // Updating the eventlog front end
    (function doPoll() {
        $.get("update_eventlog", function(data) {
            $("#eventLog").html(data)
        })
        .always(function(){
            // Was 1000
            setTimeout(doPoll, 1000);
            });
    }());


    // Handle scalar trigger ok buttion
    $('#triggerSettingsSubmit').click(function(e) {
        var audio_input = $('#audioInput').val();
        var temperature_input = $('#temperatureInput').val();
        var pressure_input = $('#pressureInput').val();
        var humidity_input = $('#humidityInput').val();

        req = $.post('update_triggersettings', {audio_input : audio_input, temperature_input : temperature_input, pressure_input : pressure_input, humidity_input : humidity_input});
    });


    // Handle scalar trigger clear button
    $('#triggerSettingsClear').click(function(e) {
        $('#audioInput').val('');
        $('#temperatureInput').val('');
        $('#pressureInput').val('');
        $('#humidityInput').val('');

        req = $.post('update_triggersettings', {audio_input : '', temperature_input : '', pressure_input : '', humidity_input : ''});
        e.stopImmediatePropagation();
    })


    // Algorithms button to take you to the uploads menu within the modal
    // The off() function of the jQuery selector removes the event handler attached to the element so it does not get called more than once
    $('#algorithmModalOpenButton').off().click( function(e) {
        $.get('algorithm_upload', function(data){
            $('#algorithmModalContent').html(data);
        });
    });


});

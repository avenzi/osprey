/**
 * @fileoverview This file is used to update the eventlog and handle all events that 
 * occur in the livefeed page other than the Sensor Controls
 */

$(document).ready(function () {

    /* Updates the eventlog front end every second */
    (function doPoll() {
        var now = Math.round(Date.now());
        $.get(`retrieve_eventlog/${now}/0/0`, function(data) {
            $("#eventLog").html(data)
        })
        .always(function(){
            setTimeout(doPoll, 1000);
        });
    }());

    /* Sets scalar triggers */
    $("#triggerSettingsSubmit").click(function(e) {
        var temperature_input = $("#temperatureInput").val();
        var pressure_input = $("#pressureInput").val();
        var humidity_input = $("#humidityInput").val();

        req = $.post("update_triggersettings", {temperature_input : temperature_input, pressure_input : pressure_input, humidity_input : humidity_input});
    });

    /* Clears scalar trigger settings */
    $("#triggerSettingsClear").click(function(e) {
        $("#temperatureInput").val("");
        $("#pressureInput").val("");
        $("#humidityInput").val("");

        req = $.post("update_triggersettings", {temperature_input : "", pressure_input : "", humidity_input : ""});
    })

    /* Opens the algorithmModal and displays the uploads menu */
    $("#algorithmModalOpenButton").off().click( function(e) {
        $.get("algorithm_upload", function(data){
            $("#algorithmModalContent").html(data);
        });
    });
});
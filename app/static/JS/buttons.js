$(document).ready(function () {

    $('#videoSwitch1').click(function(e) {
        alert("videoSwitch1");
        // Preventing other listeners of the same event from being called
        e.stopImmediatePropagation();
    });

});
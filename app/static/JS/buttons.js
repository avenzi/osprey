$(document).ready(function () {

    $('#videoSwitch1').click(function() {
        if ($(this).is(':checked')) {
            var httpRequest = new XMLHttpRequest();
            // URL is subject to change if Raspberry Pi IP is not static
            httpRequest.open('GET', 'http://192.168.86.91', true);
            httpRequest.onreadystatechange = function(e) {
                if (httpRequest.readyState == 4) {
                    if (httpRequest.status == 200) {
                        alert('SUCCESS');
                    }
                    else alert('HTTP ERROR');
                }
            }
            httpRequest.send();
        }
        else {
            alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });


    $('#audioSwitch1').click(function(e) {
        if ($(this).is(':checked')) {
            alert('Checked')
        }
        else {
            alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });


    $('#senseSwitch1').click(function(e) {
        if ($(this).is(':checked')) {
            alert('Checked')
        }
        else {
            alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });


    $('#videoCheck').click(function(e) {
        if ($(this).is(':checked')) {
            alert('Checked')
        }
        else {
            alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });   
    
    
    $('#audioCheck').click(function(e) {
        if ($(this).is(':checked')) {
            alert('Checked')
        }
        else {
            alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });


    $('#temperatureCheck').click(function(e) {
        if ($(this).is(':checked')) {
            alert('Checked')
        }
        else {
            alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });


    $('#collapseExample').click(function(e) {
        alert('Hello');
        e.stopImmediatePropagation();
    });

});
$(document).ready(function () {

    $('#videoSwitch1').click(function() {
        if ($(this).is(':checked')) {
            var httpRequest = new XMLHttpRequest();
            httpRequest.open('GET', 'receiver', true);
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
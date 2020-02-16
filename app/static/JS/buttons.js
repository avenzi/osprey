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
        if ($(this).is(':checked')) {
            alert('Checked')
        }
        else {
            alert('Unchecked')
        }
        e.stopImmediatePropagation();
    });


    $('#senseSwitch1').click(function(e) {
        (function doPoll() {
            req = $.get('update_sense', function(data){
                $('#roomTemperature').text(data.roomTemperature);
                $('#skinTemperatureSub1').text(data.skinTemperatureSub1);
                $('#skinTemperatureSub2').text(data.skinTemperatureSub2);
            })
            if ($('#senseSwitch1').is(':checked')) {
                req.always(function(){
                    setTimeout(doPoll, 5000);
                });
            }
            else {
                $('#roomTemperature').text('--.-');
                $('#skinTemperatureSub1').text('--.-');
                $('#skinTemperatureSub2').text('--.-');
                req.abort();
            }
        }());
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
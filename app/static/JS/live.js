$(document).ready(function () {
    // Default to 1 of each sensor type
    var senseNumber = 1;
    var audioNumber = 1;

    var cameraNumber = 0;

    // Define max sensors
    var maxCam = 10;
    var maxSense = 2;
    var maxAudio = 1;

    var cameraIPS = ["35.9.42.110", "35.9.42.212", "35.9.42.245", 
    "35.9.42.110", "35.9.42.212", "35.9.42.245", 
    "35.9.42.110", "35.9.42.212", "35.9.42.245", "35.9.42.110"];

    // Hide sensors on page load
   $("#sense2").hide();


    // open dialog form immediately, grey out everything else, disable closing without submitting the form
    $(function() {
        $( "#dialog" ).dialog({
            modal:true,

            // commented out closing disable for testing
            //closeOnEscape: false,
            //open: function(event, ui) {
            //    $(".ui-dialog-titlebar-close", $(this).parent()).hide();
           // }
        });
    });

    $(document).on('click','#dialogSubmit',function(e) {
        e.preventDefault();
        var queryString = $('#sensorForm').serialize();
        var query = queryString.split("&");

        if (cameraNumber > 0){
            // Create correct number of video selectors
            for (var i=1;i<=cameraNumber;i++){
                var checked = "";
                if (i==1) {
                    checked = " checked";
                }

                var block = `
                <div class="col">
                    <div class="radio d-inline">
                        <label>
                            <input type="radio" name="video" id="video${i}" autocomplete="off"${checked}> Video ${i}
                        </label>
                    </div>
                </div>`;
                $("#videoRow").append(block);
            }

            // Create iframe tags using form input
            for (var i=1;i<=cameraNumber;i++){
                var ip = query[i-1].split("=")[1];
                var block=`
                    <div class="embed-responsive embed-responsive-16by9" id="stream${i}">
                        <iframe class="embed-responsive-item" src="http://${ip}:8000/stream.mjpg" allowfullscreen></iframe>
                    </div>
                `;
                $("#videoDiv").append(block);

            }
        } else {
            // No cameras active, hide videos and selectors
            $("#videoDiv").hide();
            $("#videoRow").hide();
        }

        if (senseNumber > 0){
            // Create correct number of sensor selectors
            for (var i=1;i<=senseNumber;i++){
                var block=`
                <div class="col">
                    <div class="custom-control custom-switch d-inline">
                        <input type="checkbox" class="custom-control-input" id="senseSwitch${i}">
                        <label class="custom-control-label" for="senseSwitch${i}">Sense ${i}</label>
                    </div>
                </div>`;
                $("#senseRow").append(block);
                $(`#sense${i}`).show();
            }

        } else {
            // No sensors active, hide sensor selectors
            $("#senseRow").hide();
        }

        if (audioNumber > 0){
            // Create audio selectors
            for (var i=1;i<=audioNumber;i++) {
                var block=`
                <div class="col">
                    <div class="custom-control custom-switch">
                        <input type="checkbox" class="custom-control-input" id="audioSwitch1">
                        <label class="custom-control-label" for="audioSwitch1">Audio 1</label>
                    </div>
                </div>`;
                $("#audioRow").append(block);
            }

        } else {
            $("#audioRow").hide();
            $("#audioDiv").hide();
        }

        // Close the dialog box
        $('#dialog').dialog('close');

        // Create all normal live javascript now that all elements are correct
        live(cameraNumber, senseNumber, audioNumber);
    });

    $("#addCam").click(function(e) {
        e.preventDefault();

        // Maximum cameras
        if (cameraNumber < maxCam) {
            cameraNumber++;
            $("#cameraList").append(`<li><label for="camera${cameraNumber}">Camera ${cameraNumber} IP: </label>
            <input name="camera${cameraNumber}" id="camera${cameraNumber}" value="${cameraIPS[cameraNumber-1]}">`);
        }
    });

    $("#deleteCam").click(function(e) {
        e.preventDefault();

        // Can have 0 cameras but no less
        if (cameraNumber > 0){
            cameraNumber--;
            $('#cameraList li:last').remove();
        }
    } );

    $("#addSense").click(function(e) {
        e.preventDefault();

        // Maximum Sense HATs
        if (senseNumber < maxSense) {
            senseNumber++;
            $("#senseList").append('<li><label for="sense'.concat(senseNumber, '">Sense ',
            senseNumber, '</label></li>'));
        }
    });

    $("#deleteSense").click(function(e) {
        e.preventDefault();
        // Can have 0 Sense HATs but no less
        if (senseNumber > 0){
            senseNumber--;
            $('#senseList li:last').remove();
        }
    } );

    $("#addAudio").click(function(e) {
        e.preventDefault();

        // Maximum audio
        if (audioNumber < maxAudio) {
            audioNumber++;
            $("#audioList").append('<li><label for="audio'.concat(audioNumber, '">Audio ',
            audioNumber, '</label></li>'));
        }
    });

    $("#deleteAudio").click(function(e) {
        e.preventDefault();

        // Can have 0 Audio inputs but no less
        if (audioNumber > 0){
            audioNumber--;
            $('#audioList li:last').remove();
        }
    } );
});


// Code to handle switching between video streams
function generate_video_handler( k , numCams) {
    return function() { 
        for (var j=1;j<=numCams;j++) {
            if (j == k) {
                $(`#stream${j}`).show();
            } else {
                $(`#stream${j}`).hide();
            }
    }
    };
}

// Code to handle audio streams -- only works with one audio for now, all thats needed
function generate_audio_handler( k ) {
    return function() {
        if ($(`#audioSwitch${k}`).is(':checked')){
            intervalIDa = setInterval(function() {
                $.post('update_audio', {status : 'ON'}, function(data){
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
    }
}

// Code to handle sense streams -- should work with more than 2 sense streams, unable to test
function generate_sense_handler( k ) {
    return function() {
        $(`#sense${k}`).show();
        if ($(`#senseSwitch${k}`).is(':checked')){
            var intervalID = setInterval(function() {
                $.post(`update_sense${k}`, {status : 'ON'}, function(data){
                    $(`#roomTemperature${k}`).text(data.roomTemperature);
                    $(`#airPressure${k}`).text(data.airPressure);
                    $(`#airHumidity${k}`).text(data.airHumidity);
                    $(`#atm${k}`).text('Atmosphere ('.concat(data.ip, ')'));
                });
            }, 1000)
        }
        else {
            clearInterval(intervalID);

            // Clear form data after 1.2s to prevent async issues
            setTimeout(function () {
                $(`#roomTemperature${k}`).text('--.-');
                $(`#airPressure${k}`).text('--.-');
                $(`#airHumidity${k}`).text('--.-');
            }, 1200);
        }
    }
}

    // Need to make handlers variable to number of sensors
    var live = function(numCams, numSenses, numAudios) {
    // Deal with number of camera streams
    for (var i=1;i<=numCams;i++) {
            // Hide streams on page load
            if (i==1) {
                $('#stream1').show();
            } else {
                $(`#stream${i}`).hide();
            }
       
        // generate correct click handler for each video selector
        $(`#video${i}`).on("click", generate_video_handler(i, numCams))
   }

   // Deal with number of audio streams
   for (var i=1;i<=numAudios;i++) {
       $(`#audioSwitch${i}`).click( generate_audio_handler(i));
   }

   // Deal with number of sense streams
   for (var i=1; i<=numSenses;i++) {
       $(`#senseSwitch${i}`).on("click", generate_sense_handler(i));
   }
}
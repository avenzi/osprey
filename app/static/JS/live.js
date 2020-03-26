$(document).ready(function () {
    // Default to 1 of each sensor type
    var cameraNumber = 0;
    var senseNumber = 1;
    var audioNumber = 1;

    // Define max sensors
    var maxCam = 3;
    var maxSense = 2;
    var maxAudio = 1;

    var cameraIPS = ["35.9.42.110", "35.9.42.212", "35.9.42.245"];

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
        live();
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

// Need to make handlers variable to number of sensors
var live = function() {
   // Hide streams on page load
   $('#stream2').hide();	
   $('#stream3').hide();


   // Code to handle switching between video streams

   $('#video1').click(function(e) {
	$('#stream1').show();
	$('#stream2').hide();
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
    });


    // Handle sense Switch Functionality
    $('#senseSwitch1').click(function() {
        $('#sense1').show();
        if ($('#senseSwitch1').is(':checked')){
            intervalID1 = setInterval(function() {
                $.post('update_sense1', {status : 'ON'}, function(data){
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
                $.post('update_sense2', {status : 'ON'}, function(data){
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
}
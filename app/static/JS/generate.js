$(document).ready(function () {
    
    // $('#myModal').modal('show')

    // Default to 1 of each sensor type
    var senseNumber = 1;
    var audioNumber = 1;

    var cameraNumber = 0;

    // Define max sensors
    var maxCam = 10;
    var maxSense = 10;
    var maxAudio = 10;

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
    

    $("#addCam").click(function(e) {
        e.preventDefault();

        // Maximum cameras
        if (cameraNumber < maxCam) {
            cameraNumber++;
            cameraIPidx = (cameraNumber-1) % cameraIPS.length;

            $("#cameraList").append(`<li id="cam-${cameraNumber}"><label for="camera${cameraNumber}">Camera ${cameraNumber} IP: </label>
            <input name="camera${cameraNumber}" id="camera${cameraNumber}" value="${cameraIPS[cameraIPidx]}">
            <label for="cam-name${cameraNumber}">Camera ${cameraNumber} Name: </label>
            <input name="cam-name${cameraNumber}" id="cam-name${cameraNumber}" value="Camera ${cameraNumber}">
            </li>`);

            // $("#cameraList").append(
            //     `<li id="cam${cameraNumber}">
            //      <!-- <li id="cam${cameraNumber}" class="list-group-item"> -->
            //         <label for="camera${cameraNumber}">Camera ${cameraNumber} IP: </label>
            //         <input name="camera${cameraNumber}" id="camera${cameraNumber}" value="${cameraIPS[cameraIPidx]}">
            //         <!-- <button type="button" id="cam${cameraNumber}" class="close deleteCam" aria-label="Close">
            //             <span aria-hidden="true">&times;</span>
            //         </button> -->
            //     </li>`
            // );
        }
    });

    // $(document).on('click', '.close.deleteCam', function(e) {
    //     e.preventDefault();

    //     // Remove the Cam
    //     // var theId = "#".concat(e.currentTarget.id).concat(".list-group-item");
    //     // $(theId).remove();

    //     // Get the number of Cams
    //     // var x = document.getElementsByClassName("close deleteCam").length;
    //     // console.log(x)

    //     // If the Cam number is not 1, change the tag, subtract from all cam vals
    //     var blah = "#".concat(e.currentTarget.id).concat(".list-group-item");
    //     console.log($(blah).children()[0]);
    //     console.log($(blah).children()[1]);
    //     console.log($(blah).children()[2]);
    // } );

    $("#deleteCam").click(function(e) {
        e.preventDefault();

        // Can have 0 cameras but no less
        if (cameraNumber > 0) {
            $("#cam-" + cameraNumber).remove();
            cameraNumber--;
        }
    });

    $("#addAudio").click(function(e) {
        e.preventDefault();

        // Maximum audio
        if (audioNumber < maxAudio) {
            audioNumber++;

            $("#audioList").append(`<li id="mic-${audioNumber}"><label for="audio${audioNumber}">Microphone ${audioNumber} IP: </label>
            <input name="audio${audioNumber}" id="audio${audioNumber}" value="">
            <label for="mic-name${audioNumber}">Microphone ${audioNumber} Name: </label>
            <input name="mic-name${audioNumber}" id="mic-name${audioNumber}" value="Microphone ${audioNumber}">
            </li>`);

            // $("#audioList").append(
            //     `<li>
            //      <!-- <li class="list-group-item"> -->
            //         <label for="sense${audioNumber}">Sense ${audioNumber}</label>
            //         <!-- <button type="button" class="close" aria-label="Close">
            //             <span aria-hidden="true">&times;</span>
            //         </button> -->
            //     </li>`
            // );
        }
    });

    $("#deleteAudio").click(function(e) {
        e.preventDefault();

        // Can have 0 Audio inputs but no less
        if (audioNumber > 0){
            $("#mic-" + audioNumber).remove();
            audioNumber--;
        }
    });










    $("#addSense").click(function(e) {
        e.preventDefault();
    
        // Maximum Sense HATs
        if (senseNumber < maxSense) {
            senseNumber++;
            $("#senseList").append(
                `<li><label for="sense${senseNumber}">Sense HAT ${senseNumber} IP:</label>
                <input name="sense${senseNumber}" id="sense${senseNumber}" value="">
                <label for="sen-name${senseNumber}">Sense HAT ${senseNumber} Name: </label>
                <input name="sen-name${senseNumber}" id="sen-name${senseNumber}" value="Sense ${senseNumber}">
                </li>`
            );
    
            // $("#senseList").append(
            //     `<li>
            //      <!-- <li class="list-group-item"> -->
            //         <label for="sense${senseNumber}">Sense ${senseNumber}</label>
            //         <!-- <button type="button" class="close" aria-label="Close">
            //             <span aria-hidden="true">&times;</span>
            //         </button> -->
            //     </li>`
            // );
        }
    });
    


    $("#deleteSense").click(function(e) {
        e.preventDefault();
        // Can have 0 Sense HATs but no less
        if (senseNumber > 0){
            senseNumber--;
            $('#senseList li:last').remove();
        }
    });



    $(document).on('click','#dialogSubmit',function(e) {
        e.preventDefault();
        var queryString = $('#sensorForm').serialize();
        var query = queryString.split("&");

        $.post('livestream_config', {livestream_config: queryString}, function(result) {
            console.log("Result:");
            console.log(result);
        });
        
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
        } 
        else {
            // No cameras active, hide videos and selectors
            $("#videoDiv").hide();
            $("#videoRow").hide();
        }
    

        let senseData = new Map()
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



            senseData.set("numSense", senseNumber);
            for (var i=0; i<=query.length-1; i+=2){
                if (query[i].substring(0,5) == "sense"){
                    // console.log(query[i].split("="));
                    senseData.set(query[i].split("=")[0], query[i].split("=")[1]);
                }
            }


    
        } 
        else {
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
    
        } 
        else {
            $("#audioRow").hide();
            $("#audioDiv").hide();
        }
    
        // Close the dialog box
        $('#dialog').dialog('close');



        // Create all normal live javascript now that all elements are correct
        live(cameraNumber, senseData, audioNumber);
    });






});










// Global map object to store interval IDs for sense refresh so they can be stopped
let senseIntervals = new Map();

// Code to handle sense streams -- should work with more than 2 sense streams, unable to test
function generate_sense_handler( k, ip ) {    

    // console.log(k)          // The Sense Stream Number
    // console.log(ip)  // The IP Address of the Sense Stream, as a string




    return function() {
        $(`#sense${k}`).show();
        if ($(`#senseSwitch${k}`).is(':checked')){
            var intervalID = setInterval(function() {

                // $.post(`update_sense${k}`, {status : 'ON'}, function(data){
                //     $(`#roomTemperature${k}`).text(data.roomTemperature);
                //     $(`#airPressure${k}`).text(data.airPressure);
                //     $(`#airHumidity${k}`).text(data.airHumidity);
                //     $(`#atm${k}`).text('Atmosphere ('.concat(data.ip, ')'));

                $.post(`update_sense`, {status : 'ON', ipAddress: ip, streamNumber: k}, function(data){
                    $(`#roomTemperature${k}`).text(data.roomTemperature);
                    $(`#airPressure${k}`).text(data.airPressure);
                    $(`#airHumidity${k}`).text(data.airHumidity);
                    $(`#atm${k}`).text('Atmosphere ('.concat(data.ip, ')'));
                });

            }, 1000)
            senseIntervals.set(k, intervalID);
        }
        else {
            clearInterval(senseIntervals.get(k));

            // Clear form data after 1.2s to prevent async issues
            setTimeout(function () {
                $(`#roomTemperature${k}`).text('--.-');
                $(`#airPressure${k}`).text('--.-');
                $(`#airHumidity${k}`).text('--.-');
            }, 1200);
        }
    }
}

















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

// Global map object to store interval IDs for audio refresh
let audioIntervals = new Map();

// Code to handle audio streams -- only works with one audio for now, all thats needed
function generate_audio_handler( k ) {
    return function() {
        if ($(`#audioSwitch${k}`).is(':checked')){
            var intervalID = setInterval(function() {
                $.post('update_audio', {status : 'ON'}, function(data){
                    $('#decibels').text("Current dB: " + data.decibels);
            });
            }, 1000);
            audioIntervals.set(k, intervalID)
        }
        else {
            clearInterval(audioIntervals.get(k));

            // Clear form data after 1.2s to prevent async issues
            setTimeout(function (){
                $('#decibels').text('Current dB: --.-');
            }, 1200);
        }
    }
}




// Create button handlers after number of each sensor is determined
var live = function(numCams, dataSense, numAudios) {

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
   // Pass the sense stream number and it's IP Address
   for (var i=1; i<=dataSense.get("numSense");i++) {
       $(`#senseSwitch${i}`).on("click", generate_sense_handler(i, dataSense.get("sense".concat(i.toString()))));
   }
}

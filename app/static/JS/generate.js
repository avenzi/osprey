$(document).ready(function () {
    
    $('#myModal').modal('show')

    // Default to 1 of each sensor type
    var senseNumber = 0;
    var audioNumber = 0;

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

            $("#cameraList").append(
                `<li id="cam-${cameraNumber}" class="list-group-item">
                    <div class="row">
                        <div class="col-11">
                            <div class="row">
                                <div class="col-5">
                                <label for="cam-ip-input-${cameraNumber}" id="cam-ip-label-${cameraNumber}">Camera ${cameraNumber} IP: </label>
                                </div>
                                <div class="col-7">
                                <input name="cam-ip-input-${cameraNumber}" value="${cameraIPS[cameraIPidx]}">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-5">
                                <label for="cam-name-input-${cameraNumber}" id="cam-name-label-${cameraNumber}">Camera ${cameraNumber} Name: </label>
                                </div>
                                <div class="col-7">
                                <input name="cam-name-input-${cameraNumber}" value="Camera ${cameraNumber}">
                                </div>
                            </div>
                        </div>
                        <div class="col-1">
                            <button type="button" id="cam-delete-${cameraNumber}" class="close deleteCam" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                    </div>
                </li>`
            );
        }
    });

    $(document).on('click', '.close.deleteCam', function(e) {
        e.preventDefault();

        // The number of the cam that was clicked on
        var camClicked = e.currentTarget.id.split("-")[2]

        // Remove the Cam
        var camToRemove = "#cam-".concat(camClicked).concat(".list-group-item");
        $(camToRemove).remove();

        cameraNumber--;

        // The total number of cams after removal
        var numCams = document.getElementsByClassName("close deleteCam").length;

        
        for (let i =Number(camClicked)+1; i <= numCams +1; i++){
            var camLiTag = document.getElementById("cam-".concat(i));
            camLiTag.setAttribute("id", "cam-".concat((i-1).toString()));


            var ipLabelTag = document.getElementById("cam-ip-label-".concat(i));
            ipLabelTag.setAttribute("for", "cam-ip-input-".concat((i-1).toString()));
            ipLabelTag.setAttribute("id", "cam-ip-label-".concat((i-1).toString()));
            ipLabelTag.textContent = "Camera ".concat((i-1).toString()).concat(" IP:");

            var ipInputTag = document.getElementsByName("cam-ip-input-".concat(i))[0];
            ipInputTag.setAttribute("name", "cam-ip-input-".concat((i-1).toString()));


            var nameLabelTag = document.getElementById("cam-name-label-".concat(i));
            nameLabelTag.setAttribute("for", "cam-name-input-".concat((i-1).toString()));
            nameLabelTag.setAttribute("id", "cam-name-label-".concat((i-1).toString()));
            nameLabelTag.textContent = "Camera ".concat((i-1).toString()).concat(" Name:");
            
            var nameInputTag = document.getElementsByName("cam-name-input-".concat(i))[0];
            nameInputTag.setAttribute("name", "cam-name-input-".concat((i-1).toString()));
            // If value is the default and has not been customized, change it
            if (nameInputTag.getAttribute("value") == "Camera ".concat((i).toString())){
                nameInputTag.setAttribute("value", "Camera ".concat((i-1).toString()));
            }
            

            var deleteButtonTag = document.getElementById("cam-delete-".concat(i))
            deleteButtonTag.setAttribute("id", "cam-delete-".concat((i-1).toString()));
        }
    });



    $("#addAudio").click(function(e) {
        e.preventDefault();

        // Maximum audio
        if (audioNumber < maxAudio) {
            audioNumber++;

            $("#audioList").append(
                `<li id="mic-${audioNumber}" class="list-group-item">
                    <div class="row">
                        <div class="col-11">
                            <div class="row">
                                <div class="col-5">
                                    <label for="mic-ip-input-${audioNumber}" id="mic-ip-label-${audioNumber}">Microphone ${audioNumber} IP: </label>
                                </div>
                                <div class="col-7">
                                    <input name="mic-ip-input-${audioNumber}" value="">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-5">
                                    <label for="mic-name-input-${audioNumber}" id="mic-name-label-${audioNumber}">Microphone ${audioNumber} Name: </label>
                                </div>
                                <div class="col-7">
                                    <input name="mic-name-input-${audioNumber}" value="Microphone ${audioNumber}">
                                </div>
                            </div>
                        </div>
                        <div class="col-1">
                            <button type="button" id="mic-delete-${audioNumber}" class="close deleteMic" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                    </div>
                </li>`
            );
        }
    });


    $(document).on('click', '.close.deleteMic', function(e) {
        e.preventDefault();

        // The number of the mic that was clicked on
        var micClicked = e.currentTarget.id.split("-")[2]

        // Remove the mic
        var micToRemove = "#mic-".concat(micClicked).concat(".list-group-item");
        $(micToRemove).remove();

        audioNumber--;

        // The total number of mics after removal
        var numMics = document.getElementsByClassName("close deleteMic").length;

        
        for (let i =Number(micClicked)+1; i <= numMics +1; i++){
            var micLiTag = document.getElementById("mic-".concat(i));
            micLiTag.setAttribute("id", "mic-".concat((i-1).toString()));


            var ipLabelTag = document.getElementById("mic-ip-label-".concat(i));
            ipLabelTag.setAttribute("for", "mic-ip-input-".concat((i-1).toString()));
            ipLabelTag.setAttribute("id", "mic-ip-label-".concat((i-1).toString()));
            ipLabelTag.textContent = "Microphone ".concat((i-1).toString()).concat(" IP:");

            var ipInputTag = document.getElementsByName("mic-ip-input-".concat(i))[0];
            ipInputTag.setAttribute("name", "mic-ip-input-".concat((i-1).toString()));


            var nameLabelTag = document.getElementById("mic-name-label-".concat(i));
            nameLabelTag.setAttribute("for", "mic-name-input-".concat((i-1).toString()));
            nameLabelTag.setAttribute("id", "mic-name-label-".concat((i-1).toString()));
            nameLabelTag.textContent = "Microphone ".concat((i-1).toString()).concat(" Name:");
            
            var nameInputTag = document.getElementsByName("mic-name-input-".concat(i))[0];
            nameInputTag.setAttribute("name", "mic-name-input-".concat((i-1).toString()));
            // If value is the default and has not been customized, change it
            if (nameInputTag.getAttribute("value") == "Microphone ".concat((i).toString())){
                nameInputTag.setAttribute("value", "Microphone ".concat((i-1).toString()));
            }
            

            var deleteButtonTag = document.getElementById("mic-delete-".concat(i))
            deleteButtonTag.setAttribute("id", "mic-delete-".concat((i-1).toString()));
        }
    });


    $("#addSense").click(function(e) {
        e.preventDefault();
    
        // Maximum Sense HATs
        if (senseNumber < maxSense) {
            senseNumber++;

            $("#senseList").append(                
                `<li id="sen-${senseNumber}" class="list-group-item">
                <div class="row">
                    <div class="col-11">
                        <div class="row">
                            <div class="col-5">
                                <label for="sen-ip-input-${senseNumber}" id="sen-ip-label-${senseNumber}">Sense HAT ${senseNumber} IP: </label>
                            </div>
                            <div class="col-7">
                                <input name="sen-ip-input-${senseNumber}" value="">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-5">
                                <label for="sen-name-input-${senseNumber}" id="sen-name-label-${senseNumber}">Sense HAT ${senseNumber} Name: </label>
                            </div>
                            <div class="col-7">
                                <input name="sen-name-input-${senseNumber}" value="Sense HAT ${senseNumber}">
                            </div>
                        </div>
                    </div>
                    <div class="col-1">
                        <button type="button" id="sen-delete-${senseNumber}" class="close deleteSen" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                </div>
            </li>`
            );
        }
    });
    


    $(document).on('click', '.close.deleteSen', function(e) {
        e.preventDefault();

        // The number of the sen that was clicked on
        var senClicked = e.currentTarget.id.split("-")[2]

        // Remove the sen
        var senToRemove = "#sen-".concat(senClicked).concat(".list-group-item");
        $(senToRemove).remove();

        senseNumber--;

        // The total number of sens after removal
        var numSens = document.getElementsByClassName("close deleteSen").length;

        
        for (let i =Number(senClicked)+1; i <= numSens +1; i++){
            var senLiTag = document.getElementById("sen-".concat(i));
            senLiTag.setAttribute("id", "sen-".concat((i-1).toString()));


            var ipLabelTag = document.getElementById("sen-ip-label-".concat(i));
            ipLabelTag.setAttribute("for", "sen-ip-input-".concat((i-1).toString()));
            ipLabelTag.setAttribute("id", "sen-ip-label-".concat((i-1).toString()));
            ipLabelTag.textContent = "Sense HAT ".concat((i-1).toString()).concat(" IP:");

            var ipInputTag = document.getElementsByName("sen-ip-input-".concat(i))[0];
            ipInputTag.setAttribute("name", "sen-ip-input-".concat((i-1).toString()));


            var nameLabelTag = document.getElementById("sen-name-label-".concat(i));
            nameLabelTag.setAttribute("for", "sen-name-input-".concat((i-1).toString()));
            nameLabelTag.setAttribute("id", "sen-name-label-".concat((i-1).toString()));
            nameLabelTag.textContent = "Sense HAT ".concat((i-1).toString()).concat(" Name:");
            
            var nameInputTag = document.getElementsByName("sen-name-input-".concat(i))[0];
            nameInputTag.setAttribute("name", "sen-name-input-".concat((i-1).toString()));
            // If value is the default and has not been customized, change it
            if (nameInputTag.getAttribute("value") == "Sense HAT ".concat((i).toString())){
                nameInputTag.setAttribute("value", "Sense HAT ".concat((i-1).toString()));
            }
            

            var deleteButtonTag = document.getElementById("sen-delete-".concat(i))
            deleteButtonTag.setAttribute("id", "sen-delete-".concat((i-1).toString()));
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
                if (query[i].substring(0,12) == "sen-ip-input"){
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
        // $('#dialog').dialog('close');

        $('#myModal').modal('hide')




        // Create all normal live javascript now that all elements are correct
        live(cameraNumber, senseData, audioNumber);
    });






});










// Global map object to store interval IDs for sense refresh so they can be stopped
let senseIntervals = new Map();

// Code to handle sense streams -- should work with more than 2 sense streams, unable to test
function generate_sense_handler( k, ip ) {    

    console.log(k)          // The Sense Stream Number
    console.log(ip)  // The IP Address of the Sense Stream, as a string




    return function() {
        $(`#sense${k}`).show();
        if ($(`#senseSwitch${k}`).is(':checked')){
            var intervalID = setInterval(function() {
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
       $(`#senseSwitch${i}`).on("click", generate_sense_handler(i, dataSense.get("sen-ip-input-".concat(i.toString()))));
   }
}

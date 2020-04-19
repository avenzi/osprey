$(document).ready(function() {
    
    // Display sensor modal once the DOM is ready for JS to execute
    $("#sensorModal").modal("show");

    // Defining default number of sensors for each sensor type
    var senNumber = 0;
    var micNumber = 0;
    var camNumber = 0;

    // Defining max number of sensors for each sensor type
    var maxCams = 10;
    var maxSens = 10;
    var maxMics = 10;

    /* Adds a camera to the sensorForm */
    $("#addCam").click(function(e) {
        e.preventDefault();

        if (camNumber < maxCams) {
            camNumber++;

            // Adding the camera
            $("#camList").append(
                `<li id="cam-${camNumber}" class="list-group-item">
                    <div class="row">
                        <div class="col-11">
                            <div class="row">
                                <div class="col-5">
                                <label for="cam-ip-input-${camNumber}" id="cam-ip-label-${camNumber}">Camera ${camNumber} IP: </label>
                                </div>
                                <div class="col-7">
                                <input name="cam-ip-input-${camNumber}" value="">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-5">
                                <label for="cam-name-input-${camNumber}" id="cam-name-label-${camNumber}">Camera ${camNumber} Name: </label>
                                </div>
                                <div class="col-7">
                                <input name="cam-name-input-${camNumber}" value="Camera ${camNumber}">
                                </div>
                            </div>
                        </div>
                        <div class="col-1">
                            <button type="button" id="cam-delete-${camNumber}" class="close deleteCam" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                    </div>
                </li>`
            );
        }
    });

    /* Deletes a camera from the sensorForm */
    $(document).on("click", ".close.deleteCam", function(e) {
        e.preventDefault();

        // Number of the camera whose delete button was clicked
        var camRemoveNum = e.currentTarget.id.split("-")[2];

        // Removing the camera
        var camRemove = `#cam-${camRemoveNum}.list-group-item`;
        $(camRemove).remove();

        camNumber--;
        
        // Adjusting the HTML attributes and text content for other cameras to account for the removed camera
        for (var i = Number(camRemoveNum) + 1; i <= camNumber + 1; i++) {

            // List group item attributes
            var camLiTag = document.getElementById(`cam-${i}`);
            camLiTag.setAttribute("id", `cam-${i-1}`);

            // IP label attributes and text content
            var ipLabelTag = document.getElementById(`cam-ip-label-${i}`);
            ipLabelTag.setAttribute("for", `cam-ip-input-${i-1}`);
            ipLabelTag.setAttribute("id", `cam-ip-label-${i-1}`);
            ipLabelTag.textContent = `Camera ${i-1} IP:`;

            // IP input attributes (value is never changed)
            var ipInputTag = document.getElementsByName(`cam-ip-input-${i}`)[0];
            ipInputTag.setAttribute("name", `cam-ip-input-${i-1}`);

            // Name label attributes and text content
            var nameLabelTag = document.getElementById(`cam-name-label-${i}`);
            nameLabelTag.setAttribute("for", `cam-name-input-${i-1}`);
            nameLabelTag.setAttribute("id", `cam-name-label-${i-1}`);
            nameLabelTag.textContent = `Camera ${i-1} Name:`;
            
            // Name input attributes
            var nameInputTag = document.getElementsByName(`cam-name-input-${i}`)[0];
            nameInputTag.setAttribute("name", `cam-name-input-${i-1}`);

            // If value is the default and has not been customized, change it
            if (nameInputTag.getAttribute("value") == `Camera ${i}`){
                nameInputTag.setAttribute("value", `Camera ${i-1}`);
            }
            
            // Delete button attributes
            var deleteButtonTag = document.getElementById(`cam-delete-${i}`);
            deleteButtonTag.setAttribute("id", `cam-delete-${i-1}`);
        }
    });

    /* Adds a microphone to the sensorForm */
    $("#addMic").click(function(e) {
        e.preventDefault();

        if (micNumber < maxMics) {
            micNumber++;

            // Adding the microphone
            $("#micList").append(
                `<li id="mic-${micNumber}" class="list-group-item">
                    <div class="row">
                        <div class="col-11">
                            <div class="row">
                                <div class="col-5">
                                    <label for="mic-ip-input-${micNumber}" id="mic-ip-label-${micNumber}">Microphone ${micNumber} IP: </label>
                                </div>
                                <div class="col-7">
                                    <input name="mic-ip-input-${micNumber}" value="">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-5">
                                    <label for="mic-name-input-${micNumber}" id="mic-name-label-${micNumber}">Microphone ${micNumber} Name: </label>
                                </div>
                                <div class="col-7">
                                    <input name="mic-name-input-${micNumber}" value="Microphone ${micNumber}">
                                </div>
                            </div>
                        </div>
                        <div class="col-1">
                            <button type="button" id="mic-delete-${micNumber}" class="close deleteMic" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                    </div>
                </li>`
            );
        }
    });

    /* Deletes a microphone from the sensorForm */
    $(document).on("click", ".close.deleteMic", function(e) {
        e.preventDefault();

        // Number of the microphone whose delete button was clicked
        var micRemoveNum = e.currentTarget.id.split("-")[2];

        // Removing the microphone
        var micRemove = `#mic-${micRemoveNum}.list-group-item`;
        $(micRemove).remove();

        micNumber--;
        
        // Adjusting the HTML attributes and text content for other microphones to account for the removed microphone
        for (var i = Number(micRemoveNum) + 1; i <= micNumber + 1; i++) {

            // List group item attributes
            var micLiTag = document.getElementById(`mic-${i}`);
            micLiTag.setAttribute("id", `mic-${i-1}`);

            // IP label attributes and text content
            var ipLabelTag = document.getElementById(`mic-ip-label-${i}`);
            ipLabelTag.setAttribute("for", `mic-ip-input-${i-1}`);
            ipLabelTag.setAttribute("id", `mic-ip-label-${i-1}`);
            ipLabelTag.textContent = `Microphone ${i-1} IP:`;

            // IP input attributes (value is never changed)
            var ipInputTag = document.getElementsByName(`mic-ip-input-${i}`)[0];
            ipInputTag.setAttribute("name", `mic-ip-input-${i-1}`);

            // Name label attributes and text content
            var nameLabelTag = document.getElementById(`mic-name-label-${i}`);
            nameLabelTag.setAttribute("for", `mic-name-input-${i-1}`);
            nameLabelTag.setAttribute("id", `mic-name-label-${i-1}`);
            nameLabelTag.textContent = `Microphone ${i-1} Name:`;
            
            // Name input attributes
            var nameInputTag = document.getElementsByName(`mic-name-input-${i}`)[0];
            nameInputTag.setAttribute("name", `mic-name-input-${i-1}`);

            // If value is the default and has not been customized, change it
            if (nameInputTag.getAttribute("value") == `Microphone ${i}`){
                nameInputTag.setAttribute("value", `Microphone ${i-1}`);
            }
            
            // Delete button attributes
            var deleteButtonTag = document.getElementById(`mic-delete-${i}`);
            deleteButtonTag.setAttribute("id", `mic-delete-${i-1}`);
        }
    });

    /* Adds a Sense HAT to the sensorForm */
    $("#addSen").click(function(e) {
        e.preventDefault();
    
        if (senNumber < maxSens) {
            senNumber++;

            // Adding the Sense HAT
            $("#senList").append(                
                `<li id="sen-${senNumber}" class="list-group-item">
                    <div class="row">
                        <div class="col-11">
                            <div class="row">
                                <div class="col-5">
                                    <label for="sen-ip-input-${senNumber}" id="sen-ip-label-${senNumber}">Sense HAT ${senNumber} IP: </label>
                                </div>
                                <div class="col-7">
                                    <input name="sen-ip-input-${senNumber}" value="">
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-5">
                                    <label for="sen-name-input-${senNumber}" id="sen-name-label-${senNumber}">Sense HAT ${senNumber} Name: </label>
                                </div>
                                <div class="col-7">
                                    <input name="sen-name-input-${senNumber}" value="Sense HAT ${senNumber}">
                                </div>
                            </div>
                        </div>
                        <div class="col-1">
                            <button type="button" id="sen-delete-${senNumber}" class="close deleteSen" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                    </div>
                </li>`
            );
        }
    });

    /* Deletes a Sense HAT from the sensorForm */
    $(document).on("click", ".close.deleteSen", function(e) {
        e.preventDefault();

        // Number of the Sense HAT whose delete button was clicked
        var senRemoveNum = e.currentTarget.id.split("-")[2];

        // Removing the Sense HAT
        var senRemove = `#sen-${senRemoveNum}.list-group-item`;
        $(senRemove).remove();

        senNumber--;
        
        // Adjusting the HTML attributes and text content for other Sense HATs to account for the removed Sense HAT
        for (var i = Number(senRemoveNum) + 1; i <= senNumber + 1; i++) {

            // List group item attributes
            var senLiTag = document.getElementById(`sen-${i}`);
            senLiTag.setAttribute("id", `sen-${i-1}`);

            // IP label attributes and text content
            var ipLabelTag = document.getElementById(`sen-ip-label-${i}`);
            ipLabelTag.setAttribute("for", `sen-ip-input-${i-1}`);
            ipLabelTag.setAttribute("id", `sen-ip-label-${i-1}`);
            ipLabelTag.textContent = `Sense HAT ${i-1} IP:`;

            // IP input attributes (value is never changed)
            var ipInputTag = document.getElementsByName(`sen-ip-input-${i}`)[0];
            ipInputTag.setAttribute("name", `sen-ip-input-${i-1}`);

            // Name label attributes and text content
            var nameLabelTag = document.getElementById(`sen-name-label-${i}`);
            nameLabelTag.setAttribute("for", `sen-name-input-${i-1}`);
            nameLabelTag.setAttribute("id", `sen-name-label-${i-1}`);
            nameLabelTag.textContent = `Sense HAT ${i-1} Name:`;
            
            // Name input attributes
            var nameInputTag = document.getElementsByName(`sen-name-input-${i}`)[0];
            nameInputTag.setAttribute("name", `sen-name-input-${i-1}`);

            // If value is the default and has not been customized, change it
            if (nameInputTag.getAttribute("value") == `Sense HAT ${i}`){
                nameInputTag.setAttribute("value", `Sense HAT ${i-1}`);
            }
            
            // Delete button attributes
            var deleteButtonTag = document.getElementById(`sen-delete-${i}`);
            deleteButtonTag.setAttribute("id", `sen-delete-${i-1}`);
        }
    });

    /* Configures livestreaming, creates sensor cards and the buttons associated, and starts the timer */
    $("#sensorModalSubmit").click(function(e) {
        e.preventDefault();
        
        // Collecting form data submitted from sensorForm into a string and a list
        var queryString = $("#sensorForm").serialize();
        var queryList = queryString.split("&");

        // A map containing camera data submitted from sensorForm
        var camData = new Map();

        // A map containing Sense HAT data submitted from sensorForm
        var senData = new Map();

        // A map containing microphone data submitted from sensorForm
        var micData = new Map();

        // Sending form data to livestream_config in routes.py
        $.post("livestream_config", {livestream_config: queryString});

        if (camNumber > 0) {

            // Adding IP addresses and names of cameras to the camData map to be used when creating camera cards
            for (var i = 0; i <= queryList.length - 1; i++) {
                if (queryList[i].substring(0,12) == "cam-ip-input") {
                    ipInputName = queryList[i].split("=")[0];
                    ipInputValue = queryList[i].split("=")[1];
                    camData.set(ipInputName, ipInputValue);
                }
                else if (queryList[i].substring(0,14) == "cam-name-input") {
                    nameInputName = queryList[i].split("=")[0];
                    nameInputValue = queryList[i].split("=")[1];
                    camData.set(nameInputName, nameInputValue);
                }
            }

            for (var i = 1; i <= camNumber; i++) {
                var checkedStatus = "";
                var ip = camData.get(`cam-ip-input-${i}`);
                var name = camData.get(`cam-name-input-${i}`);

                // The first camera's radio button is checked by default
                if (i == 1) {
                    checkedStatus = " checked";
                }

                // Adding a camera radio button
                $("#camRow").append(
                    `<div class="col">
                        <div class="radio d-inline">
                            <label>
                                <input type="radio" name="cam" id="cam${i}" autocomplete="off"${checkedStatus}> ${decodeURI(name)}
                            </label>
                        </div>
                    </div>`
                );

                // Creating a camera card to display a camera stream
                $("#camDiv").append(
                    `<div class="card w-100 mb-1" id="stream${i}">
                        <div class="card-header p-0 text-center">
                            ${decodeURI(name)}
                        </div>
                        <div class=" card-body embed-responsive embed-responsive-16by9">
                            <iframe class="embed-responsive-item" src="http://${decodeURI(ip)}:8000/stream.mjpg" allowfullscreen></iframe>
                        </div>
                    </div>`
                    
                );
            }
        } 

        if (senNumber > 0) {

            // Adding number of Sense HATs to the senData map
            senData.set("numSense", senNumber);

            // Adding IP addresses and names of Sense HATs to the senData map to be used when creating Sense HAT cards
            for (var i = 0; i <= queryList.length - 1; i++) {
                if (queryList[i].substring(0,12) == "sen-ip-input") {
                    ipInputName = queryList[i].split("=")[0];
                    ipInputValue = queryList[i].split("=")[1];
                    senData.set(ipInputName, ipInputValue);
                }
                else if (queryList[i].substring(0,14) == "sen-name-input") {
                    nameInputName = queryList[i].split("=")[0];
                    nameInputValue = queryList[i].split("=")[1];
                    senData.set(nameInputName, nameInputValue);
                }
            }

            for (var i = 1; i <= senNumber; i++) {
                var name = senData.get(`sen-name-input-${i}`);

                // Adding a Sense HAT switch
                $("#senRow").append(
                    `<div class="col">
                        <div class="custom-control custom-switch d-inline">
                            <input type="checkbox" class="custom-control-input" id="senseSwitch${i}">
                            <label class="custom-control-label" for="senseSwitch${i}">${decodeURI(name)}</label>
                        </div>
                    </div>`
                );

                // Creating a Sense HAT card to display Sense HAT data
                $("#senMic").append(
                    `<div class="row justify-content-center mb-1" id="sense${i}">
                        <div class="card w-100">
                            <div class="card-header p-0 text-center">
                                ${decodeURI(name)}
                            </div>
                            <div class="card-body p-1">
                                <div class="row temp-spacing">
                                    <div class="col-8">
                                        Temperature (&#8457):
                                    </div>
                                    <div class="col-4 text-right" id="roomTemperature${i}">
                                        --.-
                                    </div>
                                </div>
                                <div class="row temp-spacing">
                                    <div class="col-8">
                                        Air Pressure (millibars):
                                    </div>
                                    <div class="col-4 text-right" id="airPressure${i}">
                                        --.-
                                    </div>
                                </div>
                                <div class="row temp-spacing">
                                    <div class="col-8">
                                        Air Humidity (%):
                                    </div>
                                    <div class="col-4 text-right" id="airHumidity${i}">
                                        --.-
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>`
                );
            }
        } 

        if (micNumber > 0) {

            // Adding IP addresses and names of microphones to the micData map to be used when creating microphone cards
            for (var i = 0; i <= queryList.length - 1; i++) {
                if (queryList[i].substring(0,12) == "mic-ip-input") {
                    ipInputName = queryList[i].split("=")[0];
                    ipInputValue = queryList[i].split("=")[1];
                    micData.set(ipInputName, ipInputValue);
                }
                else if (queryList[i].substring(0,14) == "mic-name-input") {
                    nameInputName = queryList[i].split("=")[0];
                    nameInputValue = queryList[i].split("=")[1];
                    micData.set(nameInputName, nameInputValue);
                }
            }

            for (var i = 1; i <= micNumber; i++) {
                var name = micData.get(`mic-name-input-${i}`);

                // Creating a microphone card to display microphone data
                $("#senMic").append(
                    `<div class="row">
                        <div class="card w-100" id="micDiv">
                            <div class="card-header p-0 text-center">
                                ${decodeURI(name)}
                            </div>
                            <div class="card-body p-1">
                                <div class="row">
                                    <div class="col">
                                        <audio id="audio" class="audio-player" controls>
                                            Your browser doesn't support HTML audio element.
                                        </audio>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>`
                );
            }
        } 

        // Creating onclick handlers for cameras and Sense HATs and showing a camera stream by default if there is one available
        createHandlers(camNumber, senData);

        // Starting the timer
        var timer = document.getElementById('timer');
        var watch = new ElapsedTime(timer);
        watch.start();

        // Hide sensor modal
        $("#sensorModal").modal("hide");
    });
});

// Global map object to store interval IDs for Sense HAT refresh
var senseIntervals = new Map();

/**
 * Handles updating of Sense HAT streams. Shows Sense HAT stream whose button was clicked
 * @param {number} k The number of the Sense HAT whose button was clicked
 * @param {string} ip The IP address of the Sense HAT whose button was clicked
 * @return {undefined}
 */
function generateSenseHatHandler(k, ip) {    
    return function() {
        if ($(`#senseSwitch${k}`).is(":checked")){
            var intervalID = setInterval(function() {

                // Querying the database for Sense HAT data associated with the IP address
                $.post(`update_sense`, {ip: ip, streamNumber: k}, function(data){
                    $(`#roomTemperature${k}`).text(data.roomTemperature);
                    $(`#airPressure${k}`).text(data.airPressure);
                    $(`#airHumidity${k}`).text(data.airHumidity);
                });

            }, 1000)
            senseIntervals.set(k, intervalID);
        }
        else {
            clearInterval(senseIntervals.get(k));

            setTimeout(function () {
                $(`#roomTemperature${k}`).text("--.-");
                $(`#airPressure${k}`).text("--.-");
                $(`#airHumidity${k}`).text("--.-");
            }, 1200);
        }
    };    
}

/**
 * Handles switching between camera streams. Shows the camera stream whose button was clicked and hides the rest of the camera streams
 * @param {number} k The number of the camera whose button was clicked
 * @param {number} numCams The total number of cameras
 * @return {undefined}
 */
function generateCameraHandler(k, numCams) {
    return function() { 
        for (var j = 1; j <= numCams; j++) {
            if (j == k) {
                $(`#stream${j}`).show();
            } 
            else {
                $(`#stream${j}`).hide();
            }
        }
    };
}

/**
 * Creates onclick handlers for cameras and Sense HATs. Shows a camera stream by default if there is one available
 * @param {number} numCams The total number of cameras
 * @param {map} senData A map containing Sense HAT data submitted from sensorForm
 * @return {undefined}
 */
function createHandlers(numCams, senData) {
    
    // If there are camera streams, show the first camera stream and hide any others
    for (var i = 1; i <= numCams; i++) {
        if (i == 1) {
            $(`#stream1${i}`).show();
        } 
        else {
            $(`#stream${i}`).hide();
        }

        // Generate onclick handlers for each camera stream button
        $(`#cam${i}`).on("click", generateCameraHandler(i, numCams));
    }

    // Generate onclick handlers for each Sense HAT button
    for (var i = 1; i <= senData.get("numSense"); i++) {
        $(`#senseSwitch${i}`).on("click", generateSenseHatHandler(i, senData.get(`sen-ip-input-${i}`)));
    }
}
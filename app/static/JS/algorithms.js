/**
 * @fileoverview This file is used to handle all events that occur within the algorithmModal
 */

$(document).ready(function () {

    /* Uploads a file and displays the updated uploads menu within the algorithmModal */
    $("#uploadFileSubmit").click(function(e) {

        // Getting the file to be uploaded
        formData = new FormData();
        for (file of document.getElementById("uploadFileInput").files) {
            formData.append("file", file);
        }

        // Preventing TypeError : Illegal Invocation from jQuery trying to transform the FormData object into a string
        $.ajaxSetup({
            processData: false,
            contentType: false
        });

        // Sending the file to the back end to be uploaded
        $.post("algorithm_upload", formData, function(data){

            // Setting variables back to default to allow for JSON parsing
            $.ajaxSetup({
                processData: true,
                contentType: "application/x-www-form-urlencoded; charset=UTF-8"
            });
            
            $("#algorithmModalContent").html(data);
        });
        e.stopImmediatePropagation();
    });

    /* Runs an uploaded algorithm and indicates that the algorithm is running within the algorithmModal */
    $(".availableAlgorithmsRunButton").click(function(e) {
        $.post("algorithm_handler", {"button" : "run", "filename" : this.id}, function(data){
            $("#algorithmModalContent").html(data);
        });
        e.stopImmediatePropagation();
    });

    /* Takes a user to the view section of an uploaded algorithm within the algorithmModal */   
    $(".availableAlgorithmsViewButton").click(function(e) {
        $.post("algorithm_handler", {"button" : "view", "filename" : this.id}, function(data) {
            $("#algorithmModalContent").html(data);
        });
        e.stopImmediatePropagation();
    });
    
    /* Takes a user from the view section to the uploads menu within the algorithmModal */
    $("#algorithmModalBackButton").click( function(e) {
        $.get("algorithm_upload", function(data){
            $("#algorithmModalContent").html(data);
        });
    });
    
    /* Takes a user to a prompt for the deletion of an uploaded algorithm within the algorithmModal */
    $(".availableAlgorithmsDeleteButton").click(function(e) {

        // Setting the filename to be deleted
        filename = this.id;

        $.post("algorithm_handler", {"button" : "delete", "filename" : filename}, function(data) {
            $("#algorithmModalContent").html(data);
        });
        e.stopImmediatePropagation();
    });

    /* Cancels the deletion of an uploaded algorithm and takes a user back to the uploads menu within the algorithmModal */
    $(".availableAlgorithmsDeleteCancelButton").click(function(e) {
        $.get("algorithm_upload", function(data){
            $("#algorithmModalContent").html(data);
        });
        e.stopImmediatePropagation();
    });

    /* Confirms the deletion an uploaded algorithm and displays the updated uploads menu within the algorithmModal */
    $(".availableAlgorithmsDeleteConfirmButton").click(function(e) {
        $.post("algorithm_handler", {"button" : "delete_confirm", "filename" : filename}, function(data) {
            $("#algorithmModalContent").html(data);
        });
        e.stopImmediatePropagation();
    });
});

// The name of a file to be deleted
var filename;
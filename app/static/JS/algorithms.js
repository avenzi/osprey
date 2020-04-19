$(document).ready(function () {

    // Back button to take you to the uploads menu within the modal, from the view section
    $('#algorithmModalBackButton').click( function(e) {
        $.get('algorithm_upload', function(data){
            $('#algorithmModalContent').html(data);
        });
    });

    // Posts a file to be uploaded and displays the updated uploads menu within the modal
    $('#uploadFileSubmit').click(function(e) {
        formData = new FormData();
        for (file of document.getElementById('uploadFileInput').files) {
            formData.append('file', file);
        }
        $.ajaxSetup({
            // Preventing TypeError : Illegal Invocation from jQuery trying to transform the FormData object into a string
            processData: false,
            contentType: false
        });
        $.post('algorithm_upload', formData, function(data){
            $.ajaxSetup({
                // Setting variables back to default to allow for JSON parsing
                processData: true,
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8'
            });

            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });
    
    // Select button for an uploaded algorithm
    $('.availableAlgorithmsRunButton').click(function(e) {
        $.post('algorithm_handler', {'button' : 'select', 'filename' : this.id}, function(data){
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });

    // View button for an uploaded algorithm    
    $('.availableAlgorithmsViewButton').click(function(e) {
        $.post('algorithm_handler', {'button' : 'view', 'filename' : this.id}, function(data) {
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });

    // Delete button for an uploaded algorithm 
    $('.availableAlgorithmsDeleteButton').click(function(e) {
        filename = this.id;
        $.post('algorithm_handler', {'button' : 'delete', 'filename' : this.id}, function(data) {
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });

    // Delete confirm button for an uploaded algorithm 
    $('.availableAlgorithmsDeleteConfirmButton').click(function(e) {
        $.post('algorithm_handler', {'button' : 'delete_confirm', 'filename' : filename}, function(data) {
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });

    // Delete cancel button for an uploaded algorithm 
    $('.availableAlgorithmsDeleteCancelButton').click(function(e) {
        $.get('algorithm_upload', function(data){
            $('#algorithmModalContent').html(data);
        });
        e.stopImmediatePropagation();
    });

});
// The name of a file to be deleted
var filename;
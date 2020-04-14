document.addEventListener("DOMContentLoaded", function() {
    // Create New Session button handler
    document.getElementById("new-session").addEventListener("click", function() {
        // Display the overlays
        var overlay = document.getElementById('overlay');
        overlay.style.display = "unset";
    });

    document.getElementById("overlay").addEventListener("click", function() {
        // Hide the overlays
        var overlay = document.getElementById('overlay');
        overlay.style.display = "none";
    });

    document.getElementById("overlay").addEventListener("click", function() {
        // Hide the overlays
        var overlay = document.getElementById('overlay');
        overlay.style.display = "none";
    });

    document.getElementById("new-session-modal").addEventListener("click", function(event) {
        event.stopPropagation();
    });

});

function delete_session(session_id) {
    // TODO: confirm delete modal / pop-up
    $.post(`delete_session/${session_id}`, {}, function(result) {
        $(`#entry${session_id}`).remove();
    });
}
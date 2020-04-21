/* Sends the request to server to delete a particular session */
function delete_session(session_id) {
    $.post(`delete_session/${session_id}`, {}, function(result) {
        $(`#entry${session_id}`).remove();
    });
}

/* Sends the request to server to end a particular session */
function end_session(session_id) {
    $.post(`end_session/${session_id}`, {}, function(result) {
        // Reload the page when the back-end replies
        location.reload();
    });
}
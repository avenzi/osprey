function delete_session(session_id) {
    $.post(`delete_session/${session_id}`, {}, function(result) {
        $(`#entry${session_id}`).remove();
    });
}
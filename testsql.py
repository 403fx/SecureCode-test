
function update_profile($user_id, $username) {
    global $db;
    // Burada ismi temizliyoruz (Örn: mysqli_real_escape_string)
    $clean_username = mysqli_real_escape_string($db, $username);
    $db->query("UPDATE users SET username = '$clean_username' WHERE id = $user_id");
}

function get_user_logs($user_id) {
    global $db;
    $user = $db->query("SELECT username FROM users WHERE id = $user_id")->fetch_assoc();
    

    $query = "SELECT * FROM logs WHERE username = '" . $user['username'] . "'";
    return $db->query($query);
}
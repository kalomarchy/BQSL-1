<?php
// filepath: /workspaces/BQSL/create-user-verify.php
require __DIR__ . '/config.php';
require_captcha();

$registration = $_SESSION['registration'] ?? null;
$decrypted = trim($_POST['decrypted_message'] ?? '');

if (
    !$registration ||
    time() > $registration['expires'] ||
    !hash_equals(
        $registration['challenge_hash'],
        hash('sha256', $decrypted)
    )
) {
    unset($_SESSION['registration']);
    http_response_code(401);
    exit('Invalid or expired GPG challenge.');
}

try {
    $statement = $db->prepare(
        'INSERT INTO users
        (username, email, password_hash, public_key)
        VALUES (?, ?, ?, ?)'
    );

    $statement->execute([
        $registration['username'],
        $registration['email'],
        $registration['password_hash'],
        $registration['public_key'],
    ]);

    unset($_SESSION['registration']);
    header('Location: /login.php');
    exit;
} catch (PDOException) {
    http_response_code(409);
    exit('Username or email is already registered.');
}
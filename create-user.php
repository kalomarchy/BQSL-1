<?php
// filepath: /workspaces/BQSL/create-user.php
require __DIR__ . '/config.php';
require_captcha();

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $email = strtolower(trim($_POST['email'] ?? ''));
    $password = $_POST['password'] ?? '';
    $confirmation = $_POST['confirm_password'] ?? '';
    $publicKey = trim($_POST['public_key'] ?? '');

    if (!$username || !$email || !$password || !$confirmation || !$publicKey) {
        $error = 'All fields are required.';
    } elseif ($password !== $confirmation) {
        $error = 'Passwords do not match.';
    } else {
        try {
            $challenge = bin2hex(random_bytes(32));
            $encryptedMessage = encrypt_gpg_message($publicKey, $challenge);

            $_SESSION['registration'] = [
                'username' => $username,
                'email' => $email,
                'password_hash' => password_hash($password, PASSWORD_DEFAULT),
                'public_key' => $publicKey,
                'challenge_hash' => hash('sha256', $challenge),
                'expires' => time() + 300,
            ];
        } catch (Throwable) {
            $error = 'The GPG public key is invalid.';
        }
    }
}

if (!empty($_SESSION['registration']) && isset($encryptedMessage)) {
    require __DIR__ . '/create-user-verify.php';
    exit;
}

require __DIR__ . '/templates/create_user.php';
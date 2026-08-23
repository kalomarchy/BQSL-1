<?php
// filepath: /workspaces/BQSL/templates/create_user.php
function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Create account | BQSL</title>
    <style>
        :root {
            --black: #000;
            --green: #39ff14;
            --white: #fff;
            --red: #ff7070;
        }

        * { box-sizing: border-box; }

        body {
            min-height: 100vh;
            margin: 0;
            padding: 2rem;
            background: var(--black);
            color: var(--green);
            font: 16px/1.5 Arial, sans-serif;
        }

        main {
            width: min(100%, 620px);
            margin: 2rem auto;
        }

        label {
            display: block;
            margin-top: 1rem;
        }

        input,
        textarea,
        button {
            width: 100%;
            margin-top: .4rem;
            padding: .8rem;
            border: 1px solid var(--green);
            border-radius: 4px;
            font: inherit;
        }

        input,
        textarea {
            background: var(--black);
            color: var(--green);
        }

        textarea {
            min-height: 180px;
            resize: vertical;
            font-family: monospace;
        }

        button {
            margin-top: 1.5rem;
            background: var(--green);
            color: var(--black);
            font-weight: bold;
            cursor: pointer;
        }

        a,
        a:visited {
            color: var(--white);
        }

        a:hover,
        a:focus-visible {
            color: var(--green);
        }

        .error { color: var(--red); }
        .hint { color: var(--green); }
    </style>
</head>
<body>
<main>
    <h1>Create account</h1>

    <?php if ($error !== ''): ?>
        <p class="error" role="alert"><?= e($error) ?></p>
    <?php endif; ?>

    <?php if ($encryptedMessage !== null): ?>
        <h2>Verify your GPG key</h2>
        <p class="hint">
            Copy the encrypted message, decrypt it with GPG on your computer,
            and submit the decrypted text.
        </p>

        <textarea readonly><?= e($encryptedMessage) ?></textarea>

        <form method="post" action="/create-user-verify.php">
            <label for="decrypted_message">Decrypted message</label>
            <input
                id="decrypted_message"
                name="decrypted_message"
                autocomplete="off"
                required
            >
            <button type="submit">Confirm account</button>
        </form>
    <?php else: ?>
        <form method="post" action="/create-user.php">
            <label for="username">Username</label>
            <input
                id="username"
                name="username"
                autocomplete="username"
                required
            >

            <label for="email">Email</label>
            <input
                id="email"
                name="email"
                type="email"
                autocomplete="email"
                required
            >

            <label for="password">Password</label>
            <input
                id="password"
                name="password"
                type="password"
                autocomplete="new-password"
                required
            >

            <label for="confirm_password">Confirm password</label>
            <input
                id="confirm_password"
                name="confirm_password"
                type="password"
                autocomplete="new-password"
                required
            >

            <label for="public_key">GPG public key</label>
            <p class="hint">
                Submit only your public key. Never submit a private key or
                recovery phrase.
            </p>
            <textarea
                id="public_key"
                name="public_key"
                placeholder="-----BEGIN PGP PUBLIC KEY BLOCK-----"
                required
            ></textarea>

            <button type="submit">Continue</button>
        </form>
    <?php endif; ?>

    <p><a href="/login.php">Already have an account? Log in</a></p>
    <p><a href="/index.html">Return home</a></p>
</main>
</body>
</html>
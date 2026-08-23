import hashlib
import hmac
import os
import secrets
import subprocess
import time
import tempfile

from flask import Flask, redirect, render_template_string, request, session, url_for


app = Flask(__name__)
app.secret_key = os.environ.get("BQSL_SECRET_KEY", "change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


PAGE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GPG Message Encryption | EXODUS v1.2.0</title>
    <style>
        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            padding: 2rem;
            background: #000;
            color: #39ff14;
            font: 16px/1.5 Arial, sans-serif;
        }

        main {
            width: min(100%, 760px);
            margin: 2rem auto;
        }

        textarea, input, button {
            width: 100%;
            margin-top: .75rem;
            padding: 1rem;
            border: 1px solid #39ff14;
            border-radius: 4px;
            font: inherit;
        }

        textarea, input {
            background: #000;
            color: #39ff14;
        }

        textarea {
            min-height: 260px;
            resize: vertical;
            font-family: monospace;
        }

        button {
            background: #39ff14;
            color: #000;
            font-weight: bold;
            cursor: pointer;
        }

        .error { color: #ff7070; }
        .success { color: #fff; }
        .hint { color: #baffba; }
    </style>
</head>
<body>
<main>
    <h1>Encrypt a GPG verification message</h1>

    {% if error %}
        <p class="error" role="alert">{{ error }}</p>
    {% endif %}

    {% if verified %}
        <p class="success">The decrypted message was verified successfully.</p>
    {% else %}
        <form method="post" action="{{ url_for('encrypt_page') }}">
            <label for="public_key">Your GPG public key</label>
            <p class="hint">
                Submit only your public key. Never upload your private key.
            </p>
            <textarea
                id="public_key"
                name="public_key"
                placeholder="-----BEGIN PGP PUBLIC KEY BLOCK-----"
                required
            >{{ public_key }}</textarea>

            <button type="submit">Encrypt numeric message</button>
        </form>

        {% if encrypted_message %}
            <h2>Encrypted message</h2>
            <p class="hint">
                Copy this message, decrypt it locally with your private key,
                then enter the resulting numbers below.
            </p>

            <textarea id="encrypted-output" readonly>{{ encrypted_message }}</textarea>

            <button type="button" onclick="copyMessage()">
                Copy encrypted message
            </button>

            <form method="post" action="{{ url_for('verify_message') }}">
                <label for="decrypted_message">
                    Numbers from the decrypted message
                </label>
                <input
                    id="decrypted_message"
                    name="decrypted_message"
                    inputmode="numeric"
                    pattern="[0-9]+"
                    autocomplete="off"
                    required
                >
                <button type="submit">Verify decryption</button>
            </form>
        {% endif %}
    {% endif %}
</main>

<script>
async function copyMessage() {
    const field = document.getElementById("encrypted-output");

    try {
        await navigator.clipboard.writeText(field.value);
    } catch {
        field.select();
        document.execCommand("copy");
    }
}
</script>
</body>
</html>
"""


def encrypt_gpg_message(public_key: str, message: str) -> str:
    """Encrypt message using a temporary keyring containing only public_key."""
    if (
        "-----BEGIN PGP PUBLIC KEY BLOCK-----" not in public_key
        or "-----END PGP PUBLIC KEY BLOCK-----" not in public_key
        or "-----BEGIN PGP PRIVATE KEY BLOCK-----" in public_key
    ):
        raise ValueError("A valid armored public key is required.")

    with tempfile.TemporaryDirectory(prefix="bqsl-gpg-") as home:
        key_file = os.path.join(home, "public-key.asc")

        with open(key_file, "w", encoding="utf-8") as file:
            file.write(public_key + "\n")

        gpg = [
            "gpg",
            "--batch",
            "--yes",
            "--no-options",
            "--homedir",
            home,
        ]

        imported = subprocess.run(
            [*gpg, "--import", key_file],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if imported.returncode != 0:
            raise RuntimeError(imported.stderr.strip())

        listed = subprocess.run(
            [*gpg, "--with-colons", "--list-keys"],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if listed.returncode != 0:
            raise RuntimeError(listed.stderr.strip())

        fingerprint = None

        for line in listed.stdout.splitlines():
            fields = line.split(":")
            if fields[0] == "fpr" and len(fields) > 9:
                fingerprint = fields[9]
                break

        if not fingerprint:
            raise ValueError("No usable public-key fingerprint was found.")

        encrypted = subprocess.run(
            [
                *gpg,
                "--armor",
                "--trust-model",
                "always",
                "--encrypt",
                "--recipient",
                fingerprint,
            ],
            input=message,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if encrypted.returncode != 0:
            raise RuntimeError(encrypted.stderr.strip())

        if not encrypted.stdout.strip():
            raise RuntimeError("GPG returned an empty encrypted message.")

        return encrypted.stdout


@app.route("/", methods=["GET", "POST"])
def encrypt_page():
    error = ""
    encrypted_message = ""
    public_key = ""
    verified = session.pop("gpg_verified", False)

    if request.method == "POST":
        public_key = request.form.get("public_key", "").strip()

        try:
            # Numeric plaintext that the user must recover locally.
            challenge = f"{secrets.randbelow(10**32):032d}"
            encrypted_message = encrypt_gpg_message(public_key, challenge)

            session["gpg_challenge_hash"] = hashlib.sha256(
                challenge.encode("ascii")
            ).hexdigest()
            session["gpg_challenge_expires"] = time.time() + 300

        except (
            OSError,
            ValueError,
            RuntimeError,
            subprocess.SubprocessError,
        ) as exc:
            app.logger.exception("GPG encryption failed")
            error = f"Encryption failed: {exc}"

    return render_template_string(
        PAGE,
        error=error,
        encrypted_message=encrypted_message,
        public_key=public_key,
        verified=verified,
    )


@app.route("/verify-message", methods=["POST"])
def verify_message():
    submitted = request.form.get("decrypted_message", "").strip()
    expected_hash = session.get("gpg_challenge_hash")
    expires = session.get("gpg_challenge_expires", 0)

    if (
        not expected_hash
        or time.time() > expires
        or not submitted.isdigit()
        or not hmac.compare_digest(
            expected_hash,
            hashlib.sha256(submitted.encode("ascii")).hexdigest(),
        )
    ):
        return render_template_string(
            PAGE,
            error="The decrypted number string is invalid or expired.",
            encrypted_message="",
            public_key="",
            verified=False,
        ), 400

    session.pop("gpg_challenge_hash", None)
    session.pop("gpg_challenge_expires", None)
    session["gpg_verified"] = True

    return redirect(url_for("encrypt_page"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
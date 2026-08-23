from flask import (
    Flask, jsonify, request, session, render_template,
    render_template_string, send_file, redirect, url_for
)
import subprocess
import tempfile
from werkzeug.security import check_password_hash, generate_password_hash
import numpy as np
import secrets
import hashlib
import hmac
import os
import sqlite3
import time

app = Flask(__name__)

# Used to protect the Flask session
app.secret_key = os.environ.get(
    "BQSL_SECRET_KEY",
    "development-only-change-this-secret",
)
app.config["DATABASE"] = os.environ.get(
    "BQSL_DATABASE",
    os.path.join(app.root_path, "members.db")
)


def get_db():
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                public_key TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_registrations (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                public_key TEXT NOT NULL,
                challenge_hash TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )


init_db()


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Quantum CAPTCHA</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #111;
            color: white;
            text-align: center;
            padding: 40px;
        }

        .box {
            max-width: 600px;
            margin: auto;
            padding: 30px;
            background: #222;
            border-radius: 15px;
        }

        .wave {
            font-family: monospace;
            font-size: 20px;
            letter-spacing: 3px;
            margin: 25px;
            word-break: break-all;
        }

        input {
            padding: 12px;
            font-size: 18px;
            width: 120px;
        }

        button {
            padding: 12px 25px;
            font-size: 18px;
            cursor: pointer;
        }

        .message {
            margin-top: 20px;
            font-weight: bold;
        }
    </style>
</head>

<body>

<div class="box">

<hi>Quantum CAPTCHA</hi>

<p>
    <a href="{{ url_for('home') }}">Back to BQSL home</a>
</p>

<p>
Find the region containing the greatest probability
density.
</p>

<div class="wave">
{{ wave }}
</div>

<p>
Enter the region number:
</p>

<form method="POST">

    <input
        type="hidden"
        name="csrf_token"
        value="{{ csrf_token }}"
    >

    <input
        type="number"
        name="answer"
        min="1"
        max="16"
        required
    >

    <br><br>

    <button type="submit">
        Verify
    </button>

</form>

<div class="message">
{{ message }}
</div>

</div>

</body>
</html>
"""


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum CAPTCHA</title>
    <style>
        :root { color-scheme: dark; --ink: #07100b; --panel: #101b14; --line: #31583a; --signal: #72ff91; --quiet: #a9cdb0; }
        * { box-sizing: border-box; }
        body { min-height: 100vh; margin: 0; display: grid; place-items: center; padding: 24px; background: radial-gradient(circle at 50% 20%, #193520, var(--ink) 62%); color: var(--signal); font-family: "Courier New", monospace; }
        .box { width: min(760px, 100%); padding: clamp(24px, 6vw, 56px); border: 1px solid var(--line); background: rgba(16, 27, 20, .94); box-shadow: 0 24px 80px rgba(0, 0, 0, .35); }
        a { color: var(--quiet); }
        h1 { margin: 0; font-size: clamp(2rem, 7vw, 4.5rem); line-height: .95; letter-spacing: 0; }
        .eyebrow { margin: 0 0 18px; color: var(--quiet); font-size: .75rem; letter-spacing: .16em; text-transform: uppercase; }
        .prompt { margin: 28px 0 12px; color: #f1fff3; font-family: Georgia, serif; font-size: clamp(1.1rem, 3vw, 1.45rem); }
        .arena { position: relative; height: 150px; margin: 28px 0 12px; border: 1px solid var(--line); background: linear-gradient(180deg, rgba(114, 255, 145, .04), rgba(114, 255, 145, .01)); overflow: hidden; cursor: crosshair; }
        .arena::before { content: ""; position: absolute; top: 50%; left: 4%; right: 4%; border-top: 1px dashed #42734d; }
        .dot { position: absolute; top: 50%; width: 18px; height: 18px; border-radius: 50%; transform: translate(-50%, -50%); }
        .stationary { left: {{ target_position }}%; background: #fff; box-shadow: 0 0 8px #fff, 0 0 24px var(--signal); }
        .moving { left: 4%; background: var(--signal); box-shadow: 0 0 8px var(--signal), 0 0 22px var(--signal); }
        .readout { display: flex; justify-content: space-between; gap: 16px; color: var(--quiet); font-size: .75rem; }
        .message { min-height: 1.5em; margin-top: 24px; color: #f1fff3; font-weight: 700; }
        .back { display: inline-block; margin-top: 28px; }
    </style>
</head>
<body>
    <main class="box">
        <p class="eyebrow">Wavefunction alignment protocol</p>
        <h1>Catch the state.</h1>
        <p class="prompt">Line up the green dot with the stationary white dot. Right-click at the exact moment they meet.</p>
        <form id="captcha-form" method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <input type="hidden" name="click_x" id="click-x">
            <input type="hidden" name="click_elapsed" id="click-elapsed">
            <div class="arena" id="arena" aria-label="Moving quantum dot CAPTCHA">
                <span class="dot stationary" aria-hidden="true"></span>
                <span class="dot moving" id="moving-dot" aria-hidden="true"></span>
            </div>
        </form>
        <div class="readout"><span>right-click to collapse</span><span id="timer">t = 0.00s</span></div>
        <div class="message">{{ message }}</div>
        <a class="back" href="{{ url_for('home') }}">Back to BQSL home</a>
    </main>
    <script>
        const arena = document.getElementById("arena");
        const movingDot = document.getElementById("moving-dot");
        const form = document.getElementById("captcha-form");
        const timer = document.getElementById("timer");
        const startedAt = performance.now();
        const speed = {{ motion_speed }};
        const phase = {{ motion_phase }};

        function positionAt(seconds) {
            const cycle = (seconds * speed + phase) % 2;
            const progress = cycle <= 1 ? cycle : 2 - cycle;
            return 4 + progress * 92;
        }

        function animate(now) {
            const elapsed = (now - startedAt) / 1000;
            movingDot.style.left = positionAt(elapsed) + "%";
            timer.textContent = "t = " + elapsed.toFixed(2) + "s";
            requestAnimationFrame(animate);
        }

        arena.addEventListener("contextmenu", (event) => {
            event.preventDefault();
            const elapsed = (performance.now() - startedAt) / 1000;
            const x = ((positionAt(elapsed) - 4) / 92) * 100;
            document.getElementById("click-x").value = x.toFixed(4);
            document.getElementById("click-elapsed").value = elapsed.toFixed(4);
            form.submit();
        });

        requestAnimationFrame(animate);
    </script>
</body>
</html>
"""


def quantum_captcha(seed):
    """
    Numerically evolve a 1D quantum wavefunction
    using the time-dependent Schrödinger equation.
    """

    # Convert CAPTCHA seed into deterministic randomness
    digest = hashlib.sha256(seed.encode()).digest()

    random_number = int.from_bytes(
        digest[:8],
        "big"
    )

    rng = np.random.default_rng(random_number)

    # Space
    N = 256

    x = np.linspace(-10, 10, N)

    dx = x[1] - x[0]

    # Physical constants
    hbar = 1.0
    mass = 1.0

    # ------------------------------------------------
    # Random quantum potential
    # ------------------------------------------------

    V = rng.random(N) * 3.0

    # Smooth the potential
    V = (
        V
        + np.roll(V, 1)
        + np.roll(V, -1)
    ) / 3

    # ------------------------------------------------
    # Initial wave packet
    # ------------------------------------------------

    center = rng.uniform(-4, 4)

    width = rng.uniform(0.4, 1.0)

    momentum = rng.uniform(4, 10)

    psi = np.exp(
        -(x - center) ** 2
        / (2 * width ** 2)
    ).astype(complex)

    psi *= np.exp(
        1j * momentum * x
    )

    # Normalize
    psi /= np.sqrt(
        np.sum(np.abs(psi) ** 2) * dx
    )

    # ------------------------------------------------
    # Schrödinger evolution
    # ------------------------------------------------

    dt = 0.0005

    for _ in range(500):

        second_derivative = np.zeros_like(
            psi,
            dtype=complex
        )

        second_derivative[1:-1] = (
            psi[2:]
            - 2 * psi[1:-1]
            + psi[:-2]
        ) / dx ** 2

        # Hamiltonian:
        #
        # Hψ =
        # -(ℏ² / 2m) ∂²ψ/∂x² + Vψ

        Hpsi = (
            -(hbar ** 2 / (2 * mass))
            * second_derivative
            + V * psi
        )

        # Schrödinger equation:
        #
        # iℏ ∂ψ/∂t = Hψ

        psi += (
            -1j
            * Hpsi
            * dt
            / hbar
        )

        # Normalize again
        norm = np.sqrt(
            np.sum(np.abs(psi) ** 2) * dx
        )

        if norm != 0:
            psi /= norm

    # ------------------------------------------------
    # Probability density
    # ------------------------------------------------

    probability = np.abs(psi) ** 2

    # Divide the space into 16 regions

    regions = np.array_split(
        probability,
        16
    )

    region_probability = [
        np.sum(region)
        for region in regions
    ]

    # Region containing highest probability

    answer = (
        int(np.argmax(region_probability))
        + 1
    )

    return probability, answer


def make_wave(probability):
    """
    Convert probability density into an
    ASCII visualization.
    """

    regions = np.array_split(
        probability,
        64
    )

    values = []

    for region in regions:

        value = np.mean(region)

        if value < 0.005:
            char = "."

        elif value < 0.02:
            char = ":"

        elif value < 0.05:
            char = "*"

        elif value < 0.10:
            char = "O"

        else:
            char = "#"

        values.append(char)

    return "".join(values)


def motion_position(elapsed, speed, phase):
    cycle = (elapsed * speed + phase) % 2
    progress = cycle if cycle <= 1 else 2 - cycle
    return 4 + progress * 92


@app.route("/members", methods=["GET", "POST"])
def members():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()

        if not name or not email:
            return jsonify({"error": "name and email are required"}), 400

        try:
            with get_db() as connection:
                cursor = connection.execute(
                    "INSERT INTO members (name, email) VALUES (?, ?)",
                    (name, email)
                )
                member = connection.execute(
                    "SELECT id, name, email, created_at FROM members WHERE id = ?",
                    (cursor.lastrowid,)
                ).fetchone()
        except sqlite3.IntegrityError:
            return jsonify({"error": "email is already registered"}), 409

        return jsonify(dict(member)), 201

    with get_db() as connection:
        member_rows = connection.execute(
            "SELECT id, name, email, created_at FROM members ORDER BY id"
        ).fetchall()

    return jsonify([dict(member) for member in member_rows])


@app.route("/", methods=["GET"])
def home():
    return send_file(
        app.root_path + "/index.html"
    )


@app.route("/README.md", methods=["GET"])
def readme():
    return send_file(
        app.root_path + "/README.md",
        mimetype="text/plain"
    )


@app.route("/verify", methods=["GET", "POST"])
def captcha():

    message = ""

    csrf_token = session.get("csrf_token")

    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        session["csrf_token"] = csrf_token

    # --------------------------------------------
    # Verify submitted answer
    # --------------------------------------------

    if request.method == "POST":

        submitted_token = request.form.get(
            "csrf_token",
            ""
        )

        if not hmac.compare_digest(
            submitted_token,
            csrf_token
        ):
            message = "Invalid security token. Refresh and try again."

        else:

            created = session.get(
                "captcha_time",
                0
            )

            # CAPTCHA expires after 2 minutes

            if time.time() - created > 120:

                message = "CAPTCHA expired."

            else:
                try:
                    click_position = float(request.form.get("click_x", "nan"))
                    click_elapsed = float(request.form.get("click_elapsed", "nan"))
                except (TypeError, ValueError):
                    click_position = float("nan")
                    click_elapsed = float("nan")

                expected_position = motion_position(
                    click_elapsed,
                    session.get("motion_speed", 1),
                    session.get("motion_phase", 0)
                )

                if (
                    0 <= click_elapsed <= 120
                    and abs(click_position - session.get("captcha_target", 50)) <= 6
                    and abs(click_position - expected_position) <= 6
                ):

                    message = (
                        "Correct. Quantum state aligned."
                    )

                    session.pop("captcha_answer", None)
                    session.pop("captcha_time", None)
                    session.pop("captcha_target", None)
                    session.pop("motion_speed", None)
                    session.pop("motion_phase", None)

                    session["captcha_verified"] = True
                    return render_template("captcha_success.html")

                message = "Missed alignment. Try again."


    # --------------------------------------------
    # Create new CAPTCHA
    # --------------------------------------------

    if "captcha_answer" not in session:

        seed = secrets.token_hex(32)

        probability, answer = quantum_captcha(
            seed
        )

        session["captcha_answer"] = answer

        session["captcha_seed"] = seed

        session["captcha_time"] = time.time()

        session["captcha_target"] = (
            4 + ((answer - 0.5) / 16) * 92
        )

        digest = hashlib.sha256(seed.encode()).digest()
        session["motion_speed"] = 0.75 + (float(np.max(probability)) * 2)
        session["motion_phase"] = int.from_bytes(digest[8:16], "big") / 2 ** 64

        wave = make_wave(probability)

    else:

        # Generate display from existing challenge

        seed = session["captcha_seed"]

        probability, _ = quantum_captcha(
            seed
        )

        wave = make_wave(probability)

    return render_template_string(
        HTML,
        target_position=session.get("captcha_target", 50),
        motion_speed=session.get("motion_speed", 1),
        motion_phase=session.get("motion_phase", 0),
        message=message,
        csrf_token=csrf_token
    )


@app.route("/create-user", methods=["GET", "POST"])
def create_user():
    if not session.get("captcha_verified"):
        return redirect(url_for("captcha"))

    if request.method == "GET":
        return render_template("create_user.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirmation = request.form.get("confirm_password", "")
    public_key = request.form.get("public_key", "").strip()

    if not all((username, email, password, confirmation, public_key)):
        return render_template(
            "create_user.html",
            error="All fields are required.",
        )

    if password != confirmation:
        return render_template(
            "create_user.html",
            error="Passwords do not match.",
        )

    try:
        challenge = secrets.token_urlsafe(32)
        encrypted_message = encrypt_gpg_message(public_key, challenge)
    except (ValueError, StopIteration, subprocess.SubprocessError):
        return render_template(
            "create_user.html",
            error="The GPG public key is invalid.",
        )

    token = secrets.token_urlsafe(32)

    with get_db() as connection:
        connection.execute(
            """
            DELETE FROM pending_registrations
            WHERE expires_at < ?
            """,
            (time.time(),),
        )
        connection.execute(
            """
            INSERT INTO pending_registrations
            (token, username, email, password_hash, public_key,
             challenge_hash, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                username,
                email,
                generate_password_hash(password),
                public_key,
                hashlib.sha256(challenge.encode()).hexdigest(),
                time.time() + 300,
            ),
        )

    session["registration_token"] = token

    return render_template(
        "create_user.html",
        encrypted_message=encrypted_message,
    )


@app.route("/create-user/verify", methods=["POST"])
def verify_registration():
    if not session.get("captcha_verified"):
        return redirect(url_for("captcha"))

    token = session.pop("registration_token", None)
    submitted = request.form.get("decrypted_message", "").strip()

    if not token:
        return render_template(
            "create_user.html",
            error="Registration has expired. Please start again.",
        ), 400

    with get_db() as connection:
        pending = connection.execute(
            """
            SELECT * FROM pending_registrations
            WHERE token = ? AND expires_at > ?
            """,
            (token, time.time()),
        ).fetchone()

        if not pending:
            return render_template(
                "create_user.html",
                error="Registration has expired. Please start again.",
            ), 400

        submitted_hash = hashlib.sha256(
            submitted.encode()
        ).hexdigest()

        if not hmac.compare_digest(
            submitted_hash, pending["challenge_hash"]
        ):
            return render_template(
                "create_user.html",
                error="The decrypted GPG message is incorrect.",
            ), 401

        try:
            connection.execute(
                """
                INSERT INTO users
                (username, email, password_hash, public_key)
                VALUES (?, ?, ?, ?)
                """,
                (
                    pending["username"],
                    pending["email"],
                    pending["password_hash"],
                    pending["public_key"],
                ),
            )
        except sqlite3.IntegrityError:
            connection.execute(
                "DELETE FROM pending_registrations WHERE token = ?",
                (token,),
            )
            return render_template(
                "create_user.html",
                error="Username or email is already registered.",
            ), 409

        connection.execute(
            "DELETE FROM pending_registrations WHERE token = ?",
            (token,),
        )

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if not session.get("captcha_verified"):
        return redirect(url_for("captcha"))

    error = ""
    encrypted_message = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as connection:
            user = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            error = "Invalid username or password."
        else:
            challenge = secrets.token_urlsafe(32)
            session["login_challenge"] = challenge
            session["login_user_id"] = user["id"]
            session["login_challenge_time"] = time.time()

            try:
                encrypted_message = encrypt_gpg_message(
                    user["public_key"],
                    challenge,
                )
            except (ValueError, subprocess.SubprocessError, StopIteration):
                error = "Unable to create the GPG challenge."

    return render_template(
        "login.html",
        error=error,
        encrypted_message=encrypted_message,
    )


@app.route("/login/verify", methods=["POST"])
def verify_login():
    if not session.get("captcha_verified"):
        return redirect(url_for("captcha"))

    expected = session.get("login_challenge")
    submitted = request.form.get("decrypted_message", "").strip()
    created = session.get("login_challenge_time", 0)

    valid = (
        expected
        and time.time() - created <= 300
        and hmac.compare_digest(submitted, expected)
    )

    if not valid:
        return render_template(
            "login.html",
            error="The decrypted message is invalid or expired.",
        ), 401

    session["user_id"] = session.pop("login_user_id")
    session.pop("login_challenge", None)
    session.pop("login_challenge_time", None)

    # Require a fresh CAPTCHA on the next login.
    session.pop("captcha_verified", None)

    return redirect(url_for("home"))


def encrypt_gpg_message(public_key, message):
    """Encrypt message with an armored public GPG key."""
    if (
        "-----BEGIN PGP PUBLIC KEY BLOCK-----" not in public_key
        or "-----END PGP PUBLIC KEY BLOCK-----" not in public_key
        or "-----BEGIN PGP PRIVATE KEY BLOCK-----" in public_key
    ):
        raise ValueError("A valid public GPG key is required.")

    with tempfile.TemporaryDirectory(prefix="bqsl-gpg-") as home:
        os.chmod(home, 0o700)
        key_file = os.path.join(home, "public-key.asc")

        with open(key_file, "w", encoding="utf-8") as file:
            file.write(public_key)

        base = [
            "gpg",
            "--batch",
            "--no-options",
            "--no-auto-check-trustdb",
            "--homedir",
            home,
        ]

        subprocess.run(
            [*base, "--import", key_file],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        listing = subprocess.run(
            [*base, "--with-colons", "--list-keys"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout

        fingerprint = next(
            fields[9]
            for line in listing.splitlines()
            if line.startswith("fpr:")
            and len((fields := line.split(":"))) > 9
            and fields[9]
        )

        result = subprocess.run(
            [
                *base,
                "--trust-model",
                "always",
                "--armor",
                "--encrypt",
                "--recipient",
                fingerprint,
            ],
            input=message,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        return result.stdout


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

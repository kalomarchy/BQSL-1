
from flask import Flask, request, session, render_template_string
import numpy as np
import secrets
import hashlib
import time

app = Flask(__name__)

# Used to protect the Flask session
app.secret_key = secrets.token_hex(32)


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

<h1>Quantum CAPTCHA</h1>

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
    )

    psi *= np.exp(
        1j * momentum * x
    )

    psi = psi.astype(complex)

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


@app.route("/", methods=["GET", "POST"])
def captcha():

    message = ""

    # --------------------------------------------
    # Verify submitted answer
    # --------------------------------------------

    if request.method == "POST":

        submitted = request.form.get(
            "answer",
            ""
        )

        correct = session.get(
            "captcha_answer"
        )

        created = session.get(
            "captcha_time",
            0
        )

        # CAPTCHA expires after 2 minutes

        if time.time() - created > 120:

            message = "CAPTCHA expired."

        elif submitted == str(correct):

            message = (
                "✓ Correct. Quantum verification passed."
            )

            # Destroy CAPTCHA so it can't be reused

            session.pop(
                "captcha_answer",
                None
            )

            session.pop(
                "captcha_time",
                None
            )

        else:

            message = (
                "✗ Incorrect. Try another CAPTCHA."
            )

    # --------------------------------------------
    # Create new CAPTCHA
    # --------------------------------------------

    if "captcha_answer" not in session:

        seed = secrets.token_hex(32)

        probability, answer = quantum_captcha(
            seed
        )

        session["captcha_answer"] = answer

        session["captcha_time"] = time.time()

        wave = make_wave(probability)

    else:

        # Generate display from existing challenge

        seed = str(
            session["captcha_answer"]
        )

        probability, _ = quantum_captcha(
            seed
        )

        wave = make_wave(probability)

    return render_template_string(
        HTML,
        wave=wave,
        message=message
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )

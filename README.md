# BQSL
Bitcoin Quantum Superposition Layer/v1.0

BQSL is currently a Flask prototype that presents a deterministic numerical
wave CAPTCHA. Passing the CAPTCHA only verifies that the user solved the
challenge; it does not prove Bitcoin ownership or confirm a transaction.

## Run locally

```text
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open <http://127.0.0.1:5000> in a browser.

## Bitcoin verification direction

The next layer should be a separate API that accepts public Bitcoin data and
reports verification results, for example:

- validate an address format and network;
- look up a transaction through Bitcoin Core or a trusted Esplora-compatible
	node;
- report confirmation count and output details;
- verify a signed message without ever receiving a private key.

The CAPTCHA can remain optional anti-bot protection around those endpoints. It
must not be described as a Bitcoin security mechanism or a workaround for the
Bitcoin network.

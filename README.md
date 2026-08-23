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

## Members database

The app uses SQLite for member records. By default, the database is stored in
`members.db` at the project root. Set `BQSL_DATABASE` to use another path.

List members:

```text
curl http://127.0.0.1:5000/members
```

Add a member:

```text
curl -X POST http://127.0.0.1:5000/members \
	-H 'Content-Type: application/json' \
	-d '{"name":"Ada Lovelace","email":"ada@example.com"}'
```

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

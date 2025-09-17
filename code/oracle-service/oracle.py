from flask import Flask, jsonify
import psycopg2
import hmac
import hashlib
import base64
import os

app = Flask(__name__)

# ==== CONFIG ====
DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "postgres",
    "port": 5432
}

PRIVATE_KEY = os.getenv("ORACLE_PRIVKEY", "test_secret_key")

# ==== POSTGRES CONNECTION ====
def get_all_flagged_wallets() -> str:
    """
    Returns all flagged wallets in the format:
    wallet1:true:reason1,wallet2:false:,wallet3:true:reason3
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT wallet_id, reason FROM flagged_wallets")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    entries = []
    for wallet_address, flagged, reason in rows:
        # Ensure reason is never None
        reason = reason or ""
        entries.append(f"{wallet_address}:{str(flagged).lower()}:{reason}")
    return ",".join(entries)

# ==== SIGNING ====
def sign_message(message: str) -> str:
    sig = hmac.new(PRIVATE_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()

# ==== ORACLE API ====
@app.route("/get_oracle_data", methods=["GET"])
def get_oracle_data():
    """
    Returns the entire AML dataset with signature for contract update
    """
    data = get_all_flagged_wallets()
    signature = sign_message(data)

    return jsonify({
        "data": data,
        "signature": signature
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

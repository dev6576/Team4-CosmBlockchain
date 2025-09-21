# aml_api_server.py
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import psycopg2
import os
import sys

PORT = 6000

# Add ML path
ML_PATH = os.path.join(os.path.dirname(__file__), "..", "ml-layer")
ML_PATH = os.path.abspath(ML_PATH)  # ensure absolute path
sys.path.insert(0, ML_PATH)

from ml_risk_calculator import evaluate_transaction

# =====================
# DB CONFIG
# =====================
DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5433
}

# =====================
# DB Helpers
# =====================
def get_wallet_from_db(wallet_id: str):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT wallet_id, reason, risk_score FROM flagged_wallets WHERE wallet_id = %s",
        (wallet_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"wallet_id": row[0], "reason": row[1], "risk_score": row[2]}
    return None

# =====================
# HTTP Request Handler
# =====================
class AMLRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/aml-check":
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            sender = data.get("sender")
            recipient = data.get("recipient")
            amount = data.get("amount")

            print(f"[AML API] Received request: {data}")

            response = {
                "approved": True,
                "flagged": False,
                "reason": "",
                "risk_score": 0
            }

            if not sender or not recipient:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": "sender and recipient required"}).encode())
                return

            # =====================
            # DB Lookup
            # =====================
            sender_db = get_wallet_from_db(sender)
            recipient_db = get_wallet_from_db(recipient)

            # Case 1: Either wallet is in DB → return that immediately
            if sender_db:
                response["risk_score"] = sender_db["risk_score"]
                response["flagged"] = sender_db["risk_score"] > 0
                response["reason"] = sender_db["wallet_id"] + ": " + sender_db["reason"]
            elif recipient_db:
                response["risk_score"] = recipient_db["risk_score"]
                response["flagged"] = recipient_db["risk_score"] > 0
                response["reason"] = recipient_db["wallet_id"] + ": " + recipient_db["reason"]
            else:
                # Case 2: Neither in DB → ML evaluation for both wallets
                ml_results = evaluate_transaction(sender, recipient, amount)
                for wallet_id, data_ml in ml_results.items():
                    if data_ml["risk_score"] > response["risk_score"]:
                        response["risk_score"] = data_ml["risk_score"]
                        response["flagged"] = data_ml["risk_score"] > 5
                        response["reason"] = "ML predicted score"

            # Approved is False if flagged
            if response["flagged"]:
                response["approved"] = False

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

# =====================
# Run Server
# =====================
def run():
    print(f"[AML API] Starting server on port {PORT}...")
    server = HTTPServer(("", PORT), AMLRequestHandler)
    server.serve_forever()

if __name__ == "__main__":
    run()

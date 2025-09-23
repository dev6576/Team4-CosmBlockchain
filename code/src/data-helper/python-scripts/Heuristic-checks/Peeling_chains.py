import psycopg2
from datetime import datetime

# ==== DB CONFIG ====
DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5433
}

def insert_flagged_wallets(cur, wallets, reason, risk_score):
    """
    Insert flagged wallets into flagged_wallets table.
    If the wallet already exists, update only if the new risk_score is higher.
    """
    for wallet in wallets:
        try:
            wallet_id = str(wallet).strip()
            reason_text = str(reason).strip()
            risk_val = int(risk_score)

            print(f"➡️ Inserting wallet: {wallet_id}, Reason: {reason_text}, Risk: {risk_val}")

            cur.execute("""
                INSERT INTO flagged_wallets (wallet_id, reason, risk_score)
                VALUES (%s, %s, %s)
                ON CONFLICT (wallet_id) DO UPDATE
                SET risk_score = GREATEST(flagged_wallets.risk_score, EXCLUDED.risk_score),
                    reason = EXCLUDED.reason
                WHERE EXCLUDED.risk_score > flagged_wallets.risk_score;
            """, (wallet_id, reason_text, risk_val))

        except Exception as e:
            print(f"❌ Error inserting wallet {wallet_id}: {e}")


# ==========================
# Detection Functions
# ==========================
def detect_peeling_eth(cur, min_outputs=5, time_window_minutes=10):
    """
    Detect ETH wallets that rapidly disperse funds to multiple wallets.
    """
    cur.execute(f"""
        WITH rapid_sends AS (
            SELECT from_address, COUNT(DISTINCT to_address) AS outputs
            FROM eth_token_transfers
            WHERE block_timestamp >= NOW() - INTERVAL '{time_window_minutes} minutes'
            GROUP BY from_address
            HAVING COUNT(DISTINCT to_address) >= {min_outputs}
        )
        SELECT from_address FROM rapid_sends;
    """)
    return [str(row[0]) for row in cur.fetchall() if row[0] is not None]


def detect_peeling_btc(cur, min_outputs=5, time_window_minutes=10):
    """
    Detect BTC wallets that rapidly disperse funds to multiple wallets.
    Uses bitcoin_inputs and bitcoin_outputs tables.
    """
    cur.execute(f"""
        WITH tx_chain AS (
            SELECT i.addresses AS from_address,
                   o.addresses AS to_address,
                   o.block_timestamp
            FROM bitcoin_inputs i
            JOIN bitcoin_outputs o ON i.transaction_hash = o.transaction_hash
            WHERE o.block_timestamp >= NOW() - INTERVAL '{time_window_minutes} minutes'
        ),
        rapid_sends AS (
            SELECT from_address, COUNT(DISTINCT to_address) AS outputs
            FROM tx_chain
            GROUP BY from_address
            HAVING COUNT(DISTINCT to_address) >= {min_outputs}
        )
        SELECT from_address FROM rapid_sends;
    """)
    return [str(row[0]) for row in cur.fetchall() if row[0] is not None]


# ==========================
# Main Heuristics Runner
# ==========================
def run_heuristics():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("🚀 Running rapid fund dispersion (peeling chain) checks...")

    # ETH peeling chains
    eth_peeling = detect_peeling_eth(cur)
    print(f"🔎 ETH peeling chain wallets found: {len(eth_peeling)}")
    insert_flagged_wallets(cur, eth_peeling, "ETH rapid fund dispersion (peeling chain)", 8)

    # BTC peeling chains
    btc_peeling = detect_peeling_btc(cur)
    print(f"🔎 BTC peeling chain wallets found: {len(btc_peeling)}")
    insert_flagged_wallets(cur, btc_peeling, "BTC rapid fund dispersion (peeling chain)", 8)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Rapid fund dispersion checks complete. Results inserted into flagged_wallets.")


if __name__ == "__main__":
    run_heuristics()

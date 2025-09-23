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


def detect_structuring_eth(cur, threshold_value=10, min_tx_count=20, time_window_hours=168):
    cur.execute(f"""
        WITH tx_window AS (
            SELECT from_address, COUNT(*) AS tx_count
            FROM eth_token_transfers
            WHERE value::NUMERIC <= {threshold_value}
              AND block_timestamp >= NOW() - INTERVAL '{time_window_hours} hours'
            GROUP BY from_address
            HAVING COUNT(*) >= {min_tx_count}
        )
        SELECT from_address FROM tx_window;
    """)
    return [str(row[0]) for row in cur.fetchall() if row[0] is not None]


def detect_structuring_btc(cur, threshold_value=0.1, min_tx_count=20, time_window_hours=168):
    cur.execute(f"""
        WITH tx_window AS (
            SELECT i.addresses AS from_address, COUNT(*) AS tx_count
            FROM bitcoin_inputs i
            JOIN bitcoin_outputs o
              ON i.transaction_hash = o.transaction_hash
            WHERE o.value <= {threshold_value}
              AND o.block_timestamp >= NOW() - INTERVAL '{time_window_hours} hours'
            GROUP BY i.addresses
            HAVING COUNT(*) >= {min_tx_count}
        )
        SELECT from_address FROM tx_window;
    """)
    return [str(row[0]) for row in cur.fetchall() if row[0] is not None]


# ==========================
# Main Heuristics Runner
# ==========================
def run_heuristics():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("🚀 Running heuristic checks...")
    # ETH structuring
    eth_structuring = detect_structuring_eth(cur)
    print(f"🔎 ETH structuring wallets found: {len(eth_structuring)}")
    insert_flagged_wallets(cur, eth_structuring, "ETH structuring (many small txs)", 8)

    # BTC structuring
    btc_structuring = detect_structuring_btc(cur)
    print(f"🔎 BTC structuring wallets found: {len(btc_structuring)}")
    insert_flagged_wallets(cur, btc_structuring, "BTC structuring (many small txs)", 8)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Heuristic checks complete. Results inserted into flagged_wallets.")


if __name__ == "__main__":
    run_heuristics()

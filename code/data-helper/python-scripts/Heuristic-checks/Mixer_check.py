import psycopg2
import os
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



def detect_equal_output_mixers(cur):
    cur.execute("""
        WITH suspicious_txs AS (
            SELECT
                transaction_hash,
                COUNT(*) AS output_count,
                COUNT(DISTINCT value) AS distinct_output_values
            FROM bitcoin_outputs
            GROUP BY transaction_hash
            HAVING COUNT(*) >= 5
               AND COUNT(DISTINCT value) = 1
        )
        SELECT DISTINCT o.addresses
        FROM bitcoin_outputs o
        JOIN suspicious_txs t ON o.transaction_hash = t.transaction_hash
        WHERE o.addresses IS NOT NULL;
    """)
    rows = cur.fetchall()
    return [str(row[0]) for row in rows if row[0] is not None]

def detect_quick_cycles_eth(cur):
    cur.execute("""
        WITH tx_times AS (
            SELECT from_address, to_address, block_timestamp
            FROM eth_traces
            WHERE value > 0
        )
        SELECT DISTINCT t1.from_address
        FROM tx_times t1
        JOIN tx_times t2
          ON t1.to_address = t2.from_address
        WHERE EXTRACT(EPOCH FROM (t2.block_timestamp - t1.block_timestamp)) < 300;
    """)
    rows = cur.fetchall()
    return [str(row[0]) for row in rows if row[0] is not None]



def detect_high_counterparty_eth(cur):
    """
    Detect Ethereum wallets with very high number of unique counterparties.
    """
    cur.execute("""
        SELECT from_address
        FROM eth_token_transfers
        GROUP BY from_address
        HAVING COUNT(DISTINCT to_address) > 50;
    """)
    rows = cur.fetchall()
    # flatten to list of strings
    return [str(row[0]) for row in rows if row[0] is not None]

def detect_high_inflow_eth(cur):
    """
    Detect Ethereum wallets receiving more than 50 deposits from at least 20 unique wallets.
    """
    cur.execute("""
        SELECT to_address
        FROM eth_token_transfers
        GROUP BY to_address
        HAVING COUNT(*) > 50 AND COUNT(DISTINCT from_address) >= 20;
    """)
    rows = cur.fetchall()
    return [str(row[0]) for row in rows if row[0] is not None]



def run_heuristics():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("🚀 Running heuristic checks...")

    # Mixer detection (BTC equal outputs)
    btc_mixers = detect_equal_output_mixers(cur)
    print(f"🔎 BTC Mixer-like wallets found: {len(btc_mixers)}")
    insert_flagged_wallets(cur, btc_mixers, "BTC equal-output mixer pattern", 9)

    # High counterparty ETH
    eth_high_cp = detect_high_counterparty_eth(cur)
    print(f"🔎 ETH high-counterparty wallets found: {len(eth_high_cp)}")
    insert_flagged_wallets(cur, eth_high_cp, "ETH high counterparty count", 7)

    # Quick cycling ETH
    eth_cycles = detect_quick_cycles_eth(cur)
    print(f"🔎 ETH quick-cycle wallets found: {len(eth_cycles)}")
    insert_flagged_wallets(cur, eth_cycles, "ETH quick fund cycling (<5m)", 6)

    # High inflow ETH
    eth_high_inflow = detect_high_inflow_eth(cur)
    print(f"🔎 ETH high-inflow wallets found: {len(eth_high_inflow)}")
    insert_flagged_wallets(cur, eth_high_inflow, "ETH high inflow from multiple wallets", 8)


    conn.commit()
    cur.close()
    conn.close()
    print("✅ Heuristic checks complete. Results inserted into flagged_wallets.")


if __name__ == "__main__":
    run_heuristics()

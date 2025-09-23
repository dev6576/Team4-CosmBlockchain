import psycopg2
import csv
import os

# Database connection config
DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5433
}

CSV_FILE = os.path.join(os.path.dirname(__file__), "other_flagged_wallets.csv")

def insert_flagged_wallets_from_csv(csv_file):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("Connected to database successfully.")

        with open(csv_file, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                print(f"Row read: {row}")  # 👈 debug print

                cur.execute("""
                    INSERT INTO flagged_wallets (wallet_id, reason, risk_score)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (wallet_id) DO NOTHING;
                """, (
                    row.get("wallet_address"),
                    row.get("reason"),
                    row.get("risk_score")
                ))
                count += 1

        conn.commit()
        print(f"✅ {count} wallets inserted from {csv_file}")
        
        cur.close()
        conn.close()
        print("Database connection closed.")

    except Exception as e:
        print(f"❌ Error inserting wallets: {e}")

if __name__ == "__main__":
    insert_flagged_wallets_from_csv(CSV_FILE)

CREATE TABLE IF NOT EXISTS flagged_wallets (
    wallet_id TEXT PRIMARY KEY,
    reason TEXT,
    risk_score INT DEFAULT 0  -- matches OracleDataEntry
);

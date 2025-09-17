-- ============================================
-- Table to maintain flagged wallets
-- ============================================
CREATE TABLE IF NOT EXISTS flagged_wallets (
    wallet_id TEXT PRIMARY KEY,
    reason TEXT
);

-- ============================================
-- Function to add or update flagged wallet
-- ============================================
CREATE OR REPLACE FUNCTION add_flagged_wallet(wallet TEXT, new_reason TEXT)
RETURNS VOID AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM flagged_wallets WHERE wallet_id = wallet) THEN
        UPDATE flagged_wallets
        SET reason = CASE
                        WHEN reason ILIKE '%' || new_reason || '%' THEN reason
                        ELSE reason || ', ' || new_reason
                     END
        WHERE wallet_id = wallet;
    ELSE
        INSERT INTO flagged_wallets(wallet_id, reason)
        VALUES(wallet, new_reason);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 1️⃣ OFAC wallet check (example list)
-- ============================================
DO $$
DECLARE
    ofac_wallets TEXT[] := ARRAY['wallet1', 'wallet2', 'wallet3'];
    w TEXT;
BEGIN
    FOREACH w IN ARRAY ofac_wallets
    LOOP
        PERFORM add_flagged_wallet(w, 'OFAC sanctioned');
    END LOOP;
END $$;

-- ============================================
-- 2️⃣ High value transaction checks
-- ============================================

-- Bitcoin high value transactions (>100 BTC)
INSERT INTO flagged_wallets(wallet_id, reason)
SELECT wallet, 'High BTC transaction'
FROM (
    SELECT DISTINCT i.addresses AS wallet
    FROM bitcoin_inputs i
    WHERE i.value > 100
) sub
ON CONFLICT (wallet_id)
DO UPDATE SET reason = flagged_wallets.reason || ', High BTC transaction';

-- Ethereum high value transactions (>100 ETH)
INSERT INTO flagged_wallets(wallet_id, reason)
SELECT wallet, 'High ETH transaction'
FROM (
    SELECT DISTINCT t.fromm_address AS wallet
    FROM eth_transactions t
    WHERE t.value > 100
) sub
ON CONFLICT (wallet_id)
DO UPDATE SET reason = flagged_wallets.reason || ', High ETH transaction';

-- ============================================
-- 3️⃣ Future heuristics can be added here
-- Example: rapid transactions, unusual patterns, smart contract interactions
-- ============================================

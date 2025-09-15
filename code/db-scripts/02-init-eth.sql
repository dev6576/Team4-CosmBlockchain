\connect ethereum;

CREATE TABLE IF NOT EXISTS balances (
    address TEXT NOT NULL,
    eth_balance NUMERIC
);

CREATE TABLE IF NOT EXISTS blocks (
    timestamp TIMESTAMP NOT NULL,
    number BIGINT NOT NULL,
    hash TEXT NOT NULL,
    parent_hash TEXT,
    nonce TEXT NOT NULL,
    sha3_uncles TEXT,
    logs_bloom TEXT,
    transactions_root TEXT,
    state_root TEXT,
    receipts_root TEXT,
    miner TEXT,
    difficulty NUMERIC,
    total_difficulty NUMERIC,
    size BIGINT,
    extra_data TEXT,
    gas_limit BIGINT,
    gas_used BIGINT,
    transaction_count BIGINT,
    base_fee_per_gas BIGINT,
    withdrawals_root TEXT,
    withdrawals_index BIGINT,
    wiithdrawals_validator_index BIGINT,
    withdrawals_address TEXT,
    withdrawals_amount TEXT,
    blob_gas_used BIGINT,
    excess_block_gas BIGINT
);


CREATE TABLE IF NOT EXISTS contracts (
    address TEXT NOT NULL,
    bytecode TEXT NOT NULL,
    function_sighashes TEXT,
    is_erc20 BOOLEAN,
    is_erc721 BOOLEAN,
    block_timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    block_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS load_metadata (
    chain TEXT,
    load_all_partitions BOOLEAN,
    ds DATE,
    run_id TEXT,
    complete_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
    log_index BIGINT NOT NULL,
    transaction_hash TEXT NOT NULL,
    transaction_index BIGINT NOT NULL,
    address TEXT,
    data TEXT,
    topics TEXT,
    block_timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    block_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT NOT NULL,
    start_trace_id TEXT NOT NULL,
    start_block_number BIGINT NOT NULL,
    start_block_timestamp TIMESTAMP NOT NULL,
    wallet_address TEXT NOT NULL,
    contract_address TEXT
);

CREATE TABLE IF NOT EXISTS token_transfers (
    token_address TEXT NOT NULL,
    from_address TEXT,
    to_address TEXT,
    value TEXT,
    transaction_hash TEXT NOT NULL,
    log_index BIGINT,
    block_timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    block_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    address TEXT NOT NULL,
    symbol TEXT,
    name TEXT,
    decimals TEXT,
    total_supply TEXT,
    block_timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    block_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS traces (
    transaction_hash TEXT,
    transaction_index BIGINT,
    from_address TEXT,
    to_address TEXT,
    value NUMERIC,
    input TEXT,
    output TEXT,
    trace_type TEXT NOT NULL,
    call_type TEXT,
    reward_type TEXT,
    gas BIGINT,
    gas_used BIGINT,
    subtraces BIGINT,
    trace_address TEXT,
    error TEXT,
    status BIGINT,
    block_timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    block_hash TEXT NOT NULL,
    trace_id TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    hash TEXT NOT NULL,
    nonce BIGINT NOT NULL,
    transaction_index BIGINT NOT NULL,
    fromm_address TEXT NOT NULL,
    to_address TEXT,
    value NUMERIC,
    gas BIGINT,
    gas_price BIGINT,
    input TEXT,
    receipt_cumulative_gas_used BIGINT,
    receipt_gas_used BIGINT,
    receipt_contract_address TEXT,
    receipt_root TEXT,
    receipt_status BIGINT,
    block_timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    block_hash TEXT NOT NULL,
    max_fee_per_gas BIGINT,
    max_priority_fee_per_gas BIGINT,
    transaction_type BIGINT,
    receipt_effective_gas_price BIGINT,
    max_fee_per_blob_gas BIGINT,
    block_versioned_hashes TEXT,
    receipt_blob_gas_price BIGINT,
    receipt_blob_gas_used BIGINT
);
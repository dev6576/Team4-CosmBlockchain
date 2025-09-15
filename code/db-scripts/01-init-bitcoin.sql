\connect bitcoin;

CREATE TABLE IF NOT EXISTS blocks (
    hash TEXT NOT NULL,
    size BIGINT,
    stripped_size BIGINT,
    weight BIGINT,
    number BIGINT NOT NULL,
    version BIGINT,
    merkle_root TEXT,
    timestamp TIMESTAMP NOT NULL,
    timestamp_month DATE NOT NULL,
    nonce TEXT,
    bits TEXT,
    coinbase_param TEXT,
    transaction_count BIGINT
);

CREATE TABLE IF NOT EXISTS inputs (
    transaction_hash TEXT,
    block_hash TEXT,
    block_number BIGINT,
    block_timestamp TIMESTAMP,
    index BIGINT,
    spent_transaction_hash TEXT,
    spent_output_index BIGINT,
    script_asm TEXT,
    script_hex TEXT,
    sequence BIGINT,
    required_signatures BIGINT,
    type TEXT,
    addresses TEXT,
    value NUMERIC
);


CREATE TABLE IF NOT EXISTS outputs (
    transaction_hash TEXT,
    block_hash TEXT,
    block_number BIGINT,
    block_timestamp TIMESTAMP,
    index BIGINT,
    script_asm TEXT,
    script_hex TEXT,
    required_signatures BIGINT,
    type TEXT,
    addresses TEXT,
    value NUMERIC
);

CREATE TABLE IF NOT EXISTS transactions (
    hash TEXT NOT NULL,
    size BIGINT,
    virtual_size BIGINT,
    version BIGINT,
    lock_time BIGINT,
    block_hash TEXT NOT NULL,
    block_number BIGINT NOT NULL,
    block_timestamp TIMESTAMP NOT NULL,
    block_timestamp_month DATE NOT NULL,
    input_count BIGINT,
    output_count BIGINT,
    input_value NUMERIC,
    output_value NUMERIC,
    is_coinbase BOOLEAN,
    fee NUMERIC,
    input_index BIGINT,
    input_spent_transaction_hash TEXT,
    input_spent_output_index BIGINT,
    input_script_asm TEXT,
    input_script_hex TEXT,
    input_sequence BIGINT,
    input_required_signatures BIGINT,
    input_type TEXT,
    input_addresses TEXT,
    input_value_1 NUMERIC,
    output_index NUMERIC,
    output_script_asm TEXT,
    output_script_hex TEXT,
    output_required_signatures BIGINT,
    output_type TEXT,
    output_addresses TEXT,
    output_value_1 NUMERIC 
);

#!/bin/bash
set -e

POSTGRES_USER=postgres

import_files() {
  folder=$1
  table=$2
  db=$3

  for file in $folder/*.csv; do
    echo "Importing $file into $table..."
    psql -U "$POSTGRES_USER" -d $db -c "\copy $table FROM '$file' CSV HEADER"
  done
}

import_bitcoin_all() {
  db=bitcoin

  table=inputs
  import_files /crypto_data/btc/btc-inputs1 $table $db
  import_files /crypto_data/btc/btc-inputs2 $table $db
  import_files /crypto_data/btc/btc-inputs3 $table $db
  import_files /crypto_data/btc/btc-inputs4 $table $db
  import_files /crypto_data/btc/btc-inputs5 $table $db

  table=outputs
  import_files /crypto_data/btc/btc-outputs1 $table $db
  import_files /crypto_data/btc/btc-outputs2 $table $db
  import_files /crypto_data/btc/btc-outputs3 $table $db
  import_files /crypto_data/btc/btc-outputs4 $table $db

  psql -U "$POSTGRES_USER" -d $db -c "\copy blocks FROM /crypto_data/btc/btc-blocks000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy transactions FROM /crypto_data/btc/btc-transactions000000000000.csv CSV HEADER"
}

import_ethereum_all() {
  db=ethereum

  table=balances
  import_files /crypto_data/eth/eth-balances $table $db

  table=blocks
  import_files /crypto_data/eth/eth-blocks $table $db

  table=logs
  import_files /crypto_data/eth/eth-logs1 $table $db
  import_files /crypto_data/eth/eth-logs2 $table $db
  import_files /crypto_data/eth/eth-logs3 $table $db
  import_files /crypto_data/eth/eth-logs4 $table $db
  import_files /crypto_data/eth/eth-logs5 $table $db
  import_files /crypto_data/eth/eth-logs6 $table $db
  import_files /crypto_data/eth/eth-logs7 $table $db

  table=sessions
  import_files /crypto_data/eth/eth-sessions $table $db

  table=token_transfers
  import_files /crypto_data/eth/eth-token_transfers $table $db

  table=transactions
  import_files /crypto_data/eth/eth-transactions1 $table $db
  import_files /crypto_data/eth/eth-transactions2 $table $db
  import_files /crypto_data/eth/eth-transactions3 $table $db
  import_files /crypto_data/eth/eth-transactions4 $table $db
  import_files /crypto_data/eth/eth-transactions5 $table $db
  import_files /crypto_data/eth/eth-transactions6 $table $db
  import_files /crypto_data/eth/eth-transactions7 $table $db


  psql -U "$POSTGRES_USER" -d $db -c "\copy contracts FROM /crypto_data/eth/eth-contracts000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy load_metadata FROM /crypto_data/eth/eth-load_metadata.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy tokens FROM /crypto_data/eth/eth-tokens000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy traces FROM /crypto_data/eth/eth-traces000000000000.csv CSV HEADER"
}

######################
import_single() {
  db=bitcoin

  psql -U "$POSTGRES_USER" -d $db -c "\copy inputs FROM /crypto_data/btc/btc-inputs1/btc-inputs000000000000.csv CSV HEADER"
  table=outputs
  psql -U "$POSTGRES_USER" -d $db -c "\copy outputs FROM /crypto_data/btc/btc-outputs1/btc-outputs000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy blocks FROM /crypto_data/btc/btc-blocks000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy transactions FROM /crypto_data/btc/btc-transactions000000000000.csv CSV HEADER"

  db=ethereum
  psql -U "$POSTGRES_USER" -d $db -c "\copy balances FROM /crypto_data/eth/eth-balances/eth-balances000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy blocks FROM /crypto_data/eth/eth-blocks/eth-blocks000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy logs FROM /crypto_data/eth/eth-logs1/eth-logs000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy sessions FROM /crypto_data/eth/eth-sessions/eth-sessions000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy token_transfers FROM /crypto_data/eth/eth-token_transfers/eth-token_transfers000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy transactions FROM /crypto_data/eth/eth-transactions1/eth-transactions000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy contracts FROM /crypto_data/eth/eth-contracts000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy load_metadata FROM /crypto_data/eth/eth-load_metadata.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy tokens FROM /crypto_data/eth/eth-tokens000000000000.csv CSV HEADER"
  psql -U "$POSTGRES_USER" -d $db -c "\copy traces FROM /crypto_data/eth/eth-traces000000000000.csv CSV HEADER"
}
######################

# Import Only 1 file per table
import_single

# Import ALL files
# import_bitcoin_all
# import_ethereum_all
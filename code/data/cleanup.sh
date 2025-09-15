#!/bin/bash

rename_file() {
    for f in $1/*; do
        if [[ "$f" != *.csv ]]; then
            mv "$f" "$f.csv"
        fi
    done
}

rename_file ./eth/eth-balances
rename_file ./eth/eth-token_transfers
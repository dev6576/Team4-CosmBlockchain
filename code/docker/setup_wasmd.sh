#!/bin/sh
#set -o errexit -o nounset -o pipefail

# -----------------------
# Chain configuration
# -----------------------
STAKE=${STAKE_TOKEN:-ustake}
CHAIN_ID=${CHAIN_ID:-testing}
MONIKER=${MONIKER:-node001}
KEYRING="--keyring-backend=test"
HOME_DIR="$HOME/.wasmd"

# -----------------------
# Init chain
# -----------------------
wasmd init --chain-id "$CHAIN_ID" "$MONIKER"

# staking/governance token is hardcoded in config, change this
sed -i "s/\"stake\"/\"$STAKE\"/" "$HOME"/.wasmd/config/genesis.json
# this is essential for sub-1s block times (or header times go crazy)
sed -i 's/"time_iota_ms": "1000"/"time_iota_ms": "10"/' "$HOME"/.wasmd/config/genesis.json


# -----------------------
# Import accounts with fixed mnemonics
# -----------------------
echo "pony swap next infant awkward sheriff first ridge light away net shadow ankle meat copy various spell timber aerobic name atom excuse just gossip" \
  | wasmd keys add alice --recover $KEYRING
echo "mesh admit blade produce equip humor cluster chair arch loud like grant extend believe avocado hover dream market resist tobacco mass copper tide inherit" \
  | wasmd keys add bob --recover $KEYRING
echo "artist still shield fit embark same follow lounge model dumb valid half snake deposit divorce develop color glory liberty elder flight silly swing audit" \
  | wasmd keys add charlie --recover $KEYRING
echo "enemy flower party waste put south clip march victory breeze oxygen cram hospital march enlist black october surprise across wage bomb spawn describe heavy" \
  | wasmd keys add admin --recover $KEYRING
echo "leopard run palm busy weasel comfort maze turkey canyon rural response predict ball scale coil tape organ dizzy paddle mystery fluid flight capital thing" \
  | wasmd keys add oracle --recover $KEYRING

# -----------------------
# Create validator key (new)
# -----------------------
wasmd keys add validator $KEYRING

# -----------------------
# Fund accounts
# -----------------------
wasmd genesis add-genesis-account alice     "1000000000$STAKE" $KEYRING
wasmd genesis add-genesis-account bob       "1000000000$STAKE" $KEYRING
wasmd genesis add-genesis-account charlie   "1000000000$STAKE" $KEYRING
wasmd genesis add-genesis-account admin     "1000000000$STAKE" $KEYRING
wasmd genesis add-genesis-account validator "1000000000$STAKE" $KEYRING

# -----------------------
# Genesis tx for validator
# -----------------------
wasmd genesis gentx validator "250000000$STAKE" --chain-id="$CHAIN_ID" $KEYRING
wasmd genesis collect-gentxs

echo "✅ Chain initialized successfully!"
echo "Accounts:"
wasmd keys list $KEYRING
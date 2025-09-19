use cosmwasm_schema::{cw_serde, QueryResponses};
use cosmwasm_std::{Addr, Binary, Uint128};

/// Each oracle entry = one flagged wallet + reason + optional risk score
#[cw_serde]
pub struct OracleDataEntry {
    pub wallet: String,
    pub reason: String,
    pub risk_score: Option<u64>,
}

#[cw_serde]
pub struct OracleDataResponse {
    pub data: Vec<OracleDataEntry>,
}

#[cw_serde]
pub struct OraclePubkeyResponse {
    pub pubkey: Binary,
    pub key_type: String,
}

#[cw_serde]
pub struct AdminResponse {
    pub admin: Addr,
}

#[cw_serde]
pub struct InstantiateMsg {
    pub oracle_pubkey: Binary,
    pub oracle_key_type: String, // "secp256k1" or "ed25519"
}

#[cw_serde]
pub enum ExecuteMsg {
    Transfer { recipient: String, amount: Uint128 },
    Send { recipient: String },

    /// Oracle pushes new dataset (signed JSON string from Flask)
    OracleDataUpdate { data: Vec<OracleDataEntry>, signature: Binary },

    /// Admin updates oracle key
    UpdateOracle { new_pubkey: Binary, new_key_type: Option<String> },

    /// Admin can delete a wallet from oracle data
    DeleteWallet { wallet: String },
}

#[cw_serde]
#[derive(QueryResponses)]
pub enum QueryMsg {
    /// Returns all oracle data
    #[returns(OracleDataResponse)]
    GetOracleData {},

    /// Returns oracle pubkey + type
    #[returns(OraclePubkeyResponse)]
    GetOraclePubkey {},

    /// Returns admin address
    #[returns(AdminResponse)]
    GetAdmin {},

    /// Example balance query
    #[returns(Uint128)]
    GetBalance { address: String },

    /// Returns AML check status (true if flagged, false otherwise)
    #[returns(bool)]
    CheckAML { wallet: String },
}

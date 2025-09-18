use cosmwasm_schema::{cw_serde, QueryResponses};
use cosmwasm_std::{Addr, Binary, Uint128};

/// Each oracle entry = one flagged wallet + reason
#[cw_serde]
pub struct OracleDataEntry {
    pub wallet: String,
    pub reason: String,
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
    UpdateOracle { new_pubkey: Binary, new_key_type: Option<String> },
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

    /// Returns true if flagged, false otherwise
    #[returns(bool)]
    CheckAML { wallet: String },
}

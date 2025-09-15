use cosmwasm_schema::QueryResponses;
use cosmwasm_std::{Addr, Binary};
use sha2::{Sha256, Digest};
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct OracleDataResponse {
    pub data: Option<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct OraclePubkeyResponse {
    pub pubkey: Binary,
    pub key_type: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct AdminResponse {
    pub admin: Addr,
}
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct InstantiateMsg {
    pub oracle_pubkey: Binary,
    pub oracle_key_type: String, // "secp256k1" or "ed25519"
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ExecuteMsg {
    Send { recipient: String },
    OracleDataUpdate { data: String, signature: Binary },
    UpdateOracle { new_pubkey: Binary, new_key_type: Option<String> },
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
#[derive(QueryResponses)]
pub enum QueryMsg {
    /// Returns: OracleDataResponse
    #[returns(OracleDataResponse)]
    GetOracleData {},
    /// Returns: OraclePubkeyResponse
    #[returns(OraclePubkeyResponse)]
    GetOraclePubkey {},
    /// Returns: AdminResponse
    #[returns(AdminResponse)]
    GetAdmin {},
}

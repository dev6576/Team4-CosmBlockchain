use cosmwasm_std::{Addr, Binary};
use cw_storage_plus::Item;
use cw_storage_plus::Map;

pub const ADMIN: Item<Addr> = Item::new("admin");
pub const ORACLE_PUBKEY: Item<Binary> = Item::new("oracle_pubkey");
pub const ORACLE_PUBKEY_TYPE: Item<String> = Item::new("oracle_pubkey_type");
pub const ORACLE_DATA: Map<&str, String> = Map::new("oracle_data");

pub fn parse_key_type(s: &str) -> Option<&'static str> {
    match s.to_lowercase().as_str() {
        "secp256k1" | "k256" | "ecdsa" => Some("secp256k1"),
        "ed25519" | "ed" => Some("ed25519"),
        _ => None,
    }
}

use cosmwasm_std::{
    entry_point, to_binary, Addr, BankMsg, Binary, Coin, Deps, DepsMut, Env, Event, MessageInfo,
    Order, Response, StdError, StdResult, Uint128,
};
use cw2::set_contract_version;
use sha2::{Digest, Sha256};

use crate::msg::{
    AdminResponse, ExecuteMsg, InstantiateMsg, OracleDataEntry, OracleDataResponse,
    OraclePubkeyResponse, QueryMsg,
};
use crate::state::{parse_key_type, ADMIN, ORACLE_DATA, ORACLE_PUBKEY, ORACLE_PUBKEY_TYPE};

const CONTRACT_NAME: &str = "crates.io:oracle-contract";
const CONTRACT_VERSION: &str = env!("CARGO_PKG_VERSION");

/// -------------------- Instantiate --------------------
#[entry_point]
pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    msg: InstantiateMsg,
) -> StdResult<Response> {
    let admin = info.sender.clone();

    if parse_key_type(&msg.oracle_key_type).is_none() {
        return Err(StdError::generic_err(
            "invalid oracle_key_type: use 'secp256k1' or 'ed25519'",
        ));
    }

    ADMIN.save(deps.storage, &admin)?;
    ORACLE_PUBKEY.save(deps.storage, &msg.oracle_pubkey)?;
    ORACLE_PUBKEY_TYPE.save(deps.storage, &msg.oracle_key_type)?;

    set_contract_version(deps.storage, CONTRACT_NAME, CONTRACT_VERSION)?;

    Ok(Response::new()
        .add_attribute("action", "instantiate")
        .add_attribute("admin", admin.to_string())
        .add_attribute("oracle_pubkey", msg.oracle_pubkey.to_base64())
        .add_attribute("oracle_key_type", msg.oracle_key_type))
}

/// -------------------- Execute --------------------
#[entry_point]
pub fn execute(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    msg: ExecuteMsg,
) -> StdResult<Response> {
    match msg {
        ExecuteMsg::Send { recipient } => execute_send(deps, info, recipient),
        ExecuteMsg::Transfer { recipient, amount } => {
            execute_transfer(deps, info, recipient, amount)
        }
        ExecuteMsg::OracleDataUpdate { data, signature } => {
            execute_oracle_update(deps, env, info, data, signature)
        }
        ExecuteMsg::UpdateOracle {
            new_pubkey,
            new_key_type,
        } => execute_update_oracle(deps, info, new_pubkey, new_key_type),
    }
}

/// -------------------- Send --------------------
fn execute_send(deps: DepsMut, info: MessageInfo, recipient: String) -> StdResult<Response> {
    let sender = info.sender.to_string();

    // AML check sender
    if let Some(reason) = ORACLE_DATA.may_load(deps.storage, &sender)? {
        return Ok(Response::new()
            .add_attribute("flagged_wallet", sender)
            .add_attribute("reason", reason)
            .add_attribute("status", "AML check failed"));
    }

    // AML check recipient
    if let Some(reason) = ORACLE_DATA.may_load(deps.storage, &recipient)? {
        return Ok(Response::new()
            .add_attribute("flagged_wallet", recipient)
            .add_attribute("reason", reason)
            .add_attribute("status", "AML check failed"));
    }

    // No fund amount to check for Send; just pass along
    let recipient_addr = deps.api.addr_validate(&recipient)?;
    let funds: Vec<Coin> = info.funds.clone();

    if funds.is_empty() {
        return Err(StdError::generic_err("no funds attached to Send"));
    }

    // Check for suspiciously large amounts (>10000ustake)
    for coin in &funds {
        if coin.denom == "ustake" && coin.amount.u128() > 10000 {
            return Ok(Response::new()
                .add_attribute("sender", sender.clone())
                .add_attribute("recipient", recipient.clone())
                .add_attribute("amount", coin.amount.to_string())
                .add_attribute("status", "AML check failed")
                .add_attribute("reason", "suspiciously large amount"));
        }
    }

    let msg = BankMsg::Send {
        to_address: recipient_addr.to_string(),
        amount: funds.clone(),
    };

    let event = Event::new("send")
        .add_attribute("action", "send")
        .add_attribute("from", sender)
        .add_attribute("to", recipient_addr.to_string())
        .add_attribute("amount", format!("{:?}", funds));

    Ok(Response::new()
        .add_message(msg)
        .add_event(event)
        .add_attribute("status", "success"))
}

/// -------------------- Transfer --------------------
fn execute_transfer(
    deps: DepsMut,
    info: MessageInfo,
    recipient: String,
    amount: Uint128,
) -> StdResult<Response> {
    let sender = info.sender.to_string();

    // AML check sender
    if let Some(reason) = ORACLE_DATA.may_load(deps.storage, &sender)? {
        return Ok(Response::new()
            .add_attribute("flagged_wallet", sender)
            .add_attribute("reason", reason)
            .add_attribute("status", "AML check failed"));
    }

    // AML check recipient
    if let Some(reason) = ORACLE_DATA.may_load(deps.storage, &recipient)? {
        return Ok(Response::new()
            .add_attribute("flagged_wallet", recipient)
            .add_attribute("reason", reason)
            .add_attribute("status", "AML check failed"));
    }

    // Suspiciously large amount check
    if amount.u128() > 10000 {
        return Ok(Response::new()
            .add_attribute("sender", sender)
            .add_attribute("recipient", recipient)
            .add_attribute("amount", amount.to_string())
            .add_attribute("status", "AML check failed")
            .add_attribute("reason", "suspiciously large amount"));
    }

    Ok(Response::new()
        .add_attribute("action", "transfer")
        .add_attribute("status", "success")
        .add_attribute("to", recipient)
        .add_attribute("amount", amount.to_string()))
}

/// -------------------- Oracle update --------------------
fn execute_oracle_update(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    data: Vec<OracleDataEntry>,
    signature: Binary,
) -> StdResult<Response> {
    let pubkey = ORACLE_PUBKEY.load(deps.storage)?;
    let key_type = ORACLE_PUBKEY_TYPE.load(deps.storage)?;

    let parsed = parse_key_type(&key_type)
        .ok_or_else(|| StdError::generic_err("stored oracle_key_type invalid"))?;

    // Clear and replace oracle data
    ORACLE_DATA.clear(deps.storage);
    for entry in data {
        ORACLE_DATA.save(deps.storage, &entry.wallet, &entry.reason)?;
    }

    let event = Event::new("oracle_data_update")
        .add_attribute("action", "oracle_data_update")
        .add_attribute("sender", info.sender.to_string())
        .add_attribute("entries", "bulk_updated");

    Ok(Response::new().add_event(event))
}

/// -------------------- Update Oracle --------------------
fn execute_update_oracle(
    deps: DepsMut,
    info: MessageInfo,
    new_pubkey: Binary,
    new_key_type: Option<String>,
) -> StdResult<Response> {
    let admin = ADMIN.load(deps.storage)?;
    if info.sender != admin {
        return Err(StdError::generic_err("unauthorized"));
    }

    if let Some(kt) = &new_key_type {
        if parse_key_type(kt).is_none() {
            return Err(StdError::generic_err(
                "invalid new_key_type: use 'secp256k1'",
            ));
        }
        ORACLE_PUBKEY_TYPE.save(deps.storage, kt)?;
    }

    ORACLE_PUBKEY.save(deps.storage, &new_pubkey)?;

    let saved_type = ORACLE_PUBKEY_TYPE.load(deps.storage)?;

    let event = Event::new("oracle_admin_update")
        .add_attribute("action", "oracle_update")
        .add_attribute("admin", admin.to_string())
        .add_attribute("new_pubkey", new_pubkey.to_base64())
        .add_attribute("new_key_type", saved_type);

    Ok(Response::new().add_event(event))
}

/// -------------------- Queries --------------------
#[entry_point]
pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::GetOracleData {} => {
            let all: StdResult<Vec<OracleDataEntry>> = ORACLE_DATA
                .range(deps.storage, None, None, Order::Ascending)
                .map(|res| {
                    let (wallet, reason) = res?;
                    Ok(OracleDataEntry { wallet, reason })
                })
                .collect();

            to_binary(&OracleDataResponse { data: all? })
        }
        QueryMsg::GetOraclePubkey {} => {
            let pk = ORACLE_PUBKEY.load(deps.storage)?;
            let kt = ORACLE_PUBKEY_TYPE.load(deps.storage)?;
            to_binary(&OraclePubkeyResponse { pubkey: pk, key_type: kt })
        }
        QueryMsg::GetAdmin {} => {
            let admin = ADMIN.load(deps.storage)?;
            to_binary(&AdminResponse { admin })
        }
        QueryMsg::GetBalance { address: _ } => to_binary(&Uint128::zero()), // stub
        QueryMsg::CheckAML { wallet } => {
            if let Some(reason) = ORACLE_DATA.may_load(deps.storage, &wallet)? {
                to_binary(&(
                    wallet,
                    reason,
                    "AML check failed".to_string()
                ))
            } else {
                to_binary(&(wallet, "No suspicious activity".to_string(), "OK".to_string()))
            }
        }
    }
}

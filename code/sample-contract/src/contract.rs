use cosmwasm_std::{
    entry_point, to_binary, Addr, BankMsg, Binary, Coin, Deps, DepsMut, Env, Event, MessageInfo,
    Response, StdError, StdResult, Uint128,
};
use cw2::set_contract_version;
use sha2::{Digest, Sha256};

use crate::msg::{
    AdminResponse, ExecuteMsg, InstantiateMsg, OracleDataResponse, OraclePubkeyResponse, QueryMsg,
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
            // Step 1: Query AML oracle
            let is_flagged: bool = query_aml_status(deps.as_ref(), info.sender.to_string())?;

            // Step 2: Reject if wallet is flagged
            if is_flagged {
                return Ok(Response::new()
                    .add_attribute("action", "transfer")
                    .add_attribute("status", "AML validation failed"));
            }

            // Step 3: Continue normal transfer logic
            Ok(Response::new()
                .add_attribute("action", "transfer")
                .add_attribute("status", "success")
                .add_attribute("to", recipient)
                .add_attribute("amount", amount.to_string()))
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
    // Step 1: Query AML oracle
    let (is_flagged, reason) = query_aml_status(deps.as_ref(), info.sender.to_string())?;

    // Step 2: Reject if flagged
    if is_flagged {
        return Ok(Response::new()
            .add_attribute("action", "send")
            .add_attribute("status", "AML validation failed")
            .add_attribute("reason", reason));
    }

    // Step 3: Continue with normal send logic
    let recipient_addr = deps.api.addr_validate(&recipient)?;
    let funds: Vec<Coin> = info.funds.clone();

    if funds.is_empty() {
        return Err(StdError::generic_err("no funds attached to Send"));
    }

    let msg = BankMsg::Send {
        to_address: recipient_addr.to_string(),
        amount: funds.clone(),
    };

    let event = Event::new("send")
        .add_attribute("action", "send")
        .add_attribute("from", info.sender.to_string())
        .add_attribute("to", recipient_addr.to_string())
        .add_attribute("amount", format!("{:?}", funds));

    Ok(Response::new()
        .add_message(msg)
        .add_event(event)
        .add_attribute("status", "success"))
}

/// -------------------- Oracle update --------------------
fn execute_oracle_update(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    data: String,
    signature: Binary,
) -> StdResult<Response> {
    let pubkey = ORACLE_PUBKEY.load(deps.storage)?;
    let key_type = ORACLE_PUBKEY_TYPE.load(deps.storage)?;

    let parsed = parse_key_type(&key_type)
        .ok_or_else(|| StdError::generic_err("stored oracle_key_type invalid"))?;

    let result = Sha256::digest(&data).to_vec();

    let verified = match parsed {
        "secp256k1" => deps.api.secp256k1_verify(&result, signature.as_slice(), pubkey.as_slice())
            .map_err(|e| StdError::generic_err(format!("secp256k1 verify error: {}", e)))?,
        // Extend later for "ed25519"
        _ => false,
    };

    if !verified {
        return Err(StdError::generic_err("signature verification failed"));
    }

    ORACLE_DATA.save(deps.storage, &data)?;

    let event = Event::new("oracle_data_update")
        .add_attribute("action", "oracle_data_update")
        .add_attribute("sender", info.sender.to_string())
        .add_attribute("data", data);

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
            let data = ORACLE_DATA.may_load(deps.storage)?;
            to_binary(&OracleDataResponse { data })
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
        QueryMsg::GetBalance { address: _ } => {
            // Stub: you can implement actual balance lookup
            to_binary(&Uint128::zero())
        }
        QueryMsg::CheckAML { wallet } => {
            let flagged = query_aml_status(deps, wallet)?;
            to_binary(&flagged)
        }
    }
}

/// -------------------- AML Helper --------------------
/// -------------------- AML Helper --------------------
/// -------------------- AML Helper --------------------
pub fn query_aml_status(deps: Deps, wallet: String) -> StdResult<(bool, String)> {
    // Load last oracle update
    let data = ORACLE_DATA.may_load(deps.storage)?;

    if let Some(msg) = data {
        // Expecting format: "wallet1:true:reason1,wallet2:false:,wallet3:true:reason3"
        for entry in msg.split(',') {
            let mut parts = entry.splitn(2, ':'); // split into 2 parts: wallet, reason
            if let (Some(w), Some(reason)) = (parts.next(), parts.next()) {
                if w == wallet {
                    return Ok((true, reason.to_string()));
                }
            }
        }
    }

    // Default to not flagged, empty reason
    Ok((false, "No suspicious activity".to_string()))
}

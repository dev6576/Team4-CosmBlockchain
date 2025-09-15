use cosmwasm_std::{
    entry_point, to_binary, Addr, BankMsg, Binary, Coin, Deps, DepsMut, Env, Event, MessageInfo, Response, StdError, StdResult
};
use cw2::set_contract_version;
use sha2::{Digest, Sha256};

use crate::msg::{ExecuteMsg, InstantiateMsg, OracleDataResponse, QueryMsg};
use crate::state::{ADMIN, ORACLE_DATA, ORACLE_PUBKEY, ORACLE_PUBKEY_TYPE, parse_key_type};

const CONTRACT_NAME: &str = "crates.io:oracle-contract";
const CONTRACT_VERSION: &str = env!("CARGO_PKG_VERSION");

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

#[entry_point]
pub fn execute(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    msg: ExecuteMsg,
) -> StdResult<Response> {
    match msg {
        ExecuteMsg::Send { recipient } => execute_send(deps, info, recipient),
        ExecuteMsg::OracleDataUpdate { data, signature } => {
            execute_oracle_update(deps, env, info, data, signature)
        }
        ExecuteMsg::UpdateOracle { new_pubkey, new_key_type } => {
            execute_update_oracle(deps, info, new_pubkey, new_key_type)
        }
    }
}

fn execute_send(
    deps: DepsMut,
    info: MessageInfo,
    recipient: String,
) -> StdResult<Response> {
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
        .add_event(event))
        
}

fn execute_oracle_update(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    data: String,
    signature: Binary,
) -> StdResult<Response> {
    let pubkey = ORACLE_PUBKEY.load(deps.storage)?;
    let key_type = ORACLE_PUBKEY_TYPE.load(deps.storage)?;

    let msg_bytes = data.as_bytes();
    let parsed = parse_key_type(&key_type)
        .ok_or_else(|| StdError::generic_err("stored oracle_key_type invalid"))?;

    let result = Sha256::digest(&data).to_vec();

    let verified = match parsed {
        "secp256k1" => deps.api.secp256k1_verify(&result, signature.as_slice(), pubkey.as_slice())
            .map_err(|e| StdError::generic_err(format!("secp256k1 verify error: {}", e)))?,
        // "ed25519" => deps.api.ed25519_verify(pubkey.as_slice(), msg_bytes, signature.as_slice())
        //     .map_err(|e| StdError::generic_err(format!("ed25519 verify error: {}", e)))?,
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

    Ok(Response::new()
        .add_event(event))
}

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

    Ok(Response::new()
        .add_event(event))
}

#[entry_point]
pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    use crate::msg::{AdminResponse, OracleDataResponse, OraclePubkeyResponse};

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
    }
}

use cosmwasm_std::{
    entry_point, to_binary, Addr, BankMsg, Binary, Coin, Deps, DepsMut,
    Env, Event, MessageInfo, Response, StdResult,
};
use cw2::set_contract_version;
use serde::{Deserialize, Serialize};
use cw_storage_plus::{Map, Item};

const CONTRACT_NAME: &str = "crates.io:aml-transfer";
const CONTRACT_VERSION: &str = env!("CARGO_PKG_VERSION");

// =====================
// MESSAGES
// =====================
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct InstantiateMsg {}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub enum ExecuteMsg {
    RequestTransfer { recipient: String, amount: Coin },
    OracleResponse {
        request_id: u64,
        approved: bool,
        flagged: bool,
        reason: String,
        risk_score: u64,
    },
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub enum QueryMsg {
    GetPendingTx { id: u64 },
    GetNextId {},
}

// =====================
// STATE
// =====================
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct PendingTx {
    pub sender: Addr,
    pub recipient: Addr,
    pub amount: Coin,
}

pub const PENDING_TX: Map<u64, PendingTx> = Map::new("pending");
// nxt_id: next transaction to execute (incremented on OracleResponse)
pub const NEXT_ID: Item<u64> = Item::new("next_id");
// index: last written transaction id (incremented on RequestTransfer)
pub const INDEX: Item<u64> = Item::new("index");

// =====================
// INSTANTIATE
// =====================
#[entry_point]
pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    _info: MessageInfo,
    _msg: InstantiateMsg,
) -> StdResult<Response> {
    set_contract_version(deps.storage, CONTRACT_NAME, CONTRACT_VERSION)?;
    NEXT_ID.save(deps.storage, &1)?;
    INDEX.save(deps.storage, &1)?;
    Ok(Response::default())
}

// =====================
// EXECUTE
// =====================
#[entry_point]
pub fn execute(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    msg: ExecuteMsg,
) -> StdResult<Response> {
    match msg {
        ExecuteMsg::RequestTransfer { recipient, amount } => {
            request_transfer(deps, env, info, recipient, amount)
        }
        ExecuteMsg::OracleResponse {
            request_id,
            approved,
            flagged,
            reason,
            risk_score,
        } => oracle_response(deps, env, request_id, approved, flagged, reason, risk_score),
    }
}

fn request_transfer(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    recipient: String,
    amount: Coin,
) -> StdResult<Response> {
    // Get current index
    let mut index = INDEX.load(deps.storage)?;
    // Save tx at current index
    let tx = PendingTx {
        sender: info.sender.clone(),
        recipient: deps.api.addr_validate(&recipient)?,
        amount,
    };
    PENDING_TX.save(deps.storage, index, &tx)?;

    let event = Event::new("aml_check_requested")
        .add_attribute("index", index.to_string())
        .add_attribute("sender", info.sender.to_string())
        .add_attribute("recipient", recipient)
        .add_attribute("amount", tx.amount.amount.to_string())
        .add_attribute("denom", tx.amount.denom);

    // increment index only (next_id not affected yet)
    INDEX.save(deps.storage, &(index + 1))?;

    Ok(Response::new().add_event(event))
}

fn oracle_response(
    deps: DepsMut,
    _env: Env,
    request_id: u64,
    approved: bool,
    flagged: bool,
    reason: String,
    risk_score: u64,
) -> StdResult<Response> {
    let tx = PENDING_TX.may_load(deps.storage, request_id)?;
    if tx.is_none() {
        return Ok(Response::new().add_attribute("error", "no such request_id"));
    }
    let tx = tx.unwrap();

    // Remove tx from pending table
    PENDING_TX.remove(deps.storage, request_id);

    // Increment NEXT_ID since this tx has been processed
    let mut nxt_id = NEXT_ID.load(deps.storage)?;
    if nxt_id == request_id {
        NEXT_ID.save(deps.storage, &(nxt_id + 1))?;
    }

    if approved {
        let bank_msg = BankMsg::Send {
            to_address: tx.recipient.to_string(),
            amount: vec![tx.amount.clone()],
        };
        let event = Event::new("aml_approved")
            .add_attribute("request_id", request_id.to_string())
            .add_attribute("sender", tx.sender.to_string())
            .add_attribute("recipient", tx.recipient.to_string())
            .add_attribute("amount", tx.amount.amount.to_string())
            .add_attribute("denom", tx.amount.denom)
            .add_attribute("flagged", flagged.to_string())
            .add_attribute("reason", reason)
            .add_attribute("risk_score", risk_score.to_string());

        Ok(Response::new().add_message(bank_msg).add_event(event))
    } else {
        let event = Event::new("aml_denied")
            .add_attribute("request_id", request_id.to_string())
            .add_attribute("sender", tx.sender.to_string())
            .add_attribute("recipient", tx.recipient.to_string())
            .add_attribute("amount", tx.amount.amount.to_string())
            .add_attribute("denom", tx.amount.denom)
            .add_attribute("flagged", flagged.to_string())
            .add_attribute("reason", reason)
            .add_attribute("risk_score", risk_score.to_string());

        Ok(Response::new().add_event(event))
    }
}

// =====================
// QUERY
// =====================
#[entry_point]
pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::GetPendingTx { id } => to_binary(&query_pending_tx(deps, id)?),
        QueryMsg::GetNextId {} => to_binary(&query_next_id(deps)?),
    }
}

fn query_pending_tx(deps: Deps, id: u64) -> StdResult<Option<PendingTx>> {
    PENDING_TX.may_load(deps.storage, id)
}

fn query_next_id(deps: Deps) -> StdResult<u64> {
    NEXT_ID.load(deps.storage)
}

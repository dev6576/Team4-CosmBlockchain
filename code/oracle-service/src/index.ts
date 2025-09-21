import { DirectSecp256k1Wallet } from "@cosmjs/proto-signing";
import { SigningCosmWasmClient, ExecuteResult } from "@cosmjs/cosmwasm-stargate";
import { Coin } from "@cosmjs/amino";
import axios from "axios";
import { GasPrice, calculateFee } from "@cosmjs/stargate";
import * as dotenv from "dotenv";

import { NewOracleClient, OracleResponseParams, PendingTx } from "./sdk/OracleClient";



dotenv.config();

// ==== CONFIG from .env ====
const RPC_ENDPOINT = process.env.RPC_URL!;
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS!;
const AML_API = process.env.AML_API!;
const ORACLE_PRIVKEY = process.env.ORACLE_PRIVKEY!;
const POLL_INTERVAL_MS = 10_000; // 10 seconds
const PREFIX = "wasm"; // adjust for your chain prefix
const gasPrice = GasPrice.fromString("0.025ustake"); 
const defaultFee = calculateFee(1, gasPrice); // optional fixed fee

// ==== INITIALIZE CLIENT ====
async function initOracleClient(): Promise<NewOracleClient> {
  const privKeyBytes = Uint8Array.from(Buffer.from(ORACLE_PRIVKEY, "hex"));
  const wallet = await DirectSecp256k1Wallet.fromKey(privKeyBytes, PREFIX);
  const [firstAccount] = await wallet.getAccounts();

  const signingClient = await SigningCosmWasmClient.connectWithSigner(RPC_ENDPOINT, wallet,  { gasPrice });
  const oracleClient = new NewOracleClient(signingClient, firstAccount.address, CONTRACT_ADDRESS);
  return oracleClient;
}

// ==== AML CHECK FUNCTION ====
async function performAmlCheck(tx: PendingTx): Promise<OracleResponseParams> {
  try {
    const response = await axios.post(AML_API, {
      sender: tx.sender,
      recipient: tx.recipient,
      amount: tx.amount.amount,
      denom: tx.amount.denom,
    });

    const data = response.data;
    console.info("AML API call finished");
    return {
      request_id: 0, // will set later
      approved: data.approved,
      flagged: data.flagged,
      reason: data.reason || "",
      risk_score: data.risk_score || 0,
    };
  } catch (err) {
    console.error("AML API call failed:", err);
    return {
      request_id: 0,
      approved: false,
      flagged: true,
      reason: "AML API error",
      risk_score: 100,
    };
  }
}

// ==== PROCESS NEXT PENDING TX ONLY ====
async function processNextTransaction(oracleClient: NewOracleClient) {
  try {
    const nextIdRaw = await oracleClient.getNextId();
    console.log("getNextId response:", nextIdRaw);

    if (!nextIdRaw || nextIdRaw <= 0) {
      console.log("No pending transactions.");
      return;
    }

    const tx = await oracleClient.getPendingTx(nextIdRaw);
    console.log(`getPendingTx(${nextIdRaw}) response:`, tx);

    if (!tx) {
      console.log(`No transaction found for id=${nextIdRaw}`);
      return;
    }

    console.log(`Processing pending tx id=${nextIdRaw} sender=${tx.sender} recipient=${tx.recipient}`);

    // Run AML check
    const amlResult = await performAmlCheck(tx);
    amlResult.request_id = nextIdRaw;
    console.log(amlResult)
    // Send OracleResponse
    const res: ExecuteResult = await oracleClient.executeOracleResponse(amlResult);
    console.log(`OracleResponse sent for tx id=${nextIdRaw}:`, res.transactionHash);
  } catch (err) {
    console.error("Error processing next transaction:", err);
  }
}

// ==== POLLING LOOP ====
async function startPolling() {
  const oracleClient = await initOracleClient();
  console.log("Oracle client initialized. Starting polling...");

  setInterval(() => {
    processNextTransaction(oracleClient);
  }, POLL_INTERVAL_MS);
}

// ==== START ====
startPolling();

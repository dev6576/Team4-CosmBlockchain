import { OracleClient, OracleQueryClient } from "./sdk/Oracle.client"
import { DirectSecp256k1Wallet } from "@cosmjs/proto-signing";
import { fromHex } from "@cosmjs/encoding";
import { GasPrice } from "@cosmjs/stargate";
import * as dotenv from "dotenv"

import { CosmWasmClient, SigningCosmWasmClient } from "@cosmjs/cosmwasm-stargate"

dotenv.config();

const getSignerFromPriKey = async (priv: any) => {
    return DirectSecp256k1Wallet.fromKey(fromHex(priv), "wasm");
};

export async function getQueryClient() {
    const sc = await CosmWasmClient.connect(process.env.RPC_URL!);
    const dqc = new OracleQueryClient(sc, process.env.CONTRACT_ADDRESS!);
    return dqc;
}

export async function getClient() {
    const signer = await getSignerFromPriKey(process.env.ORACLE_PRIVKEY!);
    const publicAddress = (await signer.getAccounts())[0].address;
    const ssc = await SigningCosmWasmClient.connectWithSigner(process.env.RPC_URL!, signer, { gasPrice: GasPrice.fromString("0ustake") });
    const oracle_client = new OracleClient(ssc, publicAddress, process.env.CONTRACT_ADDRESS!);
    return oracle_client;
}
import { OracleClient, OracleDataEntry } from "./sdk/Oracle.client";
import { fromHex, toUtf8 } from "@cosmjs/encoding";
import { Secp256k1, sha256 } from "@cosmjs/crypto";
import * as dotenv from "dotenv";
import { getQueryClient, getClient } from "./setup";
import asyncHandler from "express-async-handler";

dotenv.config();

let oracle_client: OracleClient;
let query_client: any;
let priv_key: Uint8Array;

// ==== Get Oracle Data ====
const getOracleData = asyncHandler(async (req, res, next) => {
    try {
        const data = await query_client.getOracleData();
        res.json(data);
    } catch (error) {
        next(error);
    }
});

// ==== Update Oracle Data ====
const updateOracleData = asyncHandler(async (req, res, next) => {
    try {
        const { msg } = req.body;
        if (!msg || !Array.isArray(msg)) {
            res.status(400).json({ error: "msg must be an array of OracleDataEntry" });
            return;
        }

        const msgData: OracleDataEntry[] = msg;

        // Canonicalize (wallet, reason, risk_score)
        const canonicalData = msgData.map(d => [
            d.wallet,
            d.reason,
            d.risk_score ?? 0,
        ]);

        // Serialize + hash
        const msgBytes = toUtf8(JSON.stringify(canonicalData));
        const msgHash = sha256(msgBytes);

        // Sign with secp256k1
        const signature = await Secp256k1.createSignature(msgHash, priv_key);
        const signatureBytes = new Uint8Array(signature.toFixedLength());
        const signatureBase64 = Buffer.from(signatureBytes).toString("base64");

        const result = await oracle_client.oracleDataUpdate({
            data: msgData,
            signature: signatureBase64,
        });

        res.json({ success: true, result });
    } catch (error) {
        next(error);
    }
});

// ==== Delete Oracle Entry ====
const deleteOracleEntry = asyncHandler(async (req, res, next) => {
    try {
        const { wallet } = req.body;
        if (!wallet) {
            res.status(400).json({ error: "wallet is required" });
            return;
        }

        // Use raw execute to call delete_wallet
        const result = await oracle_client.client.execute(
            oracle_client.sender,
            oracle_client.contractAddress,
            { delete_wallet: { wallet } },
            "auto"
        );

        res.json({ status: "deleted", wallet });
    } catch (error) {
        next(error);
    }
});

// ==== Initialize Clients ====
(async () => {
    const priv_hex = process.env.ORACLE_PRIVKEY!;
    if (!priv_hex) throw new Error("ORACLE_PRIVKEY missing in .env");

    priv_key = fromHex(priv_hex);
    oracle_client = await getClient();
    query_client = await getQueryClient();
})();

export {
    getOracleData,
    updateOracleData,
    deleteOracleEntry
};

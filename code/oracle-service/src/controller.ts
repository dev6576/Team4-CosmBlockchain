import { OracleClient, OracleQueryClient, OracleDataEntry } from "./sdk/Oracle.client";
import { fromHex, toUtf8 } from "@cosmjs/encoding";
import { Secp256k1, sha256 } from "@cosmjs/crypto";
import * as dotenv from "dotenv";
import { getQueryClient, getClient } from "./setup";
import asyncHandler from "express-async-handler";
import { fromBase64 } from "@cosmjs/encoding";

dotenv.config();

let oracle_client: OracleClient;
let query_client: OracleQueryClient;
let priv_key: string;

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

        // Parse input JSON (objects with wallet + reason)
        const msgData: OracleDataEntry[] = msg;

        // Canonicalize into array-of-arrays for signing
        const canonicalData = msgData.map(d => [d.wallet, d.reason]);

        // Serialize + hash
        const msgBytes = toUtf8(JSON.stringify(canonicalData));
        const msgHash = sha256(msgBytes);

        // Sign with secp256k1 (raw r||s format, 64 bytes)
        const signature = await Secp256k1.createSignature(msgHash, fromHex(priv_key));
        const rs = signature.toFixedLength(); // <-- this gives exactly 64 bytes
        const signatureBase64 = Buffer.from(rs).toString("base64");

        console.log("Canonical data (signed):", JSON.stringify(canonicalData));
        console.log("Signature (base64 r||s):", signatureBase64);
        

        // Send update to oracle contract
        const result = await oracle_client.oracleDataUpdate({
        data: msgData,
        signature: signatureBase64, // ✅ matches string type
        });

        console.log("Oracle update result:", result);
        res.sendStatus(200);
    } catch (error) {
        next(error);
    }
});

// ==== Initialize Clients ====
(async () => {
    priv_key = process.env.ORACLE_PRIVKEY!;
    if (!priv_key) {
        throw new Error("ORACLE_PRIVKEY missing in .env");
    }
    oracle_client = await getClient();
    query_client = await getQueryClient();
})();

export {
    getOracleData,
    updateOracleData
};

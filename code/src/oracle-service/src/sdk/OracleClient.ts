import { SigningCosmWasmClient, ExecuteResult, CosmWasmClient } from "@cosmjs/cosmwasm-stargate";
import { Coin, StdFee } from "@cosmjs/amino";

export interface PendingTx {
  sender: string;
  recipient: string;
  amount: Coin;
}

export interface OracleResponseParams {
  request_id: number;
  approved: boolean;
  flagged: boolean;
  reason: string;
  risk_score: number;
}

export interface NewOracleReadOnlyInterface {
  contractAddress: string;
  client: CosmWasmClient;
  getPendingTx: (id: number) => Promise<PendingTx | null>;
  getNextId: () => Promise<number>;
}

export class NewOracleQueryClient implements NewOracleReadOnlyInterface {
  client: CosmWasmClient;
  contractAddress: string;

  constructor(client: CosmWasmClient, contractAddress: string) {
    this.client = client;
    this.contractAddress = contractAddress;
  }

  getPendingTx = async (id: number): Promise<PendingTx | null> => {
    try {
      // Updated query message to match Rust contract
      return await this.client.queryContractSmart(this.contractAddress, {
        GetPendingTx: { id },
      });
    } catch {
      return null;
    }
  };

  getNextId = async (): Promise<number> => {
    const res = await this.client.queryContractSmart(this.contractAddress, {
      GetNextId: {},
    });
    return res; // the contract returns just a number
  };
}

export interface NewOracleInterface extends NewOracleReadOnlyInterface {
  sender: string;
  client: SigningCosmWasmClient;
  executeRequestTransfer: (
    params: { recipient: string; amount: Coin },
    fee?: number | StdFee | "auto",
    memo?: string
  ) => Promise<ExecuteResult>;
  executeOracleResponse: (
    params: OracleResponseParams,
    fee?: number | StdFee | "auto",
    memo?: string
  ) => Promise<ExecuteResult>;
}

export class NewOracleClient extends NewOracleQueryClient implements NewOracleInterface {
  client: SigningCosmWasmClient;
  sender: string;
  contractAddress: string;

  constructor(client: SigningCosmWasmClient, sender: string, contractAddress: string) {
    super(client, contractAddress);
    this.client = client;
    this.sender = sender;
    this.contractAddress = contractAddress;
  }

  executeRequestTransfer = async (
    { recipient, amount }: { recipient: string; amount: Coin },
    fee: number | StdFee | "auto" = "auto",
    memo?: string
  ): Promise<ExecuteResult> => {
    return await this.client.execute(
      this.sender,
      this.contractAddress,
      { RequestTransfer: { recipient, amount } },
      fee,
      memo
    );
  };

  executeOracleResponse = async (
    params: OracleResponseParams,
    fee: number | StdFee | "auto" = "auto",
    memo?: string
  ): Promise<ExecuteResult> => {
    return await this.client.execute(
      this.sender,
      this.contractAddress,
      {
        OracleResponse: {
          request_id: params.request_id,
          approved: params.approved,
          flagged: params.flagged,
          reason: params.reason,
          risk_score: params.risk_score,
        },
      },
      fee,
      memo
    );
  };
}

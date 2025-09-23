
## 🧪 Smart Contract Testing (CosmWasm)

### Request Transfer

```json
{
  "RequestTransfer": {
    "recipient": "wasm1ga4d4tsxrk6na6ehttwvdfmn2ejy4gwfxpt2m7",
    "amount": {
      "denom": "ustake",
      "amount": "1000"
    }
  }
}
```

### Oracle Response

Approved transfer:

```json
{
  "OracleResponse": {
    "request_id": 3,
    "approved": true,
    "flagged": false,
    "reason": "",
    "risk_score": 0
  }
}
```

Rejected transfer:

```json
{
  "OracleResponse": {
    "request_id": 3,
    "approved": false,
    "flagged": true,
    "reason": "OFAC sanctioned sender",
    "risk_score": 10
  }
}
```

### Additional Queries

* **GetPendingTx** → Returns transaction info from a given ID

```json
{ "GetPendingTx": { "id": 7 } }
```

* **GetNextId** → Returns the next transaction ID to be checked

```json
{ "GetNextId": {} }
```

### AML-check REST Endpoint (PowerShell)

```powershell
$body = @{
    sender    = "wasm1sse6pdmn5s7epjycxadjzku4qfgs604cgur6me"
    recipient = "wasm1ga4d4tsxrk6na6ehttwvdfmn2ejy4gwfxpt2m7"
    amount    = "1000"
    denom     = "ustake"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:6000/aml-check" `
                  -Method Post `
                  -Headers @{ "Content-Type" = "application/json" } `
                  -Body $body
```

You can modify the "sender", "recipient", "amount", and "denom" in the above tests to see what the different responses from the AML endpoint would look like.
---

## 🛠 MCP Integration

The AML Wallet Graph MCP server exposes tools that can be used from ChatGPT/Claude or any MCP-compatible client.

### Setup & Start MCP

1. Ensure `wallet_graph.pkl` from `code\src\wallet-Graph` is copied into the MCP folder (`code\src\mcp-layer`) **before starting**.
2. Start the MCP server (Claude config example):

```json
{
  "mcpServers": {
    "AML-Wallet-Graph-MCP": {
      "command": "D:\\GitHub\\Team4-CosmBlockchain\\code\\src\\oracle-service\\venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "uv",
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "D:\\GitHub\\Team4-CosmBlockchain\\code\\src\\mcp-layer\\aml_mcp.py"
      ]
    }
  }
}
```
The tests for the mcp are manual, so interact with the agent to ask wallet information, generate graph, etc.

# 🚀 Team4-CosmBlockchain

This project is an **end-to-end AML monitoring system** for blockchain transactions. From the time a transaction is initiated on-chain, the system:

1. Receives a transfer request from a smart contract.
2. Performs automated AML checks via the Oracle and AML server (including sanctions list checks, heuristic analyses, and ML-based risk scoring).
3. Stores transaction and wallet information in a database.
4. Allows support/data-analysts to analyze wallet and subgraph data using interactive graph visualizations and MCP tools to detect potential high-risk or suspicious activity.

This ensures continuous monitoring and supports both automated and human-led compliance workflows.

This README.md is a high level overview of the system. If you require more details, find them in artifacts/arch/solution.pptx

The project is based on [wfblockchain/wfHackathon](https://github.com/wfblockchain/wfHackathon), but extended with AML checks, an oracle service, a data-helper scheduler system, graph visualization tools, and MCP integration. Use the above repo to follow for the initial setup. Refer to this only once the blockchain is up and running, and adding the smart contract. Post that, from the oracle-service setup, refer to this.

Run the below setup sequentially to have everything running correctly.

---

## 📂 Database Setup

All AML-related tables are written to the **`aml_data`** database.

### 1. Start PostgreSQL in Docker (modified for local host access)

```powershell
docker run -d --name postgres_new `
  -v ${PWD}\data:/var/lib/postgresql/data `
  -v ${PWD}\db-scripts:/docker-entrypoint-initdb.d `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_DB=new_aml_db `
  -e POSTGRES_PASSWORD=password `
  -p 5433:5432 postgres:15
```

### 2. Load schema

```powershell
docker cp data-helper\sql-scripts\create_flagged_wallets_table.sql postgres_new:/create_flagged_wallets_table.sql

docker exec -i postgres_new psql -U postgres -d aml_db -f /create_flagged_wallets_table.sql
```

✅ The **SDN/OFAC list** is automatically fetched and refreshed by scheduled scripts.

---

## ⚙️ Local Setup

### Python Dependencies

```bash
pip install flask fastmcp psycopg2 networkx pyvis apscheduler
```

---

# 📊 Graph Visualization

⚠️ **Important Note on First-Time Setup**  
By default, `graph_builder.py` includes **risk propagation** logic:

```python
for flagged in tqdm(flagged_nodes, desc="Propagating from flagged wallets"):
    lengths = nx.single_source_shortest_path_length(G.to_undirected(), flagged, cutoff=3)
    for node, dist in lengths.items():
        if node in flagged_nodes:
            continue
        incremental_risk = MAX_RISK / dist
        risk_scores[node] = min(MAX_RISK, risk_scores.get(node,0) + incremental_risk)
```
![Graph](https://github.com/dev6576/Team4-CosmBlockchain/blob/main/artifacts/arch/Graph.png)
This step spreads risk scores across the graph but can take **many hours** during the initial build.  

👉 To speed up setup, you may **comment out this block** in `graph_builder.py`.

- **With propagation** → realistic risk scoring, but **very slow** (can take hours for initial setup).  
- **Without propagation** → graph builds in **minutes**, but no propagated risks.

---

## Run the Graph Builder

To visualize the wallet transaction graph, run:

```powershell
python code\src\wallet-Graph\graph_builder.py
```

This generates an interactive graph where:

* **Nodes** represent wallets. Node color indicates risk: purple = root wallet, red = high risk, blue = low risk.
* **Edges** represent transactions, with attributes such as amount and timestamp.
* Neighborhood subgraphs can be generated to explore wallet connections up to N hops.

The full transaction graph is stored in `wallet_graph.pkl` and can be used by the MCP server to generate subgraphs on demand.

---

## 🔗 Oracle Service

The oracle service listens for events on-chain (e.g., AML check requests) and responds back with a risk decision. Be sure to update the .env with the correct wallet address.

Start the oracle service:

```powershell
cd code\src\oracle-service
npm install @cosmjs/proto-signing @cosmjs/cosmwasm-stargate @cosmjs/amino @cosmjs/stargate axios dotenv
npm install --save-dev @types/node @types/axios @types/dotenv
npx ts-node src/index.ts
```

---



## 🕒 Scheduler Service

This is not needed for a test, it's required if you're running this system over a long period of time so that data does not become stale.

We use **APScheduler** to run periodic heuristic and sanctions checks. The scheduler can be started manually:

```powershell
python code\src\data-helper\python-scripts\scheduler.py
```

### Scheduled Tasks

| Script                  | Purpose                          | Frequency      |
| ----------------------- | -------------------------------- | -------------- |
| `Mixer_check.py`        | Detect potential mixing activity | Every 6 hours  |
| `Peeling_chains.py`     | Track peeling chain transactions | Every 6 hours  |
| `Structuring_check.py`  | Detect structuring patterns      | Every 6 hours  |
| `OFACSanctionScript.py` | Update OFAC sanctions list       | Every 24 hours |
| `third_party_data.py`   | Ingest external data sources     | Every 12 hours |

The scheduler ensures the AML system is continuously updated with the latest heuristics and sanctions data.

---


## 🧠 ML Layer

The AML system uses a **Graph Neural Network (GNN) / DNN** for risk classification.

### Features Extracted per Wallet Node

* Transaction frequency and amounts
* Counterparty diversity
* In-degree and out-degree
* Graph centrality measures (betweenness, closeness)
* Clustering coefficient
* Historical risk score aggregation

The current model has a risk score of 98.04%

### Model Workflow
![Architecture](https://github.com/dev6576/Team4-CosmBlockchain/blob/main/artifacts/arch/Architecture.png)
1. Load transaction graph from database.
2. Extract node features and construct adjacency matrix.
3. Train GNN/DNN on labeled historical data.
4. Evaluate and classify wallets as **low, medium, or high risk**.
5. Store predictions in database for the AML oracle to use in decision-making.

Run this:

```powershell
python code\src\ml-layer\ml_model.py
```

## 🧪 AML Check Server

The AML check server handles direct AML verification requests via REST API.

Start the AML check server:

```powershell
python code\src\oracle-service\aml_check.py
```

This will launch a server on `http://127.0.0.1:6000/aml-check` where AML verification requests can be sent.

---

### Transaction Flow

![Transaction Flow](https://github.com/dev6576/Team4-CosmBlockchain/blob/main/artifacts/arch/TransactionFlow.png)

This flow shows how a transfer request triggers an AML check, how the oracle queries the ML model and sanctions lists, and how the response is written back on-chain.

---

## 🧪 Smart Contract Testing (CosmWasm)
Run the next two jsons on the execute entry in cosmwasm.
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

You can monitor the logs of the oracle-service to see the polling in action, or run the below two responses to see how the blockchain handles different AML check responses differently.

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

### Available MCP Tools

1. **`db_schema()`** → Returns the database schema (tables and columns).
2. **`db_query(sql: str)`** → Run any SQL query on the AML database; returns results as JSON.
3. **`build_wallet_graph(wallet_id: str, max_hops: int = 2, output_file: str = "wallet_subgraph.html")`** → Extracts a subgraph for a wallet and generates an interactive HTML visualization.

You can test MCP tools from ChatGPT or Claude once the server is running by invoking queries like `db_schema()` or `build_wallet_graph(wallet_id='wasm1...')`.

---

## ✅ Summary

This system combines:

* Blockchain smart contracts for transaction monitoring.
* An **Oracle Service** bridging AML APIs and the blockchain.
* **AML Check Server** for REST-based AML verification requests.
* **Scheduler** to update sanctions lists and heuristics continuously.
* **Graph Analytics** for wallet clustering and ML anomaly detection.
* **MCP server** for programmatic access to AML data and wallet subgraphs.

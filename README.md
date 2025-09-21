# 🚀 Team4-CosmBlockchain

This project is based on [wfblockchain/wfHackathon](https://github.com/wfblockchain/wfHackathon), but extended with AML checks, an oracle service, a data-helper scheduler system, and graph visualization tools.

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
The above script is then later loaded with the initial data load from wfblockchain/wfHackathon, but with the modified scripts in this repo.

### 2. Load schema

```powershell
docker cp data-helper\sql-scripts\create_flagged_wallets_table.sql postgres_new:/create_flagged_wallets_table.sql

docker exec -i postgres_new psql -U postgres -d aml_db -f /create_flagged_wallets_table.sql
```

✅ The **SDN/OFAC list** is automatically fetched and refreshed by scheduled scripts.

---

## ⚙️ Local Setup

### Install Flask
```bash
pip install flask
```

---

## 🔗 Oracle Service

The oracle service listens for events on-chain (e.g., AML check requests) and responds back with a risk decision.

Start the oracle service:

```powershell
cd code\oracle-service
npx ts-node src/index.ts
```

---

## 🕒 Scheduler Service

We use **APScheduler** to run periodic heuristic and sanctions checks.

Run the scheduler:
```powershell
python code\data-helper\python-scripts\scheduler.py
```

### Scheduling Frequencies
- **Heuristic checks** (`Mixer_check.py`, `Peeling_chains.py`, `Structuring_check.py`) → every **6 hours**
- **OFAC sanctions list update** (`OFACSanctionScript.py`) → every **24 hours**
- **Third-party data ingestion** (`third_party_data.py`) → every **12 hours**

---

## 🧠 AML Server

The AML service can also be run directly for checks:

```powershell
python code\oracle-service\aml_check.py
```

---

## 📊 Graph Visualization

To visualize the wallet transaction graph, run:

```powershell
python code\wallet-Graph\graph_builder.py
```

This will load transaction data from the database, construct the graph, and help detect suspicious wallet clusters.

Open wallet_graph.html to view the interactive graph.
---

## 🧪 Sample Contract Queries

Once the blockchain is running, you can test with:

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
The orace-service would pick this up, conduct the AML check, and accept/reject the transaction.

Other Smart contract queries:
### Get Pending Transaction
```json
{
  "GetPendingTx": {
    "id": 1
  }
}
```

### Get Next ID
```json
{
  "GetNextId": {}
}
```

---

## 🧠 How the ML Model Works

1. **Graph Construction**  
   Transactions are ingested into a wallet graph (using `graph_builder.py`). Nodes represent wallets and edges represent transactions.

2. **Feature Extraction**  
   Each wallet node is enriched with features such as transaction frequency, amounts, counterparty diversity, and graph centrality.

3. **Model Training**  
   The ML model (Graph Neural Network / DNN) is trained on labeled data to classify wallets as **low risk, medium risk, or high risk**.

4. **AML Oracle Flow**  
   - The smart contract requests an AML check on transfer.  
   - The Oracle fetches features, queries the ML model + sanctions lists, and returns a **risk classification**.  
   - The decision is stored on-chain and can block or flag suspicious transfers.

---

## ✅ Summary

This extended system combines:
- Blockchain smart contracts for transaction monitoring.
- An **Oracle Service** to bridge AML APIs and the blockchain.
- A **Scheduler** to keep sanctions lists and heuristic checks updated.
- **Graph Analytics** for wallet clustering and ML-based anomaly detection.

---

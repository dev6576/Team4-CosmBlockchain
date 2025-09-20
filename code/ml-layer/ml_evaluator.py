# D:\GitHub\Team4-CosmBlockchain\code\ml-layer\api_wallet_risk.py

import os
import pickle
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import networkx as nx
import numpy as np
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder

# ==== Paths ====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_PICKLE = os.path.join(BASE_DIR, "..", "wallet-Graph", "wallet_graph.pkl")
MODEL_PATH = os.path.join(BASE_DIR, "gnn_model.pt")

# ==== DB Config ====
DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5433
}

# ==== Load trained model & graph ====
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class GCN(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim=128, output_dim=11, dropout=0.3):
        super(GCN, self).__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.fc = torch.nn.Linear(hidden_dim, output_dim)
        self.dropout = dropout

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.fc(x)
        return x

print("[INFO] Loading graph pickle...")
with open(GRAPH_PICKLE, "rb") as f:
    full_graph = pickle.load(f)

print("[INFO] Loading trained GCN model...")
# We'll determine input_dim dynamically after feature extraction
input_dim = 13 + len(set(nx.get_node_attributes(full_graph, "blockchain").values()))  # numeric + blockchain one-hot
model = GCN(input_dim=input_dim)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()

# ==== FastAPI setup ====
app = FastAPI(title="Wallet Risk Scoring API")

class WalletRequest(BaseModel):
    wallet_address: str

# ==== Helper to build subgraph features ====
def build_subgraph_features(wallet_address, G, max_hops=2):
    if wallet_address not in G:
        return None

    # BFS to get connected nodes
    nodes = set([wallet_address])
    frontier = [wallet_address]
    for _ in range(max_hops):
        new_frontier = set()
        for n in frontier:
            neighbors = list(G.successors(n)) + list(G.predecessors(n))
            for nb in neighbors:
                if nb not in nodes:
                    nodes.add(nb)
                    new_frontier.add(nb)
        frontier = new_frontier

    subG = G.subgraph(nodes).copy()

    # Build node features
    node_features = []
    node_map = {}
    blockchain_types = []
    for idx, (node, data) in enumerate(subG.nodes(data=True)):
        degree = subG.degree(node)
        in_degree = subG.in_degree(node) if hasattr(subG, "in_degree") else degree
        out_degree = subG.out_degree(node) if hasattr(subG, "out_degree") else degree

        incoming_count = data.get("incoming_count", 0)
        outgoing_count = data.get("outgoing_count", 0)
        total_sent = data.get("total_sent", 0)
        total_received = data.get("total_received", 0)
        avg_fee = data.get("avg_fee", 0)
        tx_volume = incoming_count + outgoing_count
        avg_sent = total_sent / (outgoing_count + 1e-6)
        avg_received = total_received / (incoming_count + 1e-6)

        # Neighbor aggregates
        neighbors = list(subG.successors(node)) + list(subG.predecessors(node))
        neighbor_risks = [subG.nodes[n].get("risk_score", 0) for n in neighbors]
        neighbor_risk_mean = np.mean(neighbor_risks) if neighbor_risks else 0
        neighbor_risk_max = np.max(neighbor_risks) if neighbor_risks else 0

        node_features.append([
            degree, in_degree, out_degree,
            incoming_count, outgoing_count,
            total_sent, total_received,
            avg_fee, tx_volume, avg_sent, avg_received,
            neighbor_risk_mean, neighbor_risk_max
        ])

        blockchain_types.append([data.get("blockchain", "Unknown")])
        node_map[node] = idx

    # Encode blockchain one-hot
    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    blockchain_onehot = encoder.fit_transform(blockchain_types)

    # Combine features
    features = np.hstack([node_features, blockchain_onehot])
    features = torch.tensor(MinMaxScaler().fit_transform(features), dtype=torch.float)

    # Edge index
    edges = []
    for u, v in subG.edges():
        edges.append([node_map[u], node_map[v]])
    if len(edges) == 0:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
    else:
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    return Data(x=features, edge_index=edge_index, node_map=node_map)

# ==== API Endpoint ====
@app.post("/predict_wallet_risk")
def predict_wallet_risk(req: WalletRequest):
    wallet = req.wallet_address
    if wallet not in full_graph:
        return {"wallet_address": wallet, "risk_score": 0.0}

    sub_data = build_subgraph_features(wallet, full_graph, max_hops=2)
    sub_data = sub_data.to(device)
    with torch.no_grad():
        out = model(sub_data.x, sub_data.edge_index)
        # Get prediction for target wallet node
        node_idx = sub_data.node_map[wallet]
        risk_class = torch.argmax(out[node_idx]).item()
    return {"wallet_address": wallet, "risk_score": float(risk_class)}

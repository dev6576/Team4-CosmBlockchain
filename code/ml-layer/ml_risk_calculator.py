# ml_risk_calculator.py
import os
import pickle
import torch
import torch.nn.functional as F
import numpy as np
from torch_geometric.data import Data
from sklearn.preprocessing import MinMaxScaler
from torch_geometric.nn import GCNConv

# =====================
# Paths
# =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_PICKLE = os.path.join(BASE_DIR, "..", "wallet-Graph", "wallet_graph.pkl")
MODEL_PATH = os.path.join(BASE_DIR, "wallet_gcn_model.pth")

# =====================
# Load Graph
# =====================
print("[INFO] Loading wallet graph...")
with open(GRAPH_PICKLE, "rb") as f:
    full_graph = pickle.load(f)
print(f"[INFO] Wallet graph loaded: {len(full_graph.nodes())} nodes, {len(full_graph.edges())} edges")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Using device: {device}")

# =====================
# Minimal GCN Model
# =====================
class GCN(torch.nn.Module):
    def __init__(self, in_dim, hidden_dim=64, num_risk_classes=11, dropout=0.3):
        super(GCN, self).__init__()
        self.conv1 = GCNConv(in_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.fc_risk = torch.nn.Linear(hidden_dim, num_risk_classes)
        self.dropout = dropout

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)
        risk_out = self.fc_risk(x)
        return risk_out

# =====================
# Load Trained Model
# =====================
print("[INFO] Loading trained GCN model...")
checkpoint = torch.load(MODEL_PATH, map_location=device)
input_dim = 11  # Minimal numeric features
model = GCN(in_dim=input_dim).to(device)
model.load_state_dict(checkpoint["model_state"])
model.eval()
print("[INFO] Model loaded successfully!")

# =====================
# Helper: Build Subgraph Features
# =====================
def build_subgraph_features(wallet_address, G, max_hops=2):
    if wallet_address not in G:
        print(f"[WARN] Wallet {wallet_address} not found in graph")
        return None

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
    node_features = []
    node_map = {}

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

        neighbors = list(subG.successors(node)) + list(subG.predecessors(node))
        neighbor_risks = [subG.nodes[n].get("risk_score", 0) for n in neighbors]
        neighbor_risk_mean = np.mean(neighbor_risks) if neighbor_risks else 0
        neighbor_risk_max = np.max(neighbor_risks) if neighbor_risks else 0

        node_features.append([
            degree, in_degree, out_degree,
            incoming_count, outgoing_count,
            total_sent, total_received,
            avg_fee, tx_volume,
            neighbor_risk_mean, neighbor_risk_max
        ])
        node_map[node] = idx

    features = torch.tensor(MinMaxScaler().fit_transform(node_features), dtype=torch.float)
    edges = [[node_map[u], node_map[v]] for u, v in subG.edges()]
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous() if edges else torch.zeros((2,0), dtype=torch.long)

    return Data(x=features, edge_index=edge_index, node_map=node_map)

# =====================
# Evaluator Function
# =====================
def evaluate_transaction(sender, recipient, amount, max_hops=2):
    print(f"[INFO] Evaluating transaction: {sender} -> {recipient}, amount={amount}")
    results = {}

    for wallet in [sender, recipient]:
        if wallet not in full_graph:
            results[wallet] = {"risk_score": 0}
            continue

        data_sub = build_subgraph_features(wallet, full_graph, max_hops)
        if data_sub is None:
            results[wallet] = {"risk_score": 0}
            continue

        data_sub = data_sub.to(device)
        with torch.no_grad():
            risk_out = model(data_sub.x, data_sub.edge_index)
            idx = data_sub.node_map[wallet]
            risk_class = torch.argmax(risk_out[idx]).item()

        results[wallet] = {"risk_score": int(risk_class)}
        print(f"[INFO] Wallet {wallet}: Risk={risk_class}")

    return results

# =====================
# Example Usage
# =====================
if __name__ == "__main__":
    sender = "test1"
    recipient = "0xa07d75aacefd11b425af7181958f0f85c312f143"
    amount = 1000
    output = evaluate_transaction(sender, recipient, amount)
    print("[RESULT]", output)

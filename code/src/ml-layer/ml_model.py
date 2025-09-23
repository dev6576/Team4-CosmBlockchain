# wallet_gcn_model.py
import os
import pickle
import numpy as np
from tqdm import tqdm
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from sklearn.preprocessing import MinMaxScaler

# =====================
# Paths
# =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_PICKLE = os.path.join(BASE_DIR, "..", "wallet-Graph", "wallet_graph.pkl")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "wallet_gcn_model.pth")

# =====================
# Load Graph
# =====================
print("[INFO] Loading wallet graph...")
with open(GRAPH_PICKLE, "rb") as f:
    G = pickle.load(f)

nodes = list(G.nodes())
node_to_idx = {node: i for i, node in enumerate(nodes)}

# =====================
# Prepare Node Features & Labels
# =====================
print("[INFO] Preparing node features...")
node_features = []
risk_labels = []

for node in tqdm(nodes):
    data = G.nodes[node]

    # Minimal numeric features
    degree = G.degree(node)
    in_degree = G.in_degree(node) if hasattr(G, "in_degree") else degree
    out_degree = G.out_degree(node) if hasattr(G, "out_degree") else degree
    incoming_count = data.get("incoming_count", 0)
    outgoing_count = data.get("outgoing_count", 0)
    total_sent = data.get("total_sent", 0)
    total_received = data.get("total_received", 0)
    avg_fee = data.get("avg_fee", 0)
    tx_volume = incoming_count + outgoing_count

    # Neighbor risk aggregates
    neighbors = list(G.successors(node)) + list(G.predecessors(node))
    neighbor_risks = [G.nodes[n].get("risk_score", 0) for n in neighbors]
    neighbor_risk_mean = np.mean(neighbor_risks) if neighbor_risks else 0
    neighbor_risk_max = np.max(neighbor_risks) if neighbor_risks else 0

    node_features.append([
        degree, in_degree, out_degree,
        incoming_count, outgoing_count,
        total_sent, total_received,
        avg_fee, tx_volume,
        neighbor_risk_mean, neighbor_risk_max
    ])

    # Risk label
    risk_labels.append(data.get("risk_score", 0))

X = np.array(node_features, dtype=np.float64)
y_risk = np.array(risk_labels, dtype=np.int64)

# Scale numeric features
X = MinMaxScaler().fit_transform(X)

# =====================
# Prepare Edge Index
# =====================
edges = [[node_to_idx[u], node_to_idx[v]] for u, v in G.edges()]
edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous() if edges else torch.zeros((2, 0), dtype=torch.long)

# =====================
# PyG Data Object
# =====================
data = Data(
    x=torch.tensor(X, dtype=torch.float),
    edge_index=edge_index,
    y_risk=torch.tensor(y_risk, dtype=torch.long)
)

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
# Training Setup
# =====================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = GCN(in_dim=X.shape[1]).to(device)
data = data.to(device)

optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = torch.nn.CrossEntropyLoss()

# Train/test split
num_nodes = data.num_nodes
indices = np.arange(num_nodes)
train_idx = indices[:int(0.7 * num_nodes)]
test_idx = indices[int(0.7 * num_nodes):]

train_mask = torch.zeros(num_nodes, dtype=torch.bool)
train_mask[train_idx] = True
test_mask = torch.zeros(num_nodes, dtype=torch.bool)
test_mask[test_idx] = True

data.train_mask = train_mask
data.test_mask = test_mask

# =====================
# Training Loop
# =====================
print("[INFO] Training GCN...")
for epoch in range(1, 51):
    model.train()
    optimizer.zero_grad()
    risk_out = model(data.x, data.edge_index)
    loss = criterion(risk_out[data.train_mask], data.y_risk[data.train_mask])
    loss.backward()
    optimizer.step()

    model.eval()
    with torch.no_grad():
        pred_risk = risk_out[data.test_mask].argmax(dim=1)
        acc_risk = (pred_risk == data.y_risk[data.test_mask]).sum().item() / data.test_mask.sum().item()
    print(f"Epoch {epoch:02d}, Loss: {loss.item():.4f}, Test Risk Accuracy: {acc_risk*100:.2f}%")

# =====================
# Save Model
# =====================
torch.save({
    "model_state": model.state_dict()
}, MODEL_SAVE_PATH)
print(f"[INFO] Trained model saved to {MODEL_SAVE_PATH}")

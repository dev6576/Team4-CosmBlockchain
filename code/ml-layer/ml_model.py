# ml_model_gcn_wallets.py
import os
import pickle
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from tqdm import tqdm

# ==== Paths ====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_PATH = os.path.join(BASE_DIR, "..", "wallet-Graph", "wallet_graph.pkl")
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "gcn_model_wallets.pth")

# ==== Load Graph ====
print("[INFO] Loading wallet graph...")
with open(GRAPH_PATH, "rb") as f:
    G = pickle.load(f)

# ==== Map string node IDs to integers ====
node_to_idx = {node: i for i, node in enumerate(G.nodes())}
idx_to_node = {i: node for node, i in node_to_idx.items()}

# ==== Extract Features and Labels ====
print("[INFO] Extracting features...")
X = []
y = []

for node in tqdm(G.nodes()):  # ensure same order as node_to_idx
    data = G.nodes[node]
    degree = G.degree(node)
    in_degree = G.in_degree(node) if hasattr(G, "in_degree") else degree
    out_degree = G.out_degree(node) if hasattr(G, "out_degree") else degree
    incoming_count = data.get("incoming_count", 0)
    outgoing_count = data.get("outgoing_count", 0)
    total_sent = data.get("total_sent", 0)
    total_received = data.get("total_received", 0)
    avg_fee = data.get("avg_fee", 0)
    tx_volume = incoming_count + outgoing_count

    X.append([degree, in_degree, out_degree,
              incoming_count, outgoing_count,
              total_sent, total_received,
              avg_fee, tx_volume])
    y.append(data.get("risk_score", 0))

X = np.array(X, dtype=np.float64)  # float64 to avoid overflow
y = np.array(y, dtype=np.int64)

# ==== Handle skewed/large features ====
X[:, 5:8] = np.clip(X[:, 5:8], a_min=0, a_max=1e18)  # total_sent, total_received, avg_fee
X[:, 5] = np.log1p(X[:, 5])  # total_sent
X[:, 6] = np.log1p(X[:, 6])  # total_received
X[:, 7] = np.log1p(X[:, 7])  # avg_fee

# ==== Normalize Features ====
scaler = MinMaxScaler()
X = scaler.fit_transform(X)

# ==== Convert edges to edge_index ====
edges = np.array([[node_to_idx[u], node_to_idx[v]] for u, v in G.edges()]).T

# ==== PyG Data Object ====
data = Data(
    x=torch.tensor(X, dtype=torch.float),
    edge_index=torch.tensor(edges, dtype=torch.long),
    y=torch.tensor(y, dtype=torch.long)
)

# ==== Define GCN Model ====
class GCN(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, num_classes):
        super(GCN, self).__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, num_classes)

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.3, training=self.training)
        x = self.conv2(x, edge_index)
        return F.log_softmax(x, dim=1)

# ==== Training Setup ====
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = GCN(in_channels=X.shape[1], hidden_channels=64, num_classes=11).to(device)
data = data.to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = torch.nn.NLLLoss()

# ==== Train/Test Split ====
num_nodes = data.num_nodes
indices = np.arange(num_nodes)
train_idx, test_idx = train_test_split(indices, test_size=0.3, random_state=42)
train_mask = torch.zeros(num_nodes, dtype=torch.bool)
test_mask = torch.zeros(num_nodes, dtype=torch.bool)
train_mask[train_idx] = True
test_mask[test_idx] = True
data.train_mask = train_mask
data.test_mask = test_mask

# ==== Training Loop ====
print("[INFO] Training GCN model...")
for epoch in range(1, 50):
    model.train()
    optimizer.zero_grad()
    out = model(data)
    loss = criterion(out[data.train_mask], data.y[data.train_mask])
    loss.backward()
    optimizer.step()

    model.eval()
    pred = out[data.test_mask].max(1)[1]
    acc = pred.eq(data.y[data.test_mask]).sum().item() / data.test_mask.sum().item()
    print(f"Epoch {epoch:02d}, Loss: {loss.item():.4f}, Test Accuracy: {acc*100:.2f}%")

# ==== Save Model ====
print(f"[INFO] Saving trained model to {MODEL_SAVE_PATH}")
torch.save(model.state_dict(), MODEL_SAVE_PATH)

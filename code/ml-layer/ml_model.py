# D:\GitHub\Team4-CosmBlockchain\code\ml-layer\gnn_model.py

import os
import pickle
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv
from torch_geometric.loader import DataLoader
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tqdm import tqdm

# ==== Paths ====
GRAPH_PATH = r"D:\GitHub\Team4-CosmBlockchain\code\wallet-Graph\wallet_graph.pkl"
MODEL_SAVE_PATH = r"D:\GitHub\Team4-CosmBlockchain\code\ml-layer\gnn_model.pt"

# ==== Load Graph ====
print("[INFO] Loading wallet graph...")
with open(GRAPH_PATH, "rb") as f:
    G = pickle.load(f)

# ==== Feature extraction ====
print("[INFO] Extracting features and edges...")
node_features = []
node_labels = []
node_map = {}  # Map node -> index
for idx, (node, data) in enumerate(tqdm(G.nodes(data=True))):
    degree = G.degree(node)
    in_degree = G.in_degree(node) if hasattr(G, "in_degree") else degree
    out_degree = G.out_degree(node) if hasattr(G, "out_degree") else degree
    node_features.append([degree, in_degree, out_degree])
    node_labels.append(data.get("risk_score", 0))
    node_map[node] = idx

node_features = torch.tensor(MinMaxScaler().fit_transform(node_features), dtype=torch.float)
node_labels = torch.tensor(node_labels, dtype=torch.long)

# ==== Edges ====
edges = []
for u, v in G.edges():
    edges.append([node_map[u], node_map[v]])
edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

# ==== PyTorch Geometric Data ====
data = Data(x=node_features, y=node_labels, edge_index=edge_index)

# ==== Train/Test split ====
num_nodes = data.num_nodes
train_idx, test_idx = train_test_split(range(num_nodes), test_size=0.3, random_state=42)
train_mask = torch.zeros(num_nodes, dtype=torch.bool)
test_mask = torch.zeros(num_nodes, dtype=torch.bool)
train_mask[train_idx] = True
test_mask[test_idx] = True
data.train_mask = train_mask
data.test_mask = test_mask

# ==== Define GCN ====
class GCN(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim=64, output_dim=11):
        super(GCN, self).__init__()
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.fc = torch.nn.Linear(hidden_dim, output_dim)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = self.fc(x)
        return x

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = GCN(input_dim=node_features.shape[1]).to(device)
data = data.to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = torch.nn.CrossEntropyLoss()

# ==== Training ====
epochs = 50
print("[INFO] Training GCN...")
for epoch in range(1, epochs + 1):
    model.train()
    optimizer.zero_grad()
    out = model(data.x, data.edge_index)
    loss = criterion(out[data.train_mask], data.y[data.train_mask])
    loss.backward()
    optimizer.step()

    # Evaluation
    model.eval()
    _, pred = out.max(dim=1)
    correct = int((pred[data.test_mask] == data.y[data.test_mask]).sum())
    acc = correct / int(data.test_mask.sum())
    print(f"Epoch {epoch:02d}, Loss: {loss.item():.4f}, Test Acc: {acc*100:.2f}%")

# ==== Save Model ====
torch.save(model.state_dict(), MODEL_SAVE_PATH)
print(f"[INFO] Trained GCN saved to {MODEL_SAVE_PATH}")

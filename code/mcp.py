# server.py
import os
import pickle
import psycopg2
from fastmcp import FastMCP
from psycopg2.extras import RealDictCursor
import networkx as nx
from pyvis.network import Network

# ==== CONFIG ====
DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5433
}

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
GRAPH_FILE = os.path.join(BASE_PATH, "wallet_graph.pkl")  # your pre-built graph


# ==== INIT MCP ====
mcp = FastMCP("AML-Wallet-Graph-MCP")


# ------------------------------
# Tool 1: DB Schema
# ------------------------------
@mcp.tool()
def db_schema() -> str:
    """
    Return the database schema (tables and columns) so that queries can be built correctly.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema='public'
        ORDER BY table_name, ordinal_position;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    schema = {}
    for table, col, dtype in rows:
        schema.setdefault(table, []).append(f"{col} ({dtype})")
    return "\n".join([f"{t}: {', '.join(cols)}" for t, cols in schema.items()])


# ------------------------------
# Tool 2: Run arbitrary DB query
# ------------------------------
@mcp.tool()
def db_query(sql: str) -> list:
    """
    Execute a SQL query against the AML database and return results as JSON. Make sure you have the schema information from the tool before executing this
    Input: SQL string
    Output: List of rows (dict)
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(sql)
        if cur.description:  # SELECT query
            rows = cur.fetchall()
            return rows
        else:  # INSERT/UPDATE/DELETE
            conn.commit()
            return [{"status": "success"}]
    finally:
        cur.close()
        conn.close()


# ------------------------------
# Tool 3: Build wallet subgraph from .pkl
# ------------------------------
@mcp.tool()
def build_wallet_graph(wallet_id: str, max_hops: int = 2, output_file: str = "wallet_subgraph.html") -> str:
    """
    Load the pre-built graph from .pkl and extract the neighborhood subgraph for a wallet.
    Parameters:
        wallet_id (str): The wallet address to explore.
        max_hops (int): Number of transaction hops to include.
        output_file (str): Path to save interactive HTML visualization.
    Returns: Path to generated HTML file.
    """

    if not os.path.exists(GRAPH_FILE):
        raise FileNotFoundError(f"Graph file {GRAPH_FILE} not found. Build it first.")

    # Load graph from pickle
    with open(GRAPH_FILE, "rb") as f:
        G = pickle.load(f)

    # Extract neighborhood
    if wallet_id not in G:
        raise ValueError(f"Wallet {wallet_id} not found in graph.")

    lengths = nx.single_source_shortest_path_length(G.to_undirected(), wallet_id, cutoff=max_hops)
    selected_nodes = set(lengths.keys())
    SG = G.subgraph(selected_nodes).copy()

    # Visualization
    net = Network(height="750px", width="100%", bgcolor="white", font_color="black", directed=True)
    for n, d in SG.nodes(data=True):
        label = n[:10] + "..." if len(n) > 10 else n
        color = "red" if d.get("risk_score", 0) > 0.7 else "blue"
        net.add_node(n, label=label, title=str(d), color=color)
    for u, v, d in SG.edges(data=True):
        net.add_edge(u, v, title=str(d))

    output_path = os.path.join(BASE_PATH, output_file)
    net.write_html(output_path)
    return output_path


# ==== RUN ====
if __name__ == "__main__":
    mcp.run()

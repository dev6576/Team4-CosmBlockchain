import psycopg2
import networkx as nx
from pyvis.network import Network
import os
from collections import defaultdict
from tqdm import tqdm
import pickle
import math
from psycopg2.extras import execute_values

DB_CONFIG = {
    "dbname": "aml_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5433
}

MAX_RISK = 10

# ------------------------------
# Build full wallet graph and propagate risk efficiently
# ------------------------------
def build_wallet_graph():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    G = nx.DiGraph()

    # Load flagged wallets from DB
    cur.execute("SELECT wallet_id, reason, risk_score FROM flagged_wallets;")
    flagged_wallets_db = {w: {"reason": r, "risk_score": s} for w, r, s in cur.fetchall()}
    print(f"[INFO] Loaded {len(flagged_wallets_db)} flagged wallets from DB")

    # Helper to add nodes
    def add_node(addr, blockchain):
        if not G.has_node(addr):
            is_flagged = addr in flagged_wallets_db
            G.add_node(
                addr,
                color="white",
                borderWidth=2,
                flagged=is_flagged,
                flagged_reason=flagged_wallets_db[addr]["reason"] if is_flagged else None,
                risk_score=flagged_wallets_db[addr]["risk_score"] if is_flagged else 0,
                blockchain=blockchain,
                incoming_count=0,
                outgoing_count=0,
                total_received=0,
                total_sent=0
            )

    # Load transactions (BTC, ETH, ERC20)
    tx_queries = [
        ("BTC", """
            SELECT t.hash, t.input_addresses, o.addresses, o.value, t.block_number, t.block_timestamp, t.fee
            FROM bitcoin_transactions t
            JOIN bitcoin_outputs o ON t.hash = o.transaction_hash
            WHERE t.input_addresses IS NOT NULL AND o.addresses IS NOT NULL
            ORDER BY t.block_timestamp ASC;
        """),
        ("ETH", """
            SELECT hash, fromm_address, to_address, value, block_number, block_timestamp, gas_price
            FROM eth_transactions
            WHERE fromm_address IS NOT NULL AND to_address IS NOT NULL
            ORDER BY block_timestamp ASC;
        """),
        ("ERC20", """
            SELECT transaction_hash, from_address, to_address, value, block_number, block_timestamp
            FROM eth_token_transfers
            WHERE from_address IS NOT NULL AND to_address IS NOT NULL
            ORDER BY block_timestamp ASC;
        """)
    ]

    for blockchain, query in tx_queries:
        cur.execute(query)
        rows = cur.fetchall()
        print(f"[INFO] Loaded {len(rows)} {blockchain} transactions")
        for row in tqdm(rows, desc=f"Processing {blockchain} txs"):
            if blockchain == "BTC":
                tx_hash, from_addr, to_addr, value, block_number, ts, fee = row
            elif blockchain == "ETH":
                tx_hash, from_addr, to_addr, value, block_number, ts, fee = row
            else:
                tx_hash, from_addr, to_addr, value, block_number, ts = row
                fee = None

            if not from_addr or not to_addr:
                continue

            add_node(from_addr, blockchain if blockchain != "ERC20" else "ETH")
            add_node(to_addr, blockchain if blockchain != "ERC20" else "ETH")

            # Add edge
            G.add_edge(from_addr, to_addr,
                       tx_hash=tx_hash,
                       value=float(value or 0),
                       timestamp=str(ts),
                       token_type=blockchain if blockchain != "ETH" else "ETH_native",
                       block_number=block_number,
                       fee=float(fee or 0) if fee else None)

            # Update stats
            G.nodes[from_addr]["outgoing_count"] += 1
            G.nodes[from_addr]["total_sent"] += float(value or 0)
            G.nodes[to_addr]["incoming_count"] += 1
            G.nodes[to_addr]["total_received"] += float(value or 0)

    # ------------------------------
    # Risk propagation (efficient BFS)
    # ------------------------------
    print("[INFO] Propagating risk scores...")
    # risk_scores = {n: G.nodes[n]["risk_score"] for n in G.nodes}
    # flagged_nodes = [n for n, d in G.nodes(data=True) if d.get("flagged")]
    # for node in flagged_nodes:
    #     risk_scores[node] = MAX_RISK

    # # Multi-hop BFS: 1,2,3 hops, decaying risk
    # for flagged in tqdm(flagged_nodes, desc="Propagating from flagged wallets"):
    #     lengths = nx.single_source_shortest_path_length(G.to_undirected(), flagged, cutoff=3)
    #     for node, dist in lengths.items():
    #         if node in flagged_nodes:
    #             continue
    #         # Combine risk: decay with hop, + number of flagged sources
    #         incremental_risk = MAX_RISK / dist
    #         risk_scores[node] = min(MAX_RISK, risk_scores.get(node,0) + incremental_risk)

    # # Update graph
    # for node, risk in risk_scores.items():
    #     G.nodes[node]["risk_score"] = min(risk, MAX_RISK)
    #     if risk >= 1:
    #         G.nodes[node]["flagged"] = True
    #         G.nodes[node]["flagged_reason"] = "Proximity to risky wallets"

    # ------------------------------
    # Batch update DB
    # ------------------------------
    # flagged_to_upsert = [(n, d["flagged_reason"], d["risk_score"])
    #                      for n,d in G.nodes(data=True) if d["flagged"]]
    # if flagged_to_upsert:
    #     execute_values(cur, """
    #         INSERT INTO flagged_wallets (wallet_id, reason, risk_score)
    #         VALUES %s
    #         ON CONFLICT (wallet_id) DO UPDATE
    #         SET reason = EXCLUDED.reason,
    #             risk_score = GREATEST(flagged_wallets.risk_score, EXCLUDED.risk_score)
    #     """, flagged_to_upsert)
    #     conn.commit()

    # cur.close()
    # conn.close()
    # print("[INFO] Graph building and risk propagation completed")
    return G

# ------------------------------
# Visualize wallet graph (subset with dynamic info box)
#---------------------------------------------------
def visualize_graph(G, output_file="wallet_graph.html"):
    import os, random
    from pyvis.network import Network

    print("[INFO] Visualizing Graph..")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_file)

    net = Network(
        directed=True,
        height="750px",
        width="100%",
        bgcolor="white",
        font_color="black",
        cdn_resources='remote'
    )
    net.toggle_physics(True)

    # -----------------------------
    # Step 1: Seed graph with 30 high-risk and 40 low-risk wallets
    # -----------------------------
    high_risk_nodes = [n for n in G.nodes if G.nodes[n]["risk_score"] == MAX_RISK]
    low_risk_nodes = [n for n in G.nodes if G.nodes[n]["risk_score"] < MAX_RISK]

    seed_high_risk = random.sample(high_risk_nodes, min(20, len(high_risk_nodes)))
    seed_low_risk = random.sample(low_risk_nodes, min(30, len(low_risk_nodes)))

    selected_nodes = set(seed_high_risk + seed_low_risk)

    # -----------------------------
    # Step 2: Expand to include all connected nodes (no pruning)
    # -----------------------------
    frontier = list(selected_nodes)
    while frontier:
        current = frontier.pop(0)
        neighbors = list(G.successors(current)) + list(G.predecessors(current))
        for n in neighbors:
            if n not in selected_nodes:
                selected_nodes.add(n)
    print(f"[INFO] Total wallets selected after expansion: {len(selected_nodes)}")

    # -----------------------------
    # Step 3: Add nodes to pyvis
    # -----------------------------
    for node in selected_nodes:
        data = G.nodes[node]
        risk = min(data["risk_score"], MAX_RISK)
        r = int(255 * risk / MAX_RISK)
        g = 255 - r
        b = 255 - r
        color = f"rgb({r},{g},{b})"
        info = {
            "Wallet": node,
            "Flagged": data.get('flagged'),
            "Reason": data.get('flagged_reason'),
            "Risk Score": data.get('risk_score'),
            "Blockchain": data.get('blockchain'),
            "Incoming": data.get('incoming_count'),
            "Outgoing": data.get('outgoing_count'),
            "Total Sent": data.get('total_sent'),
            "Total Received": data.get('total_received')
        }
        net.add_node(node, label=node[:10]+"...", color=color, borderWidth=2, fixed=False, **{"info": info})

    # -----------------------------
    # Step 4: Add edges between selected nodes
    # -----------------------------
    for u, v, d in G.edges(data=True):
        if u in selected_nodes and v in selected_nodes:
            info = {
                "Tx Hash": d['tx_hash'],
                "Value": d['value'],
                "Timestamp": d['timestamp'],
                "Token": d['token_type'],
                "Block": d['block_number'],
                "Fee": d['fee']
            }
            net.add_edge(u, v, value=d["value"], title="", **{"info": info})

    # -----------------------------
    # Step 5: Write HTML and inject JS
    # -----------------------------
    net.write_html(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    js_snippet = """<script type="text/javascript">
    var network = window.network;
    var container = document.getElementById('mynetwork');
    var infoBox = document.createElement('div');
    infoBox.style.position = 'absolute';
    infoBox.style.background = 'white';
    infoBox.style.border = '1px solid black';
    infoBox.style.padding = '8px';
    infoBox.style.display = 'none';
    infoBox.style.zIndex = 10;
    document.body.appendChild(infoBox);
    network.on('click', function(params) {
        if(params.nodes.length > 0){
            var nodeId = params.nodes[0];
            var nodeData = network.body.data.nodes.get(nodeId);
            var info = nodeData.info;
            infoBox.innerHTML = '';
            for(var key in info){
                infoBox.innerHTML += '<b>' + key + ':</b> ' + info[key] + '<br>';
            }
            infoBox.style.display = 'block';
            infoBox.style.left = params.pointer.DOM.x + 'px';
            infoBox.style.top = params.pointer.DOM.y + 'px';
        } else if(params.edges.length > 0){
            var edgeId = params.edges[0];
            var edgeData = network.body.data.edges.get(edgeId);
            var info = edgeData.info;
            infoBox.innerHTML = '';
            for(var key in info){
                infoBox.innerHTML += '<b>' + key + ':</b> ' + info[key] + '<br>';
            }
            infoBox.style.display = 'block';
            infoBox.style.left = params.pointer.DOM.x + 'px';
            infoBox.style.top = params.pointer.DOM.y + 'px';
        } else {
            infoBox.style.display = 'none';
        }
    });
    </script>"""
    html_content = html_content.replace("</body>", js_snippet + "</body>")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[INFO] Graph visualization saved to {output_path}")

# ------------------------------
# Save full graph for ML
# ------------------------------
def save_graph_pickle(G, file_name="wallet_graph.pkl"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, file_name)
    with open(file_path, "wb") as f:
        pickle.dump(G, f)
    print(f"[INFO] Graph pickle saved to {file_path}")

# ------------------------------
# Main
# ------------------------------
if __name__ == "__main__":
    G = build_wallet_graph()
    visualize_graph(G)
    save_graph_pickle(G)

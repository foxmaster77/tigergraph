"""
TigerGraph Data Loader
Loads generated synthetic data into TigerGraph Savanna/CE
"""
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

try:
    import pyTigerGraph as tg
    TG_AVAILABLE = True
except ImportError:
    TG_AVAILABLE = False
    print("WARNING: pyTigerGraph not installed. Using mock mode.")


def connect():
    """Establish TigerGraph connection."""
    if not TG_AVAILABLE:
        return None

    host = os.getenv('TG_HOST', 'http://localhost')
    username = os.getenv('TG_USERNAME', 'tigergraph')
    password = os.getenv('TG_PASSWORD', 'tigergraph')
    graph = os.getenv('TG_GRAPH', 'FraudGraph')

    try:
        conn = tg.TigerGraphConnection(
            host=host,
            username=username,
            password=password,
            graphname=graph
        )
        conn.getToken(conn.createSecret())
        print(f"✓ Connected to TigerGraph: {host} / {graph}")
        return conn
    except Exception as e:
        print(f"✗ TigerGraph connection failed: {e}")
        print("  Running in mock mode — data will be stored locally only.")
        return None


def upsert_accounts(conn, accounts):
    """Load accounts as Account vertices."""
    if not conn:
        print(f"  [mock] Would load {len(accounts)} Account vertices")
        return
    vertices = {}
    for a in accounts:
        vertices[a['account_id']] = {
            'card1': a['card1'], 'card2': a['card2'],
            'card3': a['card3'], 'card4': a['card4'],
            'card5': a['card5'], 'card6': a['card6'],
            'addr1': a['addr1'], 'addr2': a['addr2'],
            'P_emaildomain': a['P_emaildomain'],
            'R_emaildomain': a['R_emaildomain'],
            'is_blocked': a['is_blocked'],
            'created_at': a['created_at']
        }
    result = conn.upsertVertices('Account', vertices)
    print(f"  ✓ Loaded {result} Account vertices")


def upsert_devices(conn, devices):
    """Load devices as Device vertices."""
    if not conn:
        print(f"  [mock] Would load {len(devices)} Device vertices")
        return
    vertices = {}
    for d in devices:
        vertices[d['device_id']] = {
            'device_type': d['device_type'],
            'device_info': d['device_info'],
            'browser': d['browser'],
            'os': d['os']
        }
    result = conn.upsertVertices('Device', vertices)
    print(f"  ✓ Loaded {result} Device vertices")


def upsert_transactions(conn, transactions):
    """Load transactions as Transaction vertices and create edges."""
    if not conn:
        print(f"  [mock] Would load {len(transactions)} Transaction vertices")
        return

    t_vertices = {}
    made_edges = []
    used_device_edges = []

    now = datetime.now().isoformat()
    for t in transactions:
        t_vertices[t['transaction_id']] = {
            'transaction_dt': t['transaction_dt'],
            'transaction_amt': t['transaction_amt'],
            'product_cd': t['product_cd'],
            'dist1': t.get('dist1', 0.0),
            'dist2': t.get('dist2', 0.0),
            'risk_score': t['risk_score'],
            'status': t.get('status', 'completed'),
            'created_at': now
        }
        made_edges.append((t['account_id'], t['transaction_id']))
        if t.get('device_id'):
            used_device_edges.append((t['transaction_id'], t['device_id']))

    result = conn.upsertVertices('Transaction', t_vertices)
    print(f"  ✓ Loaded {result} Transaction vertices")

    edge_data = [(src, tgt, {'timestamp': now}) for src, tgt in made_edges]
    conn.upsertEdges('Account', 'MADE_TRANSACTION', 'Transaction', edge_data)
    print(f"  ✓ Loaded {len(made_edges)} MADE_TRANSACTION edges")

    if used_device_edges:
        dev_edge_data = [(src, tgt, {'timestamp': now}) for src, tgt in used_device_edges]
        conn.upsertEdges('Transaction', 'USED_DEVICE', 'Device', dev_edge_data)
        print(f"  ✓ Loaded {len(used_device_edges)} USED_DEVICE edges")


def upsert_fraud_patterns(conn):
    """Load 5 known fraud patterns into FraudPattern vertices."""
    patterns = [
        {
            'pattern_id': 'PT001',
            'pattern_name': 'Card Testing',
            'description': 'Multiple micro-transactions followed by large purchase',
            'indicators': 'high_velocity,small_amounts,amount_spike,multiple_merchants',
            'typical_risk': 'HIGH'
        },
        {
            'pattern_id': 'PT002',
            'pattern_name': 'Account Takeover',
            'description': 'New device, new location, unusual transaction type',
            'indicators': 'new_device,new_location,email_change,amount_anomaly',
            'typical_risk': 'CRITICAL'
        },
        {
            'pattern_id': 'PT003',
            'pattern_name': 'Synthetic Identity',
            'description': 'New account with immediate high spend and free email domain',
            'indicators': 'new_account,temp_email,no_history,mid_risk_score',
            'typical_risk': 'HIGH'
        },
        {
            'pattern_id': 'PT004',
            'pattern_name': 'Money Mule Network',
            'description': 'Multiple accounts sharing same device or card attributes',
            'indicators': 'shared_device,fund_transfers,hub_spoke_graph,high_amount',
            'typical_risk': 'CRITICAL'
        },
        {
            'pattern_id': 'PT005',
            'pattern_name': 'Merchant Collusion',
            'description': 'High volume at single merchant, multiple different cards',
            'indicators': 'single_merchant,multiple_cards,amount_above_baseline',
            'typical_risk': 'HIGH'
        }
    ]
    if not conn:
        print(f"  [mock] Would load {len(patterns)} FraudPattern vertices")
        return
    vertices = {p['pattern_id']: {
        'pattern_name': p['pattern_name'],
        'description': p['description'],
        'indicators': p['indicators'],
        'typical_risk': p['typical_risk'],
        'example_case_ids': ''
    } for p in patterns}
    result = conn.upsertVertices('FraudPattern', vertices)
    print(f"  ✓ Loaded {result} FraudPattern vertices")


def upsert_closed_cases(conn, cases):
    """Load historical closed cases."""
    if not conn:
        print(f"  [mock] Would load {len(cases)} historical FraudCase vertices")
        return
    vertices = {}
    edges_acc = []
    edges_txn = []
    now = datetime.now().isoformat()

    for c in cases:
        vertices[c['case_id']] = {
            'trigger_type': c['trigger_type'],
            'trigger_source': 'historical',
            'account_id': c['account_id'],
            'transaction_id': c['transaction_id'],
            'status': c['status'],
            'fraud_type': c['fraud_type'],
            'risk_level': c['risk_level'],
            'risk_score': c['risk_score'],
            'confidence': c['confidence'],
            'outcome': c['outcome'],
            'next_best_action': c['next_best_action'],
            'requires_sar': c['requires_sar'],
            'sar_filed': c['sar_filed'],
            'created_at': c['created_at'],
            'closed_at': c.get('closed_at', now),
            'updated_at': now
        }
        edges_acc.append((c['account_id'], c['case_id']))
        edges_txn.append((c['transaction_id'], c['case_id']))

    result = conn.upsertVertices('FraudCase', vertices)
    print(f"  ✓ Loaded {result} historical FraudCase vertices")

    conn.upsertEdges('Account', 'ACCOUNT_IN_CASE', 'FraudCase',
                     [(s, t, {'role': 'subject'}) for s, t in edges_acc])
    conn.upsertEdges('Transaction', 'PART_OF_CASE', 'FraudCase',
                     [(s, t, {'reason': 'investigation_trigger'}) for s, t in edges_txn])
    print(f"  ✓ Loaded historical case edges")


def build_shared_device_edges(conn, transactions):
    """Create SHARED_DEVICE edges between accounts sharing a device."""
    if not conn:
        print("  [mock] Would build SHARED_DEVICE edges")
        return
    from collections import defaultdict
    device_to_accounts = defaultdict(set)
    for t in transactions:
        if t.get('device_id'):
            device_to_accounts[t['device_id']].add(t['account_id'])

    edges = []
    now = datetime.now().isoformat()
    for device_id, accs in device_to_accounts.items():
        acc_list = list(accs)
        for i in range(len(acc_list)):
            for j in range(i + 1, len(acc_list)):
                edges.append((acc_list[i], acc_list[j], {
                    'device_id': device_id, 'first_seen': now
                }))
                edges.append((acc_list[j], acc_list[i], {
                    'device_id': device_id, 'first_seen': now
                }))

    if edges:
        conn.upsertEdges('Account', 'SHARED_DEVICE', 'Account', edges[:2000])
        print(f"  ✓ Built {len(edges)} SHARED_DEVICE edges (capped at 2000)")


def main():
    print("=" * 60)
    print("TigerGraph Fraud Investigation — Data Loader")
    print("=" * 60)

    # Load generated data
    with open('data/accounts.json') as f:
        accounts = json.load(f)
    with open('data/devices.json') as f:
        devices = json.load(f)
    with open('data/transactions.json') as f:
        transactions = json.load(f)
    with open('data/closed_cases.json') as f:
        closed_cases = json.load(f)

    conn = connect()

    print("\nLoading vertices...")
    upsert_accounts(conn, accounts)
    upsert_devices(conn, devices)
    upsert_transactions(conn, transactions)
    upsert_fraud_patterns(conn)

    print("\nLoading historical cases...")
    upsert_closed_cases(conn, closed_cases)

    print("\nBuilding relationship edges...")
    build_shared_device_edges(conn, transactions)

    print("\n✓ Data loading complete!")
    if not conn:
        print("  NOTE: Running in mock mode — no data was sent to TigerGraph.")
        print("  Set TG_HOST, TG_USERNAME, TG_PASSWORD in .env to connect.")


if __name__ == '__main__':
    main()

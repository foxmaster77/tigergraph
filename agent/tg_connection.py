"""
TigerGraph Connection Manager
Provides a singleton pyTigerGraph connection for the agent.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

_conn = None
_mock_data = {}

def _load_mock_data():
    """Load generated JSON data for mock mode."""
    data_dir = Path(__file__).parent.parent / 'data'
    global _mock_data
    for fname in ['accounts.json', 'devices.json', 'transactions.json',
                  'closed_cases.json']:
        fpath = data_dir / fname
        if fpath.exists():
            key = fname.replace('.json', '')
            with open(fpath) as f:
                _mock_data[key] = json.load(f)
    return _mock_data


def get_connection():
    """Return TigerGraph connection or None (mock mode)."""
    global _conn
    if _conn is not None:
        return _conn

    host = os.getenv('TG_HOST', '')
    username = os.getenv('TG_USERNAME', 'tigergraph')
    password = os.getenv('TG_PASSWORD', 'tigergraph')
    graph = os.getenv('TG_GRAPH', 'FraudGraph')

    if not host or host == 'https://your-host.i.tgcloud.io':
        _load_mock_data()
        return None

    try:
        import pyTigerGraph as tg
        conn = tg.TigerGraphConnection(
            host=host, username=username,
            password=password, graphname=graph
        )
        conn.getToken(conn.createSecret())
        _conn = conn
        print(f"✓ TigerGraph connected: {host}")
        return _conn
    except Exception as e:
        print(f"TigerGraph connection failed: {e}. Using mock mode.")
        _load_mock_data()
        return None


def get_mock_data():
    """Return in-memory mock dataset."""
    if not _mock_data:
        _load_mock_data()
    return _mock_data

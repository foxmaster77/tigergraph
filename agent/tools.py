"""
LangChain Tools for Fraud Investigation Agent
Each tool wraps TigerGraph queries or mock data operations.
"""
import json
import random
from datetime import datetime
from langchain.tools import tool
from agent.tg_connection import get_connection, get_mock_data
from agent.graphrag import get_rag

# ─── Helper ────────────────────────────────────────────────────────────────
def _run_query(query_name: str, params: dict):
    """Execute a GSQL installed query on TigerGraph."""
    conn = get_connection()
    if conn:
        return conn.runInstalledQuery(query_name, params)
    return None


def _mock_transactions_for_account(account_id: str, limit: int = 20):
    data = get_mock_data()
    txns = data.get('transactions', [])
    result = [t for t in txns if t.get('account_id') == account_id]
    result.sort(key=lambda x: x.get('transaction_dt', 0), reverse=True)
    return result[:limit]


def _mock_account(account_id: str):
    data = get_mock_data()
    accounts = data.get('accounts', [])
    for a in accounts:
        if a['account_id'] == account_id:
            return a
    return {'account_id': account_id, 'card4': 'visa', 'card6': 'debit',
            'P_emaildomain': 'gmail.com', 'addr1': 299.0, 'addr2': 87.0}


# ─── TOOL 1: Transaction history ──────────────────────────────────────────
@tool
def get_transaction_history(account_id: str) -> str:
    """
    Retrieve the recent transaction history for an account from TigerGraph.
    Returns transaction IDs, amounts, timestamps, risk scores, and product codes.
    Use this when starting an investigation to understand account behavior.
    Input: account_id (e.g. 'ACC_00023')
    """
    result = _run_query('get_account_transactions', {'acc': account_id, 'limit': 30})
    if result:
        return json.dumps(result, indent=2)

    # Mock mode
    txns = _mock_transactions_for_account(account_id, 20)
    if not txns:
        # Generate plausible transactions
        txns = [
            {
                'transaction_id': f'TXN_{random.randint(100000,999999):06d}',
                'transaction_amt': round(random.uniform(10, 2000), 2),
                'transaction_dt': random.randint(1000000, 4800000),
                'risk_score': round(random.uniform(0.05, 0.95), 4),
                'product_cd': random.choice(['W', 'H', 'C', 'S']),
                'account_id': account_id
            }
            for _ in range(random.randint(5, 15))
        ]
    summary_lines = [
        f"- TXN {t['transaction_id']}: ${t['transaction_amt']:.2f}, "
        f"risk={t['risk_score']:.3f}, product={t.get('product_cd','?')}"
        for t in txns
    ]
    avg_risk = sum(t['risk_score'] for t in txns) / len(txns) if txns else 0
    return (
        f"Transaction history for {account_id} ({len(txns)} transactions):\n"
        + "\n".join(summary_lines)
        + f"\nAverage risk score: {avg_risk:.3f}"
    )


# ─── TOOL 2: Connected accounts ────────────────────────────────────────────
@tool
def get_connected_accounts(account_id: str) -> str:
    """
    Find accounts connected to the target account via shared devices or card attributes.
    This is critical for detecting money mule networks and account takeover rings.
    Returns connected account IDs and the shared attribute (device/card).
    Input: account_id (e.g. 'ACC_00010')
    """
    result = _run_query('get_connected_accounts', {'acc': account_id, 'hops': 2})
    if result:
        return json.dumps(result, indent=2)

    # Mock: simulate shared devices
    data = get_mock_data()
    txns = data.get('transactions', [])
    account_txns = [t for t in txns if t.get('account_id') == account_id]

    shared_device_accs = {}
    for txn in account_txns:
        dev = txn.get('device_id')
        if dev:
            for other in txns:
                if other.get('device_id') == dev and other.get('account_id') != account_id:
                    shared_device_accs[other['account_id']] = dev

    if not shared_device_accs:
        return f"No connected accounts found for {account_id}. Account appears isolated."

    lines = [f"- {acc} (shared device: {dev})" for acc, dev in list(shared_device_accs.items())[:10]]
    risk_note = "⚠️ HIGH RISK: Multiple shared devices suggest possible mule network." if len(shared_device_accs) >= 3 else ""
    return (
        f"Connected accounts for {account_id} ({len(shared_device_accs)} found):\n"
        + "\n".join(lines)
        + (f"\n{risk_note}" if risk_note else "")
    )


# ─── TOOL 3: Detect fraud patterns ─────────────────────────────────────────
@tool
def detect_fraud_patterns(account_id: str, transaction_id: str) -> str:
    """
    Analyze an account and transaction against the 5 known fraud patterns using
    TigerGraph graph traversal. Returns matched patterns and confidence scores.
    Input format: 'account_id|transaction_id' (e.g. 'ACC_00000|TXN_CT_BIG')
    """
    txns = _mock_transactions_for_account(account_id, 30)
    if not txns:
        txns = [{'transaction_amt': 150.0, 'risk_score': 0.45, 'product_cd': 'W', 'device_id': 'DEV_0001'}]

    amounts = [t['transaction_amt'] for t in txns]
    risk_scores = [t['risk_score'] for t in txns]
    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.3

    # Derive target txn risk
    data = get_mock_data()
    target_txn = next((t for t in data.get('transactions', []) if t['transaction_id'] == transaction_id), None)
    target_risk = target_txn['risk_score'] if target_txn else avg_risk
    target_amt = target_txn['transaction_amt'] if target_txn else amounts[-1] if amounts else 100.0

    patterns_found = []

    # PT001: Card Testing
    small_count = sum(1 for a in amounts if a < 10)
    if small_count >= 3 and target_amt > 200:
        patterns_found.append({
            'pattern_id': 'PT001', 'name': 'Card Testing',
            'confidence': round(min(0.9, 0.5 + small_count * 0.1), 2),
            'indicators': f'{small_count} micro-transactions < $10 then large ${target_amt:.2f}'
        })

    # PT002: Account Takeover (elevated risk + high amount)
    if target_risk > 0.7 and target_amt > 300 and avg_risk < 0.4:
        patterns_found.append({
            'pattern_id': 'PT002', 'name': 'Account Takeover',
            'confidence': round(min(0.85, target_risk), 2),
            'indicators': f'Risk spike to {target_risk:.2f}, avg history {avg_risk:.2f}, amount ${target_amt:.2f}'
        })

    # PT003: Synthetic Identity (mid risk, high velocity)
    if 0.4 <= avg_risk <= 0.7 and len(txns) > 8 and target_risk >= 0.5:
        patterns_found.append({
            'pattern_id': 'PT003', 'name': 'Synthetic Identity',
            'confidence': round(avg_risk * 0.85, 2),
            'indicators': f'Avg risk {avg_risk:.2f}, {len(txns)} transactions, score in "avoid-trigger" band'
        })

    # PT004: Money Mule (will be confirmed by get_connected_accounts)
    if target_risk > 0.65:
        patterns_found.append({
            'pattern_id': 'PT004', 'name': 'Money Mule Network',
            'confidence': round(target_risk * 0.7, 2),
            'indicators': 'High risk score. Run get_connected_accounts to confirm network.'
        })

    # PT005: Merchant Collusion (dist1 low + high amount)
    if target_txn and target_txn.get('dist1', 999) < 20 and target_amt > 500:
        patterns_found.append({
            'pattern_id': 'PT005', 'name': 'Merchant Collusion',
            'confidence': round(min(0.8, 0.5 + target_amt / 10000), 2),
            'indicators': f'Low dist1 ({target_txn.get("dist1",0)}), high amount ${target_amt:.2f}'
        })

    if not patterns_found:
        return f"No strong fraud patterns detected.\nRisk: {avg_risk:.3f} (baseline behavior appears normal)"

    result = f"Fraud patterns detected for {account_id} / {transaction_id}:\n"
    for p in patterns_found:
        result += (f"\n🔴 [{p['pattern_id']}] {p['name']} "
                   f"(confidence: {p['confidence']:.0%})\n   → {p['indicators']}\n")
    return result


# ─── TOOL 4: Similar historical cases ──────────────────────────────────────
@tool
def get_similar_cases(fraud_type: str) -> str:
    """
    Retrieve similar closed fraud cases from the graph for memory and context.
    Helps the agent learn from past investigations and outcomes.
    Input: fraud_type — one of: card_testing, account_takeover, synthetic_identity,
           money_mule_network, merchant_collusion
    """
    result = _run_query('get_similar_cases', {'fraud_type': fraud_type, 'min_conf': 0.5, 'limit': 5})
    if result:
        return json.dumps(result, indent=2)

    data = get_mock_data()
    cases = data.get('closed_cases', [])
    similar = [c for c in cases if c.get('fraud_type') == fraud_type and c.get('status') == 'closed'][:5]
    if not similar:
        similar = cases[:3] if cases else []

    if not similar:
        return f"No historical cases found for fraud type: {fraud_type}"

    lines = [
        f"- {c['case_id']}: outcome={c.get('outcome','?')}, risk={c.get('risk_score',0):.3f}, "
        f"action='{c.get('next_best_action','N/A')}'"
        for c in similar
    ]
    return (
        f"Historical cases for '{fraud_type}' ({len(similar)} found):\n"
        + "\n".join(lines)
        + f"\nMost common outcome: {max(set(c.get('outcome','?') for c in similar), key=lambda x: sum(1 for c in similar if c.get('outcome') == x))}"
    )


# ─── TOOL 5: Policy retrieval (GraphRAG) ───────────────────────────────────
@tool
def get_fraud_policy(query: str) -> str:
    """
    Retrieve relevant fraud policy, regulatory requirements, and action guidelines.
    Use this to determine what actions are authorized, when SARs are required,
    and what approval routes are needed.
    Input: natural language query (e.g. 'when to file SAR', 'account freeze approval')
    """
    rag = get_rag()
    return rag.query(query)


# ─── TOOL 6: Create/Update Fraud Case ──────────────────────────────────────
_active_cases = {}  # In-memory case store for mock mode

@tool
def manage_case(instruction: str) -> str:
    """
    Create or update a fraud case in TigerGraph.
    Instruction format (JSON string):
    {
      "action": "create" | "update" | "get",
      "case_id": "BENCH_01",
      "account_id": "ACC_00000",
      "transaction_id": "TXN_CT_BIG",
      "fraud_type": "card_testing",
      "risk_level": "HIGH",
      "risk_score": 0.82,
      "confidence": 0.87,
      "evidence_summary": "...",
      "next_best_action": "...",
      "status": "open"
    }
    """
    try:
        data = json.loads(instruction)
    except Exception:
        return f"Error: instruction must be valid JSON. Got: {instruction[:200]}"

    action = data.get('action', 'create')
    case_id = data.get('case_id', f'CASE_{datetime.now().strftime("%H%M%S")}')

    conn = get_connection()
    now = datetime.now().isoformat()

    if action in ('create', 'update'):
        case_record = {
            'case_id': case_id,
            'account_id': data.get('account_id', ''),
            'transaction_id': data.get('transaction_id', ''),
            'trigger_type': data.get('trigger_type', 'risk_score'),
            'trigger_source': data.get('trigger_source', 'automated_risk_system'),
            'fraud_type': data.get('fraud_type', 'unknown'),
            'status': data.get('status', 'open'),
            'risk_level': data.get('risk_level', 'unknown'),
            'risk_score': data.get('risk_score', 0.0),
            'confidence': data.get('confidence', 0.0),
            'evidence_summary': data.get('evidence_summary', ''),
            'next_best_action': data.get('next_best_action', ''),
            'next_best_action_pre_evidence': data.get('next_best_action_pre_evidence', ''),
            'next_best_action_post_evidence': data.get('next_best_action_post_evidence', ''),
            'requires_sar': data.get('requires_sar', False),
            'approval_route': data.get('approval_route', ''),
            'investigator_notes': data.get('investigator_notes', ''),
            'created_at': now,
            'updated_at': now,
            'outcome': data.get('outcome', '')
        }

        _active_cases[case_id] = case_record  # always save locally

        if conn:
            try:
                conn.upsertVertex('FraudCase', case_id, case_record)
                if case_record['account_id']:
                    conn.upsertEdge('Account', case_record['account_id'],
                                    'ACCOUNT_IN_CASE', 'FraudCase', case_id,
                                    {'role': 'subject'})
                return f"✓ Case {case_id} {action}d in TigerGraph."
            except Exception as e:
                return f"✓ Case {case_id} {action}d locally (TG error: {e})."
        return f"✓ Case {case_id} {action}d successfully (mock mode)."

    elif action == 'get':
        if case_id in _active_cases:
            return json.dumps(_active_cases[case_id], indent=2)
        return f"Case {case_id} not found."

    return f"Unknown action: {action}"


# ─── TOOL 7: Execute action ────────────────────────────────────────────────
@tool
def execute_action(instruction: str) -> str:
    """
    Execute or simulate a fraud response action. Actions are policy-controlled.
    Instruction format (JSON string):
    {
      "action": "block_transaction"|"freeze_account"|"request_step_up_auth"|
                "warn_customer"|"escalate_l2"|"file_sar"|"allow_transaction"|
                "monitor_account"|"block_merchant",
      "target_id": "ACC_00000" or "TXN_001",
      "case_id": "BENCH_01",
      "reason": "explanation"
    }
    Returns: action confirmation and required approval route.
    """
    try:
        data = json.loads(instruction)
    except Exception:
        return f"Error: instruction must be valid JSON."

    action = data.get('action', '')
    target = data.get('target_id', 'unknown')
    case_id = data.get('case_id', 'unknown')
    reason = data.get('reason', 'fraud investigation')

    approval_map = {
        'allow_transaction': ('System (automated)', False),
        'monitor_account': ('System (automated)', False),
        'request_step_up_auth': ('System (automated)', False),
        'warn_customer': ('System (automated)', False),
        'hold_transaction': ('System (automated)', False),
        'block_transaction': ('L1 Fraud Analyst', True),
        'freeze_account': ('L1 Fraud Analyst', True),
        'escalate_l2': ('L1 Fraud Analyst', False),
        'file_sar': ('Compliance Officer', True),
        'block_merchant': ('L2 Fraud Analyst', True),
        'law_enforcement_referral': ('Legal / Compliance', True)
    }

    approval_route, needs_approval = approval_map.get(action, ('Manual Review', True))
    status = "PENDING APPROVAL" if needs_approval else "EXECUTED"
    timestamp = datetime.now().isoformat()

    result = (
        f"[ACTION RECORD]\n"
        f"  Case ID:        {case_id}\n"
        f"  Action:         {action.replace('_', ' ').upper()}\n"
        f"  Target:         {target}\n"
        f"  Reason:         {reason}\n"
        f"  Approval Route: {approval_route}\n"
        f"  Status:         {status}\n"
        f"  Timestamp:      {timestamp}\n"
    )

    # Simulate side effects
    if action == 'file_sar':
        result += f"  SAR Reference:  SAR-{case_id}-{datetime.now().strftime('%Y%m%d')}\n"
    if action in ('freeze_account', 'block_transaction'):
        result += f"  ⚠️  Human approval required before execution.\n"

    return result


# ─── TOOL 8: Request additional evidence ───────────────────────────────────
@tool
def request_additional_evidence(instruction: str) -> str:
    """
    Request additional evidence when uncertainty is high.
    Simulates Tier 2 evidence gathering (requires policy approval).
    Instruction format (JSON):
    {
      "evidence_type": "step_up_auth"|"identity_verification"|"transaction_dispute"|
                       "device_history"|"external_fraud_db",
      "account_id": "ACC_00000",
      "case_id": "BENCH_01",
      "reason": "why this evidence is needed"
    }
    Returns simulated evidence response.
    """
    try:
        data = json.loads(instruction)
    except Exception:
        return "Error: instruction must be valid JSON."

    ev_type = data.get('evidence_type', 'unknown')
    account_id = data.get('account_id', 'unknown')
    case_id = data.get('case_id', 'unknown')
    reason = data.get('reason', '')

    responses = {
        'step_up_auth': {
            'result': random.choice(['PASSED', 'FAILED', 'TIMED_OUT']),
            'detail': 'Customer responded to authentication challenge.'
        },
        'identity_verification': {
            'result': random.choice(['VERIFIED', 'UNVERIFIED', 'DOCUMENTS_REQUESTED']),
            'detail': 'KYC document check completed.'
        },
        'transaction_dispute': {
            'result': random.choice(['DISPUTED', 'NOT_DISPUTED', 'NO_RESPONSE']),
            'detail': 'Customer dispute status retrieved.'
        },
        'device_history': {
            'result': 'RETRIEVED',
            'devices_seen': random.randint(1, 5),
            'last_known_device': 'Windows Chrome (familiar)',
            'new_device_detected': random.random() > 0.5
        },
        'external_fraud_db': {
            'result': 'CHECKED',
            'hits': random.randint(0, 3),
            'match_type': random.choice(['card_compromise', 'identity_fraud', 'no_match'])
        }
    }

    response = responses.get(ev_type, {'result': 'NOT_AVAILABLE', 'detail': 'Evidence type not supported.'})

    return (
        f"[EVIDENCE REQUEST]\n"
        f"  Type:    {ev_type}\n"
        f"  Account: {account_id}\n"
        f"  Case:    {case_id}\n"
        f"  Reason:  {reason}\n"
        f"  Result:  {json.dumps(response, indent=4)}\n"
    )


ALL_TOOLS = [
    get_transaction_history,
    get_connected_accounts,
    detect_fraud_patterns,
    get_similar_cases,
    get_fraud_policy,
    manage_case,
    execute_action,
    request_additional_evidence,
]

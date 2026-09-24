"""
Synthetic IEEE-CIS-style dataset generator for TigerGraph Fraud Investigation.
Generates realistic transaction data matching HHGOA_IEEE schema.
"""
import random
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

# ── Config ────────────────────────────────────────────────────────────────────
N_ACCOUNTS = 500
N_TRANSACTIONS = 5000
N_DEVICES = 200
START_DT = datetime(2024, 1, 1)
BASE_DT = int(START_DT.timestamp())

PRODUCT_CATEGORIES = ['W', 'H', 'C', 'S', 'R']
EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
                 'anonymous.com', 'temp-mail.org', 'protonmail.com']
DEVICE_TYPES = ['desktop', 'mobile', 'tablet']
CARD4_VALUES = ['visa', 'mastercard', 'discover', 'american express']
CARD6_VALUES = ['debit', 'credit', 'charge card']

def random_dt(start=0, end=4838400):
    """Returns random transaction delta-time."""
    return random.randint(start, end)

def generate_accounts(n=N_ACCOUNTS):
    accounts = []
    for i in range(n):
        acc = {
            'account_id': f'ACC_{i:05d}',
            'card1': random.randint(1000, 18000),
            'card2': round(random.uniform(100, 600), 0),
            'card3': round(random.uniform(100, 220), 0),
            'card4': random.choice(CARD4_VALUES),
            'card5': round(random.uniform(100, 240), 0),
            'card6': random.choice(CARD6_VALUES),
            'addr1': round(random.uniform(100, 500), 0),
            'addr2': round(random.uniform(10, 102), 0),
            'P_emaildomain': random.choice(EMAIL_DOMAINS),
            'R_emaildomain': random.choice(EMAIL_DOMAINS),
            'is_blocked': False,
            'fraud_score_avg': 0.0,
            'total_transactions': 0,
            'total_amount': 0.0,
            'created_at': (START_DT - timedelta(days=random.randint(0, 365))).isoformat()
        }
        accounts.append(acc)
    return accounts

def generate_devices(n=N_DEVICES):
    devices = []
    for i in range(n):
        dev = {
            'device_id': f'DEV_{i:04d}',
            'device_type': random.choice(DEVICE_TYPES),
            'device_info': f'{random.choice(["Windows", "MacOS", "iOS", "Android"])} {random.randint(10,14)}',
            'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
            'os': random.choice(['Windows NT 10.0', 'Mac OS X', 'Android', 'iPhone OS'])
        }
        devices.append(dev)
    return devices

def assign_base_risk(txn):
    """Heuristic risk score based on transaction features."""
    score = 0.1
    if txn['transaction_amt'] > 1000:
        score += 0.2
    if txn['transaction_amt'] > 5000:
        score += 0.2
    if txn['product_cd'] in ['H', 'C']:
        score += 0.05
    if txn['dist1'] > 300:
        score += 0.1
    score += random.uniform(-0.05, 0.1)
    return min(max(round(score, 4), 0.01), 0.99)

def inject_fraud_patterns(transactions, accounts, devices):
    """Inject 5 known fraud patterns into transaction data."""
    injected = []

    # Pattern 1: Card Testing (PT001) — small txns then large
    ct_account = accounts[0]['account_id']
    base_t = random_dt(100000, 3000000)
    for i in range(5):
        injected.append({
            'transaction_id': f'TXN_CT_{i:03d}',
            'account_id': ct_account,
            'transaction_dt': base_t + i * 300,
            'transaction_amt': round(random.uniform(0.5, 5.0), 2),
            'product_cd': 'W',
            'dist1': 10.0, 'dist2': 0.0,
            'risk_score': 0.30 + random.uniform(0, 0.1),
            'device_id': f'DEV_{random.randint(0, 10):04d}',
            'status': 'completed'
        })
    injected.append({
        'transaction_id': 'TXN_CT_BIG',
        'account_id': ct_account,
        'transaction_dt': base_t + 5 * 300,
        'transaction_amt': 2499.99,
        'product_cd': 'H',
        'dist1': 310.0, 'dist2': 50.0,
        'risk_score': 0.82,
        'device_id': f'DEV_0001',
        'status': 'completed'
    })

    # Pattern 2: Account Takeover (PT002) — new device, new location
    ato_account = accounts[1]['account_id']
    injected.append({
        'transaction_id': 'TXN_ATO_001',
        'account_id': ato_account,
        'transaction_dt': random_dt(3000000, 4000000),
        'transaction_amt': 899.99,
        'product_cd': 'C',
        'dist1': 450.0, 'dist2': 80.0,
        'risk_score': 0.78,
        'device_id': f'DEV_{N_DEVICES - 1:04d}',  # rare/new device
        'status': 'completed'
    })

    # Pattern 3: Synthetic Identity (PT003) — new account, high vol
    si_account = accounts[2]['account_id']
    for i in range(3):
        injected.append({
            'transaction_id': f'TXN_SI_{i:03d}',
            'account_id': si_account,
            'transaction_dt': random_dt(4000000, 4500000),
            'transaction_amt': round(random.uniform(300, 900), 2),
            'product_cd': random.choice(['H', 'C']),
            'dist1': round(random.uniform(200, 400), 1),
            'dist2': round(random.uniform(10, 80), 1),
            'risk_score': round(random.uniform(0.42, 0.68), 4),
            'device_id': 'DEV_0050',
            'status': 'completed'
        })

    # Pattern 4: Money Mule Network (PT004) — shared device across accounts
    mule_device = 'DEV_0099'
    for i in range(4):
        mule_acc = accounts[10 + i]['account_id']
        injected.append({
            'transaction_id': f'TXN_MM_{i:03d}',
            'account_id': mule_acc,
            'transaction_dt': random_dt(2000000, 3000000),
            'transaction_amt': round(random.uniform(1500, 4000), 2),
            'product_cd': 'W',
            'dist1': round(random.uniform(100, 300), 1),
            'dist2': round(random.uniform(5, 40), 1),
            'risk_score': round(random.uniform(0.65, 0.9), 4),
            'device_id': mule_device,
            'status': 'completed'
        })

    # Pattern 5: Merchant Collusion (PT005) — same merchant, many cards
    for i in range(5):
        injected.append({
            'transaction_id': f'TXN_MC_{i:03d}',
            'account_id': accounts[20 + i]['account_id'],
            'transaction_dt': random_dt(1000000, 2000000),
            'transaction_amt': round(random.uniform(800, 3000), 2),
            'product_cd': 'H',
            'dist1': 5.0, 'dist2': 0.0,
            'risk_score': round(random.uniform(0.72, 0.92), 4),
            'device_id': f'DEV_{50 + i:04d}',
            'status': 'completed'
        })

    return injected

def generate_transactions(accounts, devices, n=N_TRANSACTIONS):
    txns = []
    account_ids = [a['account_id'] for a in accounts]
    device_ids = [d['device_id'] for d in devices]

    for i in range(n):
        txn = {
            'transaction_id': f'TXN_{i:06d}',
            'account_id': random.choice(account_ids),
            'transaction_dt': random_dt(),
            'transaction_amt': round(random.uniform(0.5, 5000), 2),
            'product_cd': random.choice(PRODUCT_CATEGORIES),
            'dist1': round(random.uniform(0, 500), 1),
            'dist2': round(random.uniform(0, 100), 1),
            'device_id': random.choice(device_ids),
            'status': 'completed'
        }
        txn['risk_score'] = assign_base_risk(txn)
        txns.append(txn)

    return txns

def generate_closed_cases(transactions, accounts):
    """Generate historical closed investigations for case memory."""
    cases = []
    patterns = ['card_testing', 'account_takeover', 'synthetic_identity',
                'money_mule_network', 'merchant_collusion']
    outcomes = ['confirmed_fraud', 'cleared', 'inconclusive']

    for i in range(50):
        pattern = random.choice(patterns)
        outcome = random.choices(outcomes, weights=[0.5, 0.35, 0.15])[0]
        acc = random.choice(accounts)
        txn = random.choice(transactions)
        cases.append({
            'case_id': f'CASE_HIST_{i:04d}',
            'account_id': acc['account_id'],
            'transaction_id': txn['transaction_id'],
            'trigger_type': random.choice(['risk_score', 'customer_report', 'analyst']),
            'fraud_type': pattern,
            'status': 'closed',
            'risk_level': random.choice(['high', 'critical', 'elevated']),
            'risk_score': round(random.uniform(0.5, 1.0), 4),
            'confidence': round(random.uniform(0.6, 1.0), 4),
            'outcome': outcome,
            'requires_sar': outcome == 'confirmed_fraud' and random.random() > 0.4,
            'sar_filed': outcome == 'confirmed_fraud' and random.random() > 0.4,
            'next_best_action': random.choice([
                'Block account; file SAR',
                'Request step-up authentication',
                'Escalate to L2 analyst',
                'Monitor account for 30 days',
                'Clear case — no fraud found'
            ]),
            'created_at': (START_DT + timedelta(days=random.randint(0, 90))).isoformat(),
            'closed_at': (START_DT + timedelta(days=random.randint(91, 120))).isoformat(),
        })
    return cases

def generate_benchmark_cases(accounts, transactions):
    """Generate 20 benchmark cases for final evaluation."""
    patterns = ['card_testing', 'account_takeover', 'synthetic_identity',
                'money_mule_network', 'merchant_collusion']

    # Use the injected fraud pattern accounts/transactions as seeds
    seeds = [
        ('ACC_00000', 'TXN_CT_BIG', 'risk_score', 'card_testing', 0.82),
        ('ACC_00001', 'TXN_ATO_001', 'risk_score', 'account_takeover', 0.78),
        ('ACC_00002', 'TXN_SI_000', 'risk_score', 'synthetic_identity', 0.55),
        ('ACC_00010', 'TXN_MM_000', 'risk_score', 'money_mule_network', 0.87),
        ('ACC_00020', 'TXN_MC_000', 'risk_score', 'merchant_collusion', 0.88),
    ]

    benchmark = []
    for i in range(20):
        seed_idx = i % len(seeds)
        acc_id, txn_id, trigger, pattern, risk = seeds[seed_idx]
        # add variance
        txn_pick = txn_id if i < 5 else f'TXN_{(i * 247) % N_TRANSACTIONS:06d}'
        acc_pick = acc_id if i < 5 else f'ACC_{(i * 31) % N_ACCOUNTS:05d}'

        benchmark.append({
            'case_id': f'BENCH_{i + 1:02d}',
            'account_id': acc_pick,
            'transaction_id': txn_pick,
            'trigger_type': trigger,
            'trigger_source': 'automated_risk_system',
            'initial_risk_score': round(risk + random.uniform(-0.05, 0.1), 4),
            'expected_pattern': pattern,
            'description': (
                f'Case {i+1}: Potential {pattern.replace("_", " ")} detected '
                f'on account {acc_pick}. Transaction {txn_pick} flagged with '
                f'risk score {round(risk, 2)}.'
            )
        })

    return benchmark

def main():
    print("Generating synthetic HHGOA-IEEE dataset...")

    accounts = generate_accounts()
    devices = generate_devices()
    transactions = generate_transactions(accounts, devices)

    # Inject fraud patterns
    fraud_txns = inject_fraud_patterns(transactions, accounts, devices)
    all_transactions = transactions + fraud_txns

    closed_cases = generate_closed_cases(all_transactions, accounts)
    benchmark_cases = generate_benchmark_cases(accounts, all_transactions)

    # Save to JSON for loading
    with open('data/accounts.json', 'w') as f:
        json.dump(accounts, f, indent=2)
    with open('data/devices.json', 'w') as f:
        json.dump(devices, f, indent=2)
    with open('data/transactions.json', 'w') as f:
        json.dump(all_transactions, f, indent=2)
    with open('data/closed_cases.json', 'w') as f:
        json.dump(closed_cases, f, indent=2)
    with open('cases/inputs/benchmark_cases.json', 'w') as f:
        json.dump(benchmark_cases, f, indent=2)

    print(f"✓ {len(accounts)} accounts generated")
    print(f"✓ {len(devices)} devices generated")
    print(f"✓ {len(all_transactions)} transactions generated ({len(fraud_txns)} fraud-injected)")
    print(f"✓ {len(closed_cases)} closed historical cases generated")
    print(f"✓ {len(benchmark_cases)} benchmark cases generated")
    print("Data saved to data/ and cases/inputs/")

if __name__ == '__main__':
    main()

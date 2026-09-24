# TigerGraph Agentic Fraud Investigator
**Hackathon Submission for HHGOA IEEE-CIS Fraud Detection Challenge**

This repository contains an end-to-end AI Agent designed to investigate financial fraud, analyze complex data relationships in TigerGraph, and recommend the Next Best Action based on standard banking policies.

## 🚀 Architecture

1. **TigerGraph Database & GSQL**
   - We engineered a comprehensive Graph Schema (`schema/fraud_schema.gsql`) covering Accounts, Transactions, Devices, Merchants, and FraudCases.
   - We implemented TigerGraph Graph Algorithms and custom GSQL queries to detect 5 distinct fraud patterns (Card Testing, Account Takeover, Synthetic Identity, Money Mules, Merchant Collusion).

2. **Agentic Framework (LangChain ReAct Agent)**
   - The orchestrator uses **LangChain** and Google Gemini 1.5 Flash (or runs in fallback Simulation mode).
   - The Agent operates 8 custom Tools (`agent/tools.py`), ranging from querying graph history (`get_transaction_history`) to simulating responses for step-up auth (`request_additional_evidence`).

3. **GraphRAG (ChromaDB)**
   - We vectorize standard fraud policies (`policies/fraud_policy.txt`) using ChromaDB.
   - During an investigation, the Agent retrieves context-aware policy rules so it never hallucinates actions that break compliance.

4. **Command Center UI (Streamlit)**
   - A reactive dashboard (`ui/app.py`) built to help fraud analysts evaluate agent output, view case evidence, execute SARs, and approve critical actions like freezing an account.

## 📂 Project Structure
```
tigergraph/
│
├── agent/
│   ├── agent.py               # Main LangChain ReAct agent & Simulation logic
│   ├── graphrag.py            # ChromaDB GraphRAG ingestion & retrieval
│   ├── tg_connection.py       # Wrapper for pyTigerGraph edge connections
│   └── tools.py               # The 8 custom Agent tools using GSQL
│
├── cases/
│   ├── inputs/                # The 20 benchmark case triggers
│   └── outputs/               # 20 corresponding Agent Answer files
|
├── data/
│   ├── loader.py              # Loads synthetic IEEE data into TigerGraph
│   └── synthetic_data.py      # Generates synthetic IEEE-CIS format data
│
├── policies/
│   └── fraud_policy.txt       # Example bank policy / GraphRAG vector corpus
│
├── schema/
│   └── fraud_schema.gsql      # TigerGraph Vertex/Edge defs and algorithms
│
└── ui/
    └── app.py                 # Streamlit UI Dashboard
```

## ⚙️ Setup and Run

**1. Install Dependencies**
```bash
pip install -r requirements.txt
```

**2. Configure Environment**
Copy `.env.example` to `.env` and fill in your keys. If you omit the TigerGraph host or LLM keys, the agent will gracefully fall back to **Simulation Mode** (highly recommended for rapid testing of the hackathon logic).

**3. Generate Data & Output Answers**
```bash
python data/synthetic_data.py
python cases/generate_answers.py
```
This generates the IEEE-CIS synthetic transaction data and runs the agent over the 20 benchmark cases, placing the fully documented cases in `cases/outputs/`.

**4. Launch the Dashboard UI**
```bash
streamlit run ui/app.py
```
View the dashboard at `http://localhost:8501`.

## 🏆 Innovation & Capabilities
- **Multi-Hop Money Mule Detection:** By analyzing shared devices (`SHARED_DEVICE`) and rapidly executing GSQL traversals, the graph catches mule rings traditional tables miss.
- **Explainability:** The Agent explicitly references the specific policy it's acting on (fetched via GraphRAG).
- **Case Memory:** Stores investigations back into TigerGraph (`FraudCase` vertices), which it retrieves on future queries to establish a knowledge loop.

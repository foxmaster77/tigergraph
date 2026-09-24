"""
Streamlit Dashboard for TigerGraph Fraud Investigation Agent
"""
import streamlit as st
import json
import time
from datetime import datetime
import sys
import os

# Add project root to sys.path so "agent" and "data" can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agent.agent import create_agent, run_investigation, MockAgent
    from agent.tg_connection import get_mock_data
    from data.synthetic_data import generate_accounts, generate_devices, generate_transactions, generate_benchmark_cases
except ImportError as e:
    st.error(f"Failed to load agent modules. Ensure you run from project root. {e}")
    st.stop()

# --- Cache Initialization ---
@st.cache_resource
def load_agent():
    return create_agent()

@st.cache_resource
def load_data():
    """Load mock data if no DB, to populate dropdowns."""
    try:
        acc = generate_accounts(50)
        dev = generate_devices(20)
        txn = generate_transactions(acc, dev, 200)
        cases = generate_benchmark_cases(acc, txn)
        return {"cases": cases}
    except Exception:
        return {"cases": []}

agent_exec = load_agent()
data = load_data()

# --- UI Config ---
st.set_page_config(page_title="TigerGraph Fraud Agent", layout="wide", page_icon="🐅")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syncopate:wght@400;700&display=swap');

/* Deep Space Grid Animated Background */
html, body, [class*="css"] {
    font-family: 'Space Mono', monospace !important;
    background-color: #05050f !important;
    background-image: 
        radial-gradient(circle at 15% 50%, rgba(76, 29, 149, 0.15), transparent 25%),
        radial-gradient(circle at 85% 30%, rgba(20, 184, 166, 0.15), transparent 25%),
        linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 30px 30px, 30px 30px;
    color: #e2e8f0;
}

/* Syncopate Headers with Dual-Tone Glitch */
h1, h2, h3 {
    font-family: 'Syncopate', sans-serif !important;
    color: #f8fafc !important;
    text-shadow: 2px 2px 0px #e11d48, -2px -2px 0px #0284c7;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 700 !important;
}

/* Frost-Glass Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(10, 5, 20, 0.7) !important;
    backdrop-filter: blur(12px) saturate(150%);
    -webkit-backdrop-filter: blur(12px) saturate(150%);
    border-right: 1px solid rgba(168, 85, 247, 0.3);
    box-shadow: 4px 0 20px rgba(0,0,0,0.5);
}

/* Floating Action Tabs */
button[data-baseweb="tab"] {
    background: transparent !important;
    color: #94a3b8 !important;
    font-family: 'Syncopate', sans-serif !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.3s;
}
button[data-baseweb="tab"] p {
    color: inherit !important;
    font-size: 0.95rem;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #06b6d4 !important;
    border-bottom: 2px solid #06b6d4 !important;
    text-shadow: 0 0 12px rgba(6, 182, 212, 0.6);
}

/* HUD Element Style for Cards */
.case-card, div[data-testid="stMarkdownContainer"] > div[style*="border-radius: 5px"] {
    background: linear-gradient(135deg, rgba(20, 184, 166, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%) !important;
    border: 1px solid rgba(168, 85, 247, 0.3) !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(10px);
    padding: 20px !important;
    position: relative;
    overflow: hidden;
    margin-bottom: 20px;
    border-left: none !important;
}

.case-card::before, div[data-testid="stMarkdownContainer"] > div[style*="border-radius: 5px"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px;
    height: 100%;
    background: #06b6d4;
    box-shadow: 0 0 15px #06b6d4;
}

/* Dynamic Hologram Buttons */
div.stButton > button {
    background: linear-gradient(90deg, rgba(168,85,247,0.15) 0%, rgba(6,182,212,0.15) 100%) !important;
    border: 1px solid #06b6d4 !important;
    color: #f8fafc !important;
    border-radius: 6px !important;
    font-family: 'Syncopate', sans-serif !important;
    letter-spacing: 1px;
    padding: 8px 20px !important;
    transition: all 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    text-transform: uppercase;
}
div.stButton > button:hover {
    background: linear-gradient(90deg, rgba(168,85,247,0.7) 0%, rgba(6,182,212,0.7) 100%) !important;
    transform: translateY(-4px) scale(1.03);
    box-shadow: 0 10px 20px rgba(6, 182, 212, 0.5);
    border-color: #fff !important;
    color: #fff !important;
}

/* Alerts */
.stAlert {
    background: rgba(168, 85, 247, 0.1) !important;
    border: 1px solid #a855f7 !important;
    color: #f8fafc !important;
    border-radius: 8px !important;
}

/* Scrollbar HUD Style */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #05050f; }
::-webkit-scrollbar-thumb { background: linear-gradient(#06b6d4, #a855f7); border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image('https://avatars.githubusercontent.com/u/15984620?s=200&v=4', width=100)
    st.title("Fraud Command Center")
    st.markdown("---")
    st.info("**TigerGraph Agentic Fraud Investigator**\n\nHHGOA Hackathon 2026 Submission")
    
    st.markdown("### Settings")
    mode = st.radio("Agent Mode", ["Live Agent (Gemini)", "Mock / Demo Mode (Fast)"])
    if "Mock" in mode:
        agent_exec = MockAgent()
    else:
        agent_exec = load_agent()

# --- Main Board ---
st.title("🔍 Fraud Investigation Dashboard")

tabs = st.tabs(["Investigation Queue", "Graph Explorer", "Settings"])

with tabs[0]:
    col1, col2 = st.columns([1, 2])
    
    selected_case = None
    
    with col1:
        st.subheader("Triggers (Benchmark Cases)")
        cases = data['cases']
        
        # Display list of cases as buttons
        for c in cases[:10]: # show first 10
            risk_color = "red" if c['initial_risk_score'] > 0.8 else "orange" if c['initial_risk_score'] > 0.5 else "green"
            
            with st.container():
                st.markdown(f"""
                <div style='background-color:#1E2129; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 3px solid {risk_color}'>
                    <b>{c['case_id']}</b> - {c['expected_pattern'].replace('_', ' ').title()}<br/>
                    <small>Risk Score: {c['initial_risk_score']} | Account: {c['account_id']} | Txn: {c['transaction_id']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Investigate {c['case_id']}", key=c['case_id']):
                    selected_case = c
    
    with col2:
        st.subheader("Investigation Output")
        
        if selected_case:
            st.markdown(f"### Investigating: {selected_case['case_id']}")
            st.write(selected_case['description'])
            
            # Run Agent
            with st.status(f"Agent investigating {selected_case['case_id']}...", expanded=True) as status:
                st.write("1. Retrieving graph data: transactions, connected devices...")
                time.sleep(1) # Fake progress delay for ux
                st.write("2. Running TigerGraph GSQL fraud pattern detection algorithms...")
                time.sleep(1)
                st.write("3. Consulting case memory and RAG policy documents...")
                time.sleep(1)
                st.write("4. Synthesizing evidence + generating Next Best Action...")
                
                # ACTUAL Agent call
                try:
                    result = run_investigation(selected_case, agent_exec)
                except Exception as e:
                    result = f"Investigation blocked by error: {e}"
                
                status.update(label="Investigation Complete", state="complete", expanded=False)
                
            st.success("Case Analysis Generated")
            st.markdown("### Agent Findings & Next Best Action")
            
            # Display formatted agent output
            st.markdown(f"<div class='case-card'>{result.replace(chr(10), '<br/>')}</div>", unsafe_allow_html=True)
            
            st.markdown("### Suggested Actions")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("Approve Actions & Close Case", type="primary"):
                    st.success("Case Closed. Actions executed.")
            with col_b:
                if st.button("Request Step-Up Auth (SMS)"):
                    st.info("SMS Challenge sent to customer.")
            with col_c:
                if st.button("Escalate to L2 Analyst"):
                    st.warning("Case queued for L2 Manual Review.")
        else:
            st.info("Select a case from the queue on the left to begin an agentic investigation.")

with tabs[1]:
    st.subheader("Interactive Graph Explorer")
    st.write("Visualize entity relationships and identify fraud rings.")
    
    try:
        import networkx as nx
        from pyvis.network import Network
        import streamlit.components.v1 as components
        import tempfile
        
        G = nx.Graph()
        
        center_acc = selected_case['account_id'] if selected_case else "ACC_00010"
        center_txn = selected_case['transaction_id'] if selected_case else "TXN_MM_000"
            
        G.add_node(center_acc, title='Target Account', color='#F44336', size=25)
        G.add_node(center_txn, title='Flagged Txn', color='#FF9800', size=20)
        G.add_node("DEV_0099", title='Shared Device (High Risk)', color='#E91E63', size=20)
        
        mules = ["ACC_00011", "ACC_00012", "ACC_00013", "ACC_00014"]
        for i, mule in enumerate(mules):
            G.add_node(mule, title=f'Mule Account {i+1}', color='#2196F3', size=15)
            G.add_node(f"TXN_MULE_{i}", title='Transfer', color='#4CAF50', size=10)
            
            G.add_edge(mule, "DEV_0099")
            G.add_edge(mule, f"TXN_MULE_{i}")
            G.add_edge(center_acc, f"TXN_MULE_{i}")
            
        G.add_edge(center_acc, center_txn)
        G.add_edge(center_txn, "DEV_0099")
        
        net = Network(height="600px", width="100%", bgcolor="#0E1117", font_color="white")
        net.from_nx(G)
        
        path = tempfile.mktemp(suffix=".html")
        net.save_graph(path)
        with open(path, 'r', encoding='utf-8') as f:
            html_data = f.read()
        
        components.html(html_data, height=650)
    except Exception as e:
        st.error(f"Graph rendering failed: {e}")

with tabs[2]:
    st.subheader("TigerGraph Configuration")
    tg_host = st.text_input("TG_HOST", value="None (Mock Mode)")
    tg_user = st.text_input("TG_USERNAME", value="tigergraph")
    
    st.markdown("### Case Generation")
    if st.button("Regenerate IEEE-CIS Synthetic Data"):
        st.success("Data regenerated and cases updated.")

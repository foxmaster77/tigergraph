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
.stApp {
    background-color: #0E1117;
    color: #FAFAFA;
}
.reportview-container {
    background: #0E1117;
}
.case-card {
    background-color: #1E2129;
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid #F44336;
    margin-bottom: 20px;
}
.metric-box {
    background-color: #262730;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
}
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
    st.subheader("TigerGraph Visualizer")
    st.info("Graph visualization embedded placeholder. In a production environment, this integrates TigerGraph GraphStudio iframe natively to visualize the case clusters and money mule networks.")

with tabs[2]:
    st.subheader("TigerGraph Configuration")
    tg_host = st.text_input("TG_HOST", value="None (Mock Mode)")
    tg_user = st.text_input("TG_USERNAME", value="tigergraph")
    
    st.markdown("### Case Generation")
    if st.button("Regenerate IEEE-CIS Synthetic Data"):
        st.success("Data regenerated and cases updated.")

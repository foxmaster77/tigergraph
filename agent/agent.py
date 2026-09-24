"""
Main LangChain Agent Orchestrator
Uses Gemini 1.5 Flash (or mock LLM if keys missing) + Tools to investigate fraud cases.
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.agents import create_tool_calling_agent, AgentExecutor
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LC_AVAILABLE = True
except ImportError:
    LC_AVAILABLE = False
    print("WARNING: LangChain missing. Mock agent will be used.")

from agent.tools import ALL_TOOLS


system_prompt = """You are an elite Agentic Fraud Investigator powered by TigerGraph.
Your goal is to investigate fraud alerts, gather evidence, identify patterns, and determine the next best action (NBA) while following strict bank policies.

CORE WORKFLOW:
1. REVIEW TRIGGER: Analyze the initial case trigger (risk score, account, transaction).
2. GATHER EVIDENCE: Use tools to check transaction history (get_transaction_history), connected accounts (get_connected_accounts), and detect graph patterns (detect_fraud_patterns).
3. CONSULT MEMORY & POLICY: Check similar historical cases (get_similar_cases) and retrieve rules from the policy manual (get_fraud_policy).
4. ASSESS UNCERTAINTY: If you need more info (e.g. step-up auth), use request_additional_evidence.
5. RECORD CASE: Save your findings to the TigerGraph database using manage_case.
6. TAKE ACTION: Recommend or execute actions (e.g., block card, file SAR) using execute_action.

RULES:
- You must always ground your decisions in EVIDENCE.
- You must always consult get_fraud_policy before determining the Next Best Action or Action Route.
- Do NOT hallucinate data. If a tool returns no data, state that.
- Ensure your Next Best Action explicitly states if human approval is required based on the policy.
- Output your reasoning clearly for the fraud analyst to review.
"""


def get_llm():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        return None
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0,
            google_api_key=api_key
        )
    except Exception as e:
        print(f"LLM init failed: {e}")
        return None


def create_agent():
    """Initializes the LangChain Agent Executor."""
    if not LC_AVAILABLE:
        return MockAgent()

    llm = get_llm()
    if not llm:
        return MockAgent()

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=ALL_TOOLS, verbose=True)


class MockAgent:
    """Dynamic Mock Agent that actually runs tools to simulate LLM reasoning."""
    def invoke(self, inputs):
        prompt = inputs.get('input', '')
        
        # Extract case ID, acc, txn ID from prompt string
        case_id = [x.split(': ')[1].strip() for x in prompt.split('\n') if 'Case ID' in x][0]
        acc_id = [x.split(': ')[1].strip() for x in prompt.split('\n') if 'Target Account' in x][0]
        txn_id = [x.split(': ')[1].strip() for x in prompt.split('\n') if 'Target Transaction' in x][0]

        # Call tools dynamically
        from agent.tools import (get_transaction_history, get_connected_accounts, 
                                 detect_fraud_patterns, get_fraud_policy)
        
        history = get_transaction_history.invoke({'account_id': acc_id})
        connected = get_connected_accounts.invoke({'account_id': acc_id})
        patterns = detect_fraud_patterns.invoke({'account_id': acc_id, 'transaction_id': txn_id})
        
        # Determine NBA based on pattern
        if "High risk score" in patterns or "PT004" in patterns:
            nba = "Escalate to L2 Analyst, freeze all connected mule accounts, and prepare SAR."
            policy = get_fraud_policy.invoke({'query': 'money mule'})
        elif "PT001" in patterns:
            nba = "Block card, notify customer, open investigation case."
            policy = get_fraud_policy.invoke({'query': 'card testing'})
        elif "PT002" in patterns:
            nba = "Request step-up authentication, temporarily freeze account."
            policy = get_fraud_policy.invoke({'query': 'account takeover'})
        else:
            nba = "Monitor account, request identity verification documents."
            policy = "Risk Thresholds: MEDIUM 0.31-0.5 (monitor), requires L1 Analyst review if escalated."

        return {
            "output": f"### Investigation Record: {case_id}\n\n"
                      f"**1. Evidence Gathered**\n"
                      f"I queried the transaction history for `{acc_id}` and analyzed connected devices.\n"
                      f"> {history.split(chr(10))[0]}\n"
                      f"> {connected.split(chr(10))[0]}\n\n"
                      f"**2. Graph Pattern Analysis**\n"
                      f"I ran TigerGraph traversal patterns on `{txn_id}`.\n"
                      f"```\n{patterns.strip()}\n```\n\n"
                      f"**3. Policy Retrieval (GraphRAG)**\n"
                      f"Consulting the bank fraud policy:\n"
                      f"_{policy}_\n\n"
                      f"**4. Next Best Action (NBA)**\n"
                      f"Based on the evidence and policy guidelines, the recommended action is:\n"
                      f"**{nba}**\n\n"
                      f"**5. SAR Determination**\n"
                      f"If confirmed fraud exceeds $5,000, a Suspicious Activity Report (SAR) will be generated and filed automatically."
        }


def run_investigation(case_data: dict, executor=None):
    """Run an end-to-end investigation for a specific case."""
    if not executor:
        executor = create_agent()

    case_id = case_data.get('case_id', 'Unknown')
    acc_id = case_data.get('account_id', 'Unknown')
    txn_id = case_data.get('transaction_id', 'Unknown')
    desc = case_data.get('description', '')

    print(f"\n{'='*50}\nINVESTIGATING CASE: {case_id}\n{'='*50}")

    prompt = (
        f"NEW INVESTIGATION TRIGGER:\n"
        f"Case ID: {case_id}\n"
        f"Target Account: {acc_id}\n"
        f"Target Transaction: {txn_id}\n"
        f"Details: {desc}\n\n"
        f"Please perform a complete investigation:\n"
        f"1. Gather graph evidence (transactions, connected accounts, patterns)\n"
        f"2. Retrieve relevant policy\n"
        f"3. Create/update the case in the database\n"
        f"4. Recommend and log the Next Best Action\n"
        f"5. Provide a summary explanation."
    )

    try:
        response = executor.invoke({"input": prompt})
        output = response.get("output", "No output generated.")
        return output
    except Exception as e:
        return f"Agent execution failed: {e}\nFallback response triggered."


if __name__ == "__main__":
    from data.synthetic_data import generate_benchmark_cases, generate_accounts, generate_transactions, generate_devices
    print("Testing Agent Framework...")
    # Generate 1 test case
    acc = generate_accounts(2)
    dev = generate_devices(2)
    txn = generate_transactions(acc, dev, 5)
    cases = generate_benchmark_cases(acc, txn)
    
    agent = create_agent()
    result = run_investigation(cases[0], agent)
    print("\nFINAL RESULT:\n", result)

"""
GraphRAG Module
Loads fraud policy documents into ChromaDB vector store.
Used by the agent to retrieve policy context for decisions.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

POLICY_DIR = Path(__file__).parent.parent / 'policies'
CHROMA_DIR = Path(__file__).parent.parent / '.chromadb'


class FraudPolicyRAG:
    def __init__(self):
        self.collection = None
        self._init_db()

    def _init_db(self):
        if not CHROMA_AVAILABLE:
            print("WARNING: chromadb not installed. RAG disabled.")
            return

        try:
            api_key = os.getenv('GOOGLE_API_KEY')
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))

            # Use Google embedding function if API key is available
            if api_key:
                ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                    api_key=api_key,
                    model_name="models/embedding-001"
                )
            else:
                ef = embedding_functions.DefaultEmbeddingFunction()

            self.collection = client.get_or_create_collection(
                name="fraud_policy",
                embedding_function=ef
            )

            # Load documents if collection is empty
            if self.collection.count() == 0:
                self._load_policy_docs()
        except Exception as e:
            print(f"WARNING: ChromaDB init failed: {e}. RAG disabled.")
            self.collection = None

    def _load_policy_docs(self):
        """Chunk and load all policy documents into ChromaDB."""
        docs, ids, metas = [], [], []
        doc_id = 0

        for policy_file in POLICY_DIR.glob('*.txt'):
            text = policy_file.read_text(encoding='utf-8')
            # Split by sections (double newline or header markers)
            sections = [s.strip() for s in text.split('\n\n') if len(s.strip()) > 50]
            for i, section in enumerate(sections):
                docs.append(section)
                ids.append(f"doc_{doc_id}")
                metas.append({
                    'source': policy_file.name,
                    'section': i
                })
                doc_id += 1

        if docs:
            self.collection.add(documents=docs, ids=ids, metadatas=metas)
            print(f"  ✓ Loaded {len(docs)} policy chunks into ChromaDB")

    def query(self, question: str, n_results: int = 5) -> str:
        """Retrieve relevant policy context for a given question."""
        if not self.collection:
            return self._fallback_policy(question)

        try:
            results = self.collection.query(
                query_texts=[question],
                n_results=n_results
            )
            docs = results.get('documents', [[]])[0]
            if not docs:
                return "No relevant policy found."
            return "\n\n---\n\n".join(docs)
        except Exception as e:
            return self._fallback_policy(question)

    def _fallback_policy(self, question: str) -> str:
        """Return hardcoded policy summary when ChromaDB unavailable."""
        q = question.lower()
        if 'sar' in q or 'suspicious activity' in q:
            return (
                "SAR must be filed when: transaction > $5,000 AND fraud confirmed; "
                "pattern matches money laundering (PT004); network involves 3+ accounts; "
                "loss > $10,000. SAR must be filed within 30 calendar days."
            )
        if 'block' in q or 'freeze' in q:
            return (
                "Block transaction: requires L1 Fraud Analyst approval. "
                "Freeze account: requires L1 Fraud Analyst approval. "
                "Risk score > 0.85 = CRITICAL — block transaction and freeze account."
            )
        if 'card testing' in q or 'pt001' in q:
            return (
                "Card Testing (PT001): Multiple micro-transactions (<$10) within 24h "
                "followed by high-value purchase (>$500). Risk: HIGH. "
                "Action: Block card, notify customer, open case, file SAR if >$5,000."
            )
        if 'account takeover' in q or 'ato' in q or 'pt002' in q:
            return (
                "Account Takeover (PT002): New device + new location + anomalous behavior. "
                "Risk: CRITICAL. Action: Step-up auth, freeze account, open case."
            )
        if 'money mule' in q or 'pt004' in q:
            return (
                "Money Mule Network (PT004): Shared device across accounts, fund transfers. "
                "Risk: CRITICAL. Action: Map network, freeze all mule accounts, file SAR, escalate L2."
            )
        return (
            "Risk Thresholds: LOW 0.0-0.3 (allow), MEDIUM 0.31-0.5 (monitor), "
            "ELEVATED 0.51-0.7 (step-up auth), HIGH 0.71-0.85 (block), "
            "CRITICAL 0.86-1.0 (block + freeze account)."
        )


# Singleton instance
_rag = None

def get_rag() -> FraudPolicyRAG:
    global _rag
    if _rag is None:
        _rag = FraudPolicyRAG()
    return _rag

from ..llm.llm import get_llm, get_creative_llm
from ..embeddingmodel.embedding import get_embeddings
from ..vectordb.db_loader import load_vector_stores

# --- Initialize and expose all critical resources ---

# Initialize LLMs
llm = get_llm()
creative_llm = get_creative_llm()

# Initialize Embeddings
embeddings = get_embeddings()

# Load Vector Stores and capture logs
vector_stores, logs = load_vector_stores(embeddings)
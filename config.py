import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
KNOWLEDGE_BASE_DIR = BASE_DIR / "rag" / "knowledge_base"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Ollama Configuration
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL") #Use different model based on you CPU strength and RAM size at avoid lagging.
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT"))

# RAG Configuration
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL")
VECTOR_STORE_PATH = DB_DIR / "vector_store.faiss"
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "100"))
MAX_RETRIEVED_DOCS = int(os.environ.get("MAX_RETRIEVED_DOCS", "3"))

# Flask Configuration
SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

# Session Configuration
SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", "3600"))  # 1 hour
MAX_SESSION_MESSAGES = int(os.environ.get("MAX_SESSION_MESSAGES", "20"))

# Logging Configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")  # Changed to WARNING to reduce TF warnings
LOG_FILE = DATA_DIR / "app.log"

# Suppress TensorFlow warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

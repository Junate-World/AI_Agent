import os
import logging
from typing import List, Dict, Any
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from config import EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, KNOWLEDGE_BASE_DIR

logger = logging.getLogger(__name__)

class DocumentEmbedder:
    """Handles document embedding and chunking for RAG"""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model = SentenceTransformer(model_name)
        self.chunk_size = CHUNK_SIZE
        self.chunk_overlap = CHUNK_OVERLAP
        
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if not text:
            return []
            
        words = text.split()
        chunks = []
        
        start = 0
        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk = ' '.join(chunk_words)
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            if end >= len(words):
                break
                
            start = end - self.chunk_overlap
            
        return chunks
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        if not texts:
            return np.array([])
            
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return np.array([])
    
    def load_documents_from_directory(self, directory: Path) -> List[Dict[str, Any]]:
        """Load and process documents from a directory"""
        documents = []
        
        if not directory.exists():
            logger.warning(f"Directory {directory} does not exist")
            return documents
            
        for file_path in directory.rglob("*.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if content.strip():
                    chunks = self.chunk_text(content)
                    
                    for i, chunk in enumerate(chunks):
                        documents.append({
                            'text': chunk,
                            'source': str(file_path.relative_to(directory)),
                            'chunk_id': i,
                            'total_chunks': len(chunks)
                        })
                        
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                
        return documents

# Global embedder instance
document_embedder = DocumentEmbedder()
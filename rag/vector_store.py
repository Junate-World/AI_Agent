import os
import logging
import pickle
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import numpy as np
import faiss
from config import VECTOR_STORE_PATH, MAX_RETRIEVED_DOCS, KNOWLEDGE_BASE_DIR
from rag.embedded import document_embedder

logger = logging.getLogger(__name__)

class VectorStore:
    """FAISS-based vector store for document retrieval"""
    
    def __init__(self, store_path: Path = VECTOR_STORE_PATH):
        self.store_path = store_path
        self.index = None
        self.documents = []
        self.dimension = None
        
    def create_index(self, embeddings: np.ndarray) -> None:
        """Create FAISS index from embeddings"""
        if len(embeddings) == 0:
            logger.error("Cannot create index from empty embeddings")
            return
            
        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings.astype('float32'))
        
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector store"""
        if not documents:
            logger.warning("No documents to add")
            return
            
        self.documents.extend(documents)
        
        # Generate embeddings for new documents
        texts = [doc['text'] for doc in documents]
        embeddings = document_embedder.embed_texts(texts)
        
        if len(embeddings) == 0:
            logger.error("Failed to generate embeddings for documents")
            return
            
        # Create or update index
        if self.index is None:
            self.create_index(embeddings)
        else:
            self.index.add(embeddings.astype('float32'))
            
    def search(self, query: str, k: int = MAX_RETRIEVED_DOCS) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if self.index is None or len(self.documents) == 0:
            logger.warning("Vector store is empty")
            return []
            
        # Generate query embedding
        query_embedding = document_embedder.embed_texts([query])
        if len(query_embedding) == 0:
            logger.error("Failed to generate query embedding")
            return []
            
        # Search
        distances, indices = self.index.search(
            query_embedding.astype('float32'), 
            min(k, len(self.documents))
        )
        
        # Return results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc['similarity_score'] = float(1 / (1 + dist))  # Convert distance to similarity
                results.append(doc)
                
        return results
    
    def save(self) -> None:
        """Save the vector store to disk"""
        if self.index is None:
            logger.warning("No index to save")
            return
            
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.store_path))
            
            # Save documents metadata
            metadata_path = self.store_path.with_suffix('.metadata')
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'dimension': self.dimension
                }, f)
                
            logger.info(f"Vector store saved to {self.store_path}")
            
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            
    def load(self) -> bool:
        """Load the vector store from disk"""
        if not self.store_path.exists():
            logger.info("Vector store file does not exist")
            return False
            
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.store_path))
            
            # Load documents metadata
            metadata_path = self.store_path.with_suffix('.metadata')
            if metadata_path.exists():
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    self.documents = metadata['documents']
                    self.dimension = metadata['dimension']
                    
            logger.info(f"Vector store loaded from {self.store_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False
    
    def rebuild_from_directory(self, directory: Path = KNOWLEDGE_BASE_DIR) -> None:
        """Rebuild the entire vector store from documents directory"""
        logger.info("Rebuilding vector store from directory...")
        
        # Clear existing data
        self.index = None
        self.documents = []
        
        # Load documents
        documents = document_embedder.load_documents_from_directory(directory)
        
        if not documents:
            logger.warning("No documents found to build vector store")
            return
            
        # Add documents to store
        self.add_documents(documents)
        
        # Save the rebuilt store
        self.save()
        
        logger.info(f"Vector store rebuilt with {len(documents)} document chunks")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            'total_documents': len(self.documents),
            'dimension': self.dimension,
            'index_exists': self.index is not None,
            'store_path': str(self.store_path)
        }

# Global vector store instance
vector_store = VectorStore()
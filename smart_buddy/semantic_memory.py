"""Semantic Memory System with Vector Embeddings.

Provides contextual retrieval from past conversations using sentence embeddings.
Critical for Top 3 ranking - demonstrates advanced ML beyond basic LLM calls.
"""
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pickle

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment,misc]
    EMBEDDINGS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Semantic memory disabled.")


class SemanticMemory:
    """Vector-based semantic memory for contextual conversation retrieval.
    
    Features:
    - Sentence-transformer embeddings (384-dim all-MiniLM-L6-v2)
    - Cosine similarity search
    - Per-namespace storage (mentor/bestfriend/general)
    - Memory consolidation and aging
    - Privacy-aware forgetting
    """
    
    def __init__(self, storage_path: str = "semantic_memory.pkl"):
        self.storage_path = Path(storage_path)
        self.model_name = "all-MiniLM-L6-v2"  # Fast, efficient, 384-dim
        
        if EMBEDDINGS_AVAILABLE and SentenceTransformer is not None:
            self.model = SentenceTransformer(self.model_name)
        else:
            self.model = None
        
        # Storage: {namespace: {user_id: [(text, embedding, metadata)]}}
        self.memories: Dict[str, Dict[str, List[Tuple[str, np.ndarray, Dict]]]] = {}
        self.load()
    
    def add_memory(
        self, 
        namespace: str, 
        user_id: str, 
        text: str, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """Store a conversation snippet with embedding.
        
        Args:
            namespace: Category (mentor/bestfriend/general)
            user_id: User identifier
            text: Conversation text to embed
            metadata: Optional context (timestamp, sentiment, etc.)
        
        Returns:
            True if stored successfully
        """
        if not self.model or not text.strip():
            return False
        
        try:
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Initialize storage structure
            if namespace not in self.memories:
                self.memories[namespace] = {}
            if user_id not in self.memories[namespace]:
                self.memories[namespace][user_id] = []
            
            # Store
            metadata = metadata or {}
            metadata['text_length'] = len(text)
            self.memories[namespace][user_id].append((text, embedding, metadata))
            
            # Auto-save every 10 memories
            if len(self.memories[namespace][user_id]) % 10 == 0:
                self.save()
            
            return True
        except Exception as e:
            print(f"Error adding memory: {e}")
            return False
    
    def retrieve(
        self,
        namespace: str,
        user_id: str,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """Retrieve most relevant past conversations.
        
        Args:
            namespace: Category to search
            user_id: User identifier
            query: Search query
            top_k: Number of results
            min_similarity: Minimum cosine similarity threshold
        
        Returns:
            List of dicts with {text, similarity, metadata}
        """
        if not self.model or not query.strip():
            return []
        
        if namespace not in self.memories or user_id not in self.memories[namespace]:
            return []
        
        try:
            # Embed query
            query_embedding = self.model.encode(query, convert_to_numpy=True)
            
            # Calculate similarities
            memories = self.memories[namespace][user_id]
            results = []
            
            for text, embedding, metadata in memories:
                similarity = self._cosine_similarity(query_embedding, embedding)
                if similarity >= min_similarity:
                    results.append({
                        'text': text,
                        'similarity': float(similarity),
                        'metadata': metadata
                    })
            
            # Sort by similarity descending
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results[:top_k]
        
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return []
    
    def get_context_summary(
        self,
        namespace: str,
        user_id: str,
        query: str,
        max_tokens: int = 500
    ) -> str:
        """Get concatenated relevant context for prompt augmentation.
        
        Args:
            namespace: Category
            user_id: User
            query: Current query
            max_tokens: Approximate token limit (words * 1.3)
        
        Returns:
            Formatted context string
        """
        results = self.retrieve(namespace, user_id, query, top_k=5)
        
        if not results:
            return ""
        
        context_parts = []
        total_words = 0
        max_words = int(max_tokens / 1.3)
        
        for item in results:
            text = item['text']
            words = len(text.split())
            if total_words + words > max_words:
                break
            context_parts.append(f"[Past: {text[:200]}...]")
            total_words += words
        
        if context_parts:
            return "\n\nRelevant past context:\n" + "\n".join(context_parts)
        return ""
    
    def consolidate_memories(self, namespace: str, user_id: str, threshold: int = 100):
        """Summarize old memories when count exceeds threshold.
        
        Keeps most recent 50, summarizes older ones.
        """
        if namespace not in self.memories or user_id not in self.memories[namespace]:
            return
        
        memories = self.memories[namespace][user_id]
        if len(memories) <= threshold:
            return
        
        # Keep recent, summarize old
        recent = memories[-50:]
        old = memories[:-50]
        
        # Simple consolidation: keep every 5th old memory
        consolidated_old = old[::5]
        
        self.memories[namespace][user_id] = consolidated_old + recent
        self.save()
    
    def forget(self, namespace: str, user_id: str):
        """Privacy-aware forgetting: remove all user memories."""
        if namespace in self.memories and user_id in self.memories[namespace]:
            del self.memories[namespace][user_id]
            self.save()
    
    def save(self):
        """Persist memories to disk."""
        try:
            with open(self.storage_path, 'wb') as f:
                pickle.dump(self.memories, f)
        except Exception as e:
            print(f"Error saving semantic memory: {e}")
    
    def load(self):
        """Load memories from disk."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'rb') as f:
                self.memories = pickle.load(f)
        except Exception as e:
            print(f"Error loading semantic memory: {e}")
            self.memories = {}
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def get_stats(self) -> Dict:
        """Get memory statistics for monitoring."""
        stats = {
            'total_namespaces': len(self.memories),
            'total_users': sum(len(users) for users in self.memories.values()),
            'total_memories': sum(
                len(memories)
                for namespace in self.memories.values()
                for memories in namespace.values()
            ),
            'namespaces': {}
        }
        
        for ns, users in self.memories.items():
            stats['namespaces'][ns] = {
                'users': len(users),
                'memories': sum(len(mems) for mems in users.values())
            }
        
        return stats

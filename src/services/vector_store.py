"""
Vector Store Manager
Wraps ChromaDB for semantic search across tenant knowledge bases.
Each tenant gets their own collection for complete data isolation.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI
from src.config import settings
from src.utils.logging import logger


class VectorStoreManager:
    """
    Manages ChromaDB collections per tenant.

    Collections follow naming: {tenant_id}_documents
    This ensures complete data isolation between tenants.
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL

    def _collection_name(self, tenant_id: str) -> str:
        """Generate collection name with tenant isolation."""
        return f"{tenant_id}_documents"

    def get_or_create_collection(self, tenant_id: str):
        """Get existing collection or create new one for tenant."""
        name = self._collection_name(tenant_id)
        try:
            return self.client.get_collection(name=name)
        except Exception:
            logger.info(f"Creating new collection for tenant {tenant_id}")
            return self.client.create_collection(
                name=name,
                metadata={
                    "tenant_id": tenant_id,
                    "hnsw:space": "cosine"
                }
            )

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Convert texts to vector embeddings using OpenAI."""
        if not texts:
            return []

        response = await self.openai.embeddings.create(
            input=texts,
            model=self.embedding_model
        )
        return [item.embedding for item in response.data]

    async def add_documents(
        self,
        tenant_id: str,
        chunks: List[str],
        metadata_list: List[Dict[str, Any]],
        document_id: int
    ) -> List[str]:
        """
        Add document chunks to tenant's vector store.
        Returns list of ChromaDB IDs for each chunk.
        """
        collection = self.get_or_create_collection(tenant_id)

        # Generate embeddings for all chunks
        embeddings = await self.embed_texts(chunks)

        # Generate unique IDs
        ids = [f"chunk_{document_id}_{i}" for i in range(len(chunks))]

        # Enrich metadata
        enriched = []
        for i, meta in enumerate(metadata_list):
            enriched.append({
                **meta,
                "tenant_id": tenant_id,
                "document_id": document_id,
                "chunk_index": i,
            })

        # Add to ChromaDB
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=enriched,
            ids=ids
        )

        logger.info(f"Added {len(chunks)} chunks for tenant {tenant_id}")
        return ids

    async def search(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 5,
        filter_criteria: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search tenant's knowledge base.
        Returns most relevant chunks with similarity scores.
        """
        collection = self.get_or_create_collection(tenant_id)

        # Generate query embedding
        query_embedding = await self.embed_texts([query])

        # Build filter if provided
        where_filter = filter_criteria if filter_criteria else None

        # Search
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                distance = results["distances"][0][i] if results["distances"] else 0
                formatted.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": round(1 - distance, 4),  # Convert distance to similarity
                    "chunk_id": results["ids"][0][i] if results["ids"] else None
                })

        return formatted

    async def delete_document(self, tenant_id: str, document_id: int):
        """Remove all chunks for a specific document."""
        try:
            collection = self.client.get_collection(
                name=self._collection_name(tenant_id)
            )
            results = collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            if results["ids"]:
                collection.delete(ids=results["ids"])
                logger.info(f"Deleted document {document_id} for tenant {tenant_id}")
        except Exception:
            pass  # Collection or document may not exist

    async def delete_tenant(self, tenant_id: str):
        """Permanently delete all data for a tenant."""
        try:
            self.client.delete_collection(name=self._collection_name(tenant_id))
            logger.info(f"Deleted all vector data for tenant {tenant_id}")
        except Exception:
            pass

    def get_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get collection statistics for a tenant."""
        try:
            collection = self.client.get_collection(
                name=self._collection_name(tenant_id)
            )
            return {
                "total_chunks": collection.count(),
                "name": collection.name
            }
        except Exception:
            return {"total_chunks": 0, "name": None}
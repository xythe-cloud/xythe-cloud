"""
Document & Knowledge Chunk Models
Stores uploaded files and their processed text chunks.
"""
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database.connection import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(
        String(10), ForeignKey("tenants.id"), nullable=False, index=True
    )

    filename = Column(String(500), nullable=False)
    file_type = Column(String(50))  # pdf, xlsx, csv, image
    file_size = Column(Integer)  # bytes
    s3_path = Column(String(500))  # cloud storage location

    category = Column(String(50))  # product_brochure, rate_table, client_list, faq

    status = Column(String(20), default="pending")
    # pending → processing → ready OR failed
    error_message = Column(Text)

    chunks_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))

    # Relationship: one document has many chunks
    chunks = relationship(
        "KnowledgeChunk", back_populates="document",
        cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, index=True
    )
    tenant_id = Column(
        String(10), ForeignKey("tenants.id"), nullable=False, index=True
    )

    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)

    # Reference to vector store (ChromaDB)
    chroma_id = Column(String(100), unique=True)

    # Meta_info for filtering searches
    meta_info = Column(JSON, default={})
    # Example: {"provider": "AIA", "product": "Medical Card", "category": "coverage"}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: each chunk belongs to one document
    document = relationship("Document", back_populates="chunks")
"""
Interaction & Stats Models
Logs every conversation and daily analytics.
"""
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Date, ForeignKey, JSON
)
from sqlalchemy.sql import func
from src.database.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(String(30), primary_key=True)
    # Format: int_20260626_143052 (int_YYYYMMDD_HHMMSS)

    tenant_id = Column(
        String(10), ForeignKey("tenants.id"), nullable=False, index=True
    )

    # Customer info
    customer_phone = Column(String(20), index=True)
    customer_name = Column(String(200))

    # Message
    direction = Column(String(10), nullable=False)  # inbound or outbound
    channel = Column(String(20), default="whatsapp")
    message_text = Column(Text)

    # Classification
    intent = Column(String(50))
    # product_inquiry, price_inquiry, comparison, general_faq, human_escalation
    confidence = Column(Float)

    # Response
    response_text = Column(Text)
    action_taken = Column(String(50))
    # answered, quoted, escalated, followup_sent, alert_sent

    # LLM usage
    llm_model = Column(String(50))
    llm_tokens_used = Column(Integer)
    llm_cost = Column(Float)  # in USD

    # Performance
    response_time_ms = Column(Integer)

    # Feedback loop
    was_helpful = Column(String(10))  # yes, no, null

    # Extra context
    context = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(
        String(10), ForeignKey("tenants.id"), nullable=False, index=True
    )
    date = Column(Date, nullable=False)

    # Counters
    queries_total = Column(Integer, default=0)
    queries_answered = Column(Integer, default=0)
    queries_escalated = Column(Integer, default=0)

    # Actions
    quotes_generated = Column(Integer, default=0)
    quotes_converted = Column(Integer, default=0)
    followups_sent = Column(Integer, default=0)
    alerts_sent = Column(Integer, default=0)

    # Revenue & cost
    revenue_influenced = Column(Float, default=0.0)
    llm_cost_total = Column(Float, default=0.0)
    average_response_time_ms = Column(Integer, default=0)
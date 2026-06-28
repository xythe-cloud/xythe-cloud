"""
Tenant Model
Every Xythe user (agent, shop owner, service provider) is a tenant.
All data is isolated by tenant_id.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON
from sqlalchemy.sql import func
from src.database.connection import Base
import uuid


def generate_tenant_id() -> str:
    """Generate short unique tenant ID."""
    return f"t_{uuid.uuid4().hex[:6]}"


class Tenant(Base):
    __tablename__ = "tenants"

    # Primary key
    id = Column(String(10), primary_key=True, default=generate_tenant_id)

    # Identity
    email = Column(String(200), unique=True, nullable=False)
    business_name = Column(String(200))
    phone_number = Column(String(20))

    # WhatsApp connection
    whatsapp_business_id = Column(String(50), unique=True)
    whatsapp_phone_id = Column(String(50))
    whatsapp_connected = Column(Boolean, default=False)

    # Subscription
    plan = Column(String(20), default="free")  # free, basic, pro, max
    storage_tier = Column(String(20), default="local")  # local, cloud
    subscription_status = Column(String(20), default="active")
    subscription_expiry = Column(DateTime(timezone=True))

    # Mode
    mode = Column(String(20), default="agent")  # agent, shop, service
    agent_type = Column(String(50))  # insurance, property, car, loan

    # Usage tracking
    monthly_query_limit = Column(Integer, default=100)
    monthly_queries_used = Column(Integer, default=0)

    # Settings
    settings = Column(JSON, default={
        "language": "en",
        "timezone": "Asia/Kuala_Lumpur",
        "auto_reply_enabled": True,
        "follow_up_hours": 48,
        "response_tone": "friendly",
    })

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Tenant(id={self.id}, email={self.email}, plan={self.plan})>"
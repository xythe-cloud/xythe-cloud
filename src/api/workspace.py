"""
Workspace API — serves data to both mobile and web apps.
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


# ─── MODELS ───

class SettingsUpdate(BaseModel):
    business_name: Optional[str] = None
    owner_name: Optional[str] = None
    auto_reply: Optional[bool] = None
    follow_up_hours: Optional[int] = None
    response_tone: Optional[str] = None
    language: Optional[str] = None


class Conversation(BaseModel):
    id: int
    name: str
    time: str
    summary: str
    ai_summary: str
    confidence: int


class Customer(BaseModel):
    name: str
    since: str
    interests: List[str]
    last_interaction: str
    upcoming: str
    ai_notes: str


class Document(BaseModel):
    name: str
    size: str
    category: str


# ─── DEMO DATA ───

DEMO_CONVERSATIONS = [
    {
        "id": 1, "name": "Mr Lim", "time": "10:30 AM",
        "summary": "Asked about medical card",
        "ai_summary": "Interested in family coverage. Budget around RM350. Married, 2 children. Previously asked about AIA.",
        "confidence": 96
    },
    {
        "id": 2, "name": "Sarah", "time": "9:15 AM",
        "summary": "Viewed quotation yesterday",
        "ai_summary": "High intent. Viewed medical card quotation. Hasn't replied yet.",
        "confidence": 82
    },
    {
        "id": 3, "name": "Muthu", "time": "Yesterday, 4:42 PM",
        "summary": "Asked about Prudential",
        "ai_summary": "Price sensitive. Comparing Prudential vs AIA. Wants family coverage.",
        "confidence": 73
    },
    {
        "id": 4, "name": "Mei Ling", "time": "Yesterday, 6:00 PM",
        "summary": "Follow-up sent",
        "ai_summary": "Renewal due in 28 days. Has been a customer since 2025.",
        "confidence": 68
    }
]

DEMO_CUSTOMERS = [
    {
        "name": "Mr Tan", "since": "2025",
        "interests": ["Medical Card", "Life Insurance", "Travel Insurance"],
        "last_interaction": "3 days ago", "upcoming": "Renewal in 27 days",
        "ai_notes": "Prefers WhatsApp. Usually replies after 8pm. Price sensitive. Children aged 7 and 10."
    },
    {
        "name": "Sarah", "since": "2026",
        "interests": ["Medical Card"],
        "last_interaction": "Yesterday", "upcoming": "Quotation pending",
        "ai_notes": "New lead. Interested in family coverage. Budget RM300-400."
    },
    {
        "name": "Jason", "since": "2024",
        "interests": ["Life Insurance", "Investment"],
        "last_interaction": "5 days ago", "upcoming": "Renewal next week",
        "ai_notes": "Loyal customer. Prefers email. Usually replies within 24 hours."
    }
]

DEMO_STATS = {
    "queries": 47,
    "quotes": 12,
    "converted": 4,
    "revenue": 2400,
    "pipeline": 18500,
    "leads": 18,
    "active_customers": 47,
    "conversion_rate": 28,
    "avg_response_seconds": 28,
    "documents_count": 12,
    "overnight": {
        "enquiries_answered": 14,
        "appointments_booked": 2,
        "quotations_generated": 5,
        "followups_sent": 7,
        "potential_revenue": 12000
    }
}

DEMO_SETTINGS = {
    "business_name": "Farah Insurance Agency",
    "owner_name": "Sanjay",
    "auto_reply": True,
    "follow_up_hours": 48,
    "response_tone": "friendly",
    "language": "en"
}

# In-memory store (replace with database later)
workspace_store = {}


# ─── ENDPOINTS ───

@router.get("/{tenant_id}/stats")
async def get_stats(tenant_id: str):
    """Get workspace statistics."""
    store = workspace_store.get(tenant_id, {})
    return store.get("stats", DEMO_STATS)


@router.get("/{tenant_id}/conversations")
async def get_conversations(tenant_id: str):
    """Get recent conversations."""
    store = workspace_store.get(tenant_id, {})
    return store.get("conversations", DEMO_CONVERSATIONS)


@router.get("/{tenant_id}/customers")
async def get_customers(tenant_id: str):
    """Get customer list."""
    store = workspace_store.get(tenant_id, {})
    return store.get("customers", DEMO_CUSTOMERS)


@router.get("/{tenant_id}/settings")
async def get_settings(tenant_id: str):
    """Get workspace settings."""
    store = workspace_store.get(tenant_id, {})
    return store.get("settings", DEMO_SETTINGS)


@router.put("/{tenant_id}/settings")
async def update_settings(tenant_id: str, data: SettingsUpdate):
    """Update workspace settings."""
    if tenant_id not in workspace_store:
        workspace_store[tenant_id] = {}

    current = workspace_store[tenant_id].get("settings", DEMO_SETTINGS.copy())

    updates = data.dict(exclude_none=True)
    current.update(updates)

    workspace_store[tenant_id]["settings"] = current

    return {"status": "ok", "settings": current}


@router.get("/{tenant_id}/health")
async def workspace_health(tenant_id: str):
    """Quick health check for workspace."""
    return {
        "status": "active",
        "tenant_id": tenant_id,
        "timestamp": datetime.utcnow().isoformat()
    }
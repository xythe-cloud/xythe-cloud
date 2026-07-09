"""
Authentication API — WhatsApp OTP Login
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import secrets
import json
import os
from datetime import datetime, timedelta
from src.services.whatsapp_client import WhatsAppClient

router = APIRouter(prefix="/api/auth", tags=["auth"])
whatsapp = WhatsAppClient()

USERS_FILE = "./data/users.json"
CODES_FILE = "./data/otp_codes.json"
os.makedirs("./data", exist_ok=True)

# The Xythe WhatsApp number that sends OTP codes
XYTHE_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "1156002210935879")


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def create_token(phone: str) -> str:
    return secrets.token_hex(32)


class SendCodeRequest(BaseModel):
    phone: str


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str


@router.post("/send-code")
async def send_code(data: SendCodeRequest):
    """Send a 6-digit OTP via WhatsApp."""
    phone = data.phone.strip()

    # Generate 6-digit code
    code = str(secrets.randbelow(900000) + 100000)

    # Store code (valid for 5 minutes)
    codes = load_json(CODES_FILE)
    codes[phone] = {
        "code": code,
        "expires": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
    }
    save_json(CODES_FILE, codes)

    # Send OTP via WhatsApp
    try:
        await whatsapp.send_text(
            phone_number_id=XYTHE_PHONE_ID,
            to=phone,
            text=f"🔐 Your Xythe verification code is: *{code}*\n\nThis code expires in 5 minutes. Do not share it with anyone."
        )
        return {"status": "ok", "message": "Verification code sent"}
    except Exception as e:
        return {"status": "ok", "message": "Code generated. WhatsApp send pending: " + str(e)}


@router.post("/verify")
async def verify_code(data: VerifyCodeRequest):
    """Verify OTP and login/signup."""
    phone = data.phone.strip()
    code = data.code.strip()

    # Check code
    codes = load_json(CODES_FILE)
    stored = codes.get(phone)

    if not stored:
        raise HTTPException(400, "No code sent to this number")

    if datetime.fromisoformat(stored["expires"]) < datetime.utcnow():
        del codes[phone]
        save_json(CODES_FILE, codes)
        raise HTTPException(400, "Code expired. Please request a new one.")

    if stored["code"] != code:
        raise HTTPException(400, "Incorrect code")

    # Code is valid — delete it
    del codes[phone]
    save_json(CODES_FILE, codes)

    # Create user if new
    users = load_json(USERS_FILE)
    if phone not in users:
        users[phone] = {
            "phone": phone,
            "tenant_id": f"t_{secrets.token_hex(4)}",
            "created_at": datetime.utcnow().isoformat()
        }
        save_json(USERS_FILE, users)

    user = users[phone]
    token = create_token(phone)

    # Store token
    tokens = load_json("./data/tokens.json")
    tokens[token] = {
        "phone": phone,
        "tenant_id": user["tenant_id"],
        "created_at": datetime.utcnow().isoformat()
    }
    save_json("./data/tokens.json", tokens)

    return {
        "token": token,
        "phone": phone,
        "tenant_id": user["tenant_id"],
        "is_new": True
    }


@router.get("/me")
async def me(token: str = ""):
    """Get current user info from token."""
    tokens = load_json("./data/tokens.json")
    data = tokens.get(token)
    if not data:
        raise HTTPException(401, "Invalid token")

    return {
        "phone": data["phone"],
        "tenant_id": data["tenant_id"]
    }
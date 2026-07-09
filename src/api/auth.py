"""
Authentication API — email/password with JWT tokens.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import secrets
import json
import os

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple file-based user store (replace with database later)
USERS_FILE = "./data/users.json"
os.makedirs("./data", exist_ok=True)

# Secret key for JWT (in production, use a proper secret)
JWT_SECRET = os.getenv("JWT_SECRET", "xythe_jwt_secret_2026")


def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((password + salt).encode()).hexdigest()


def check_password(password: str, hashed: str) -> bool:
    salt, hash_val = hashed.split(":")
    return hashlib.sha256((password + salt).encode()).hexdigest() == hash_val


def create_token(email: str) -> str:
    expiry = datetime.utcnow() + timedelta(days=30)
    payload = f"{email}:{expiry.isoformat()}:{JWT_SECRET}"
    token = hashlib.sha256(payload.encode()).hexdigest()
    return f"{token}:{expiry.isoformat()}"


def verify_token(token: str) -> Optional[str]:
    try:
        hash_part, expiry_str = token.split(":")
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.utcnow() > expiry:
            return None
        users = load_users()
        for email, user in users.items():
            expected = create_token(email)
            expected_hash = expected.split(":")[0]
            if hash_part == expected_hash:
                return email
        return None
    except:
        return None


# Models
class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    token: str
    email: str
    name: str
    tenant_id: str


@router.post("/signup")
async def signup(data: SignupRequest):
    users = load_users()

    if data.email in users:
        raise HTTPException(400, "Email already registered")

    tenant_id = f"t_{secrets.token_hex(4)}"

    users[data.email] = {
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name or data.email.split("@")[0],
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow().isoformat()
    }

    save_users(users)

    token = create_token(data.email)

    return TokenResponse(
        token=token,
        email=data.email,
        name=users[data.email]["name"],
        tenant_id=tenant_id
    )


@router.post("/login")
async def login(data: LoginRequest):
    users = load_users()

    if data.email not in users:
        raise HTTPException(400, "Email not registered")

    user = users[data.email]

    if not check_password(data.password, user["password"]):
        raise HTTPException(400, "Incorrect password")

    token = create_token(data.email)

    return TokenResponse(
        token=token,
        email=data.email,
        name=user["name"],
        tenant_id=user["tenant_id"]
    )


@router.get("/me")
async def me(token: str = ""):
    email = verify_token(token)
    if not email:
        raise HTTPException(401, "Invalid or expired token")

    users = load_users()
    user = users.get(email)
    if not user:
        raise HTTPException(404, "User not found")

    return {
        "email": user["email"],
        "name": user["name"],
        "tenant_id": user["tenant_id"]
    }
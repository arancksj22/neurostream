from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ..database import get_db
from ..models import User
from ..responses import success_response
from ..schemas import LoginRequest, RegisterRequest
from ..security import create_access_token, hash_password, verify_password
from ..serializers import serialize_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="USER",
    )
    db.add(user)
    db.flush()
    db.commit()
    db.refresh(user)

    token = create_access_token({"userId": user.id, "email": user.email, "role": user.role})

    return success_response(
        {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            },
        },
        message="User registered successfully.",
        status_code=201,
    )


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({"userId": user.id, "email": user.email, "role": user.role})

    return success_response(
        {
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            },
        },
        message="Login successful.",
    )


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response(serialize_user(current_user))

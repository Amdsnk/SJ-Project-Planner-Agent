from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..security import (get_current_user, hash_password, issue_token,
                        require_role, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return schemas.TokenOut(
        access_token=issue_token(user),
        expires_in=settings.jwt_ttl_minutes * 60,
    )


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate,
                admin: models.User = Depends(require_role("admin")),
                db: Session = Depends(get_db)):
    if db.query(models.User).filter(
        models.User.org_id == admin.org_id, models.User.email == payload.email
    ).first():
        raise HTTPException(409, "User already exists in this org")
    user = models.User(
        org_id=admin.org_id, email=payload.email, full_name=payload.full_name,
        password_hash=hash_password(payload.password), role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(admin: models.User = Depends(require_role("admin")),
               db: Session = Depends(get_db)):
    return db.query(models.User).filter(models.User.org_id == admin.org_id).all()

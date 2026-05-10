"""Authentication and authorisation.

Two flows are supported:

1. **Local JWT** (default): email + password → bcrypt-verified → JWT signed with
   ``JWT_SECRET``. Use this for local dev, on-prem, or as a fallback.
2. **Microsoft Entra ID (Azure AD)**: bearer tokens issued by Entra are accepted
   when ``ENTRA_TENANT_ID`` and ``ENTRA_CLIENT_ID`` are configured. The user is
   matched (or auto-provisioned) by ``oid`` claim within the configured org.
"""
from __future__ import annotations

import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

log = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- password hashing ----------
def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return _pwd.verify(password, hashed)
    except Exception:
        return False


# ---------- local JWT ----------
def issue_token(user: models.User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "org": user.org_id,
        "email": user.email,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_ttl_minutes)).timestamp()),
        "iss": "sj-planner",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_local(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], issuer="sj-planner")
    except jwt.PyJWTError:
        return None


# ---------- Entra ID validation ----------
_ENTRA_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0}


def _entra_jwks() -> Optional[dict]:
    if not settings.entra_enabled:
        return None
    # Refresh JWKS at most every 6 hours.
    if _ENTRA_JWKS_CACHE["keys"] and time.time() - _ENTRA_JWKS_CACHE["fetched_at"] < 6 * 3600:
        return _ENTRA_JWKS_CACHE["keys"]
    url = f"https://login.microsoftonline.com/{settings.entra_tenant_id}/discovery/v2.0/keys"
    try:
        with httpx.Client(timeout=5.0) as cli:
            r = cli.get(url)
            r.raise_for_status()
            _ENTRA_JWKS_CACHE["keys"] = r.json()
            _ENTRA_JWKS_CACHE["fetched_at"] = time.time()
            return _ENTRA_JWKS_CACHE["keys"]
    except Exception as e:
        log.warning("Failed to fetch Entra JWKS: %s", e)
        return None


def _decode_entra(token: str) -> Optional[dict[str, Any]]:
    if not settings.entra_enabled:
        return None
    jwks = _entra_jwks()
    if not jwks:
        return None
    try:
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if not key:
            return None
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        return jwt.decode(
            token, public_key,
            algorithms=[unverified.get("alg", "RS256")],
            audience=settings.entra_audience or settings.entra_client_id,
            issuer=f"https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0",
        )
    except jwt.PyJWTError as e:
        log.info("Entra token rejected: %s", e)
        return None


# ---------- FastAPI dependencies ----------
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token",
                            headers={"WWW-Authenticate": "Bearer"})
    # Try local JWT first, then Entra ID.
    claims = _decode_local(token) or _decode_entra(token)
    if not claims:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})

    user = None
    if "sub" in claims and claims.get("iss") == "sj-planner":
        user = db.get(models.User, int(claims["sub"]))
    elif "oid" in claims:
        # Entra-issued token — match or auto-provision within configured org.
        user = (
            db.query(models.User)
            .filter(models.User.entra_oid == claims["oid"])
            .first()
        )
        if not user and claims.get("preferred_username"):
            org = db.query(models.Organization).first()  # single-tenant deployment
            if org:
                user = models.User(
                    org_id=org.id, email=claims["preferred_username"],
                    full_name=claims.get("name", ""), entra_oid=claims["oid"],
                    role="reviewer", is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or disabled")
    return user


def require_role(*roles: str):
    def _dep(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles and "admin" != user.role:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {roles}")
        return user
    return _dep


def require_project(project_id: int,
                    user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> models.Project:
    """Ensure the project exists and belongs to the user's org."""
    proj = db.get(models.Project, project_id)
    if not proj or proj.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return proj

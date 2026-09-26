"""Authentication & Authorization.

Default implementation: simple credential-based auth with opaque bearer
session tokens stored server-side (so a session can be revoked instantly by
deleting its row — no JWT to invalidate). Two roles:

- "analyst":  can ingest/generate, view drafts, and make disclosure decisions.
- "approver": everything an analyst can do, PLUS approve/export deliverables
              (the only path that writes to the Provenance Ledger).

This is a deliberate default, not a locked-in architectural decision — see
the security remediation brief's item 1. If SSO/OAuth2 is required instead,
replace get_current_operator's implementation (and the login/bootstrap
plumbing) here; every route depends only on `Depends(get_current_operator)`
returning an `OperatorModel`, so nothing else needs to change.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import OperatorModel, OperatorSessionModel

logger = logging.getLogger("srigen.auth")

PBKDF2_ITERATIONS = 260_000
SESSION_TTL_HOURS = 12
ROLE_ANALYST = "analyst"
ROLE_APPROVER = "approver"
VALID_ROLES = {ROLE_ANALYST, ROLE_APPROVER}


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Returns (password_hash_hex, salt_hex). Stdlib-only PBKDF2-HMAC-SHA256 —
    deliberately avoids adding a bcrypt/argon2 dependency for this default
    implementation; swap for one if this becomes the long-term auth backend."""
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, PBKDF2_ITERATIONS)
    return derived.hex(), salt_bytes.hex()


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate_hash, _ = hash_password(password, salt=salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def _hash_token(token: str) -> str:
    """Store only a hash of the bearer token server-side, never the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_operator(db: Session, username: str, password: str, role: str = ROLE_ANALYST) -> OperatorModel:
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of {VALID_ROLES}.")
    password_hash, salt = hash_password(password)
    operator = OperatorModel(username=username, password_hash=password_hash, password_salt=salt, role=role)
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator


def authenticate(db: Session, username: str, password: str) -> Optional[OperatorModel]:
    operator = db.query(OperatorModel).filter(OperatorModel.username == username).first()
    if not operator or not operator.is_active:
        return None
    if not verify_password(password, operator.password_hash, operator.password_salt):
        return None
    return operator


def issue_session(db: Session, operator: OperatorModel) -> str:
    """Creates a session and returns the RAW bearer token (only ever returned
    once, at login time — only its hash is persisted)."""
    raw_token = secrets.token_urlsafe(32)
    session = OperatorSessionModel(
        token_hash=_hash_token(raw_token),
        operator_id=operator.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
    )
    db.add(session)
    db.commit()
    return raw_token


def bootstrap_default_operator(db: Session) -> None:
    """Dev/first-run convenience only: if NO operators exist yet and bootstrap
    credentials are configured via env, create one 'approver' account so the
    system isn't left unusable out of the box. Does nothing once any operator
    exists. Change/remove these credentials before any shared or production
    deployment — see README."""
    if db.query(OperatorModel).first() is not None:
        return
    if not settings.OPERATOR_BOOTSTRAP_USERNAME or not settings.OPERATOR_BOOTSTRAP_PASSWORD:
        logger.warning(
            "No operators exist and no OPERATOR_BOOTSTRAP_USERNAME/PASSWORD is configured — "
            "every route requiring auth will return 401 until an operator is created."
        )
        return
    create_operator(
        db,
        username=settings.OPERATOR_BOOTSTRAP_USERNAME,
        password=settings.OPERATOR_BOOTSTRAP_PASSWORD,
        role=ROLE_APPROVER,
    )
    logger.warning(
        f"Bootstrapped default operator '{settings.OPERATOR_BOOTSTRAP_USERNAME}' (role=approver) "
        f"from env. Change this password or create real accounts before any shared deployment."
    )


async def get_current_operator(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> OperatorModel:
    """FastAPI dependency: resolves the Bearer token in the Authorization
    header to an active OperatorModel, or raises 401. Wired at the
    router-include level in app/api/__init__.py so no route can be added
    later and accidentally left unauthenticated."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    raw_token = authorization[len("Bearer "):].strip()
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty bearer token.")

    token_hash = _hash_token(raw_token)
    session = db.query(OperatorSessionModel).filter(OperatorSessionModel.token_hash == token_hash).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token.")

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session token has expired.")

    operator = db.query(OperatorModel).filter(OperatorModel.id == session.operator_id).first()
    if not operator or not operator.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Operator account is inactive or no longer exists.")

    return operator


def require_role(*allowed_roles: str):
    """Dependency factory: use as Depends(require_role('approver')) on routes
    that need role scoping beyond plain authentication (approve/export)."""

    async def _check(current_operator: OperatorModel = Depends(get_current_operator)) -> OperatorModel:
        if current_operator.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_operator.role}' is not permitted to perform this action. "
                       f"Requires one of: {', '.join(allowed_roles)}.",
            )
        return current_operator

    return _check

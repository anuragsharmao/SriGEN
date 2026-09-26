"""Routes for Authentication. `/auth/login` is intentionally the ONLY public
route in the API besides `/` and `/health` — every other router is mounted
with `Depends(get_current_operator)` at the router-include level in
app/api/__init__.py, so nothing can be added later and accidentally left
unauthenticated.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import OperatorModel
from app.services.auth import (
    ROLE_ANALYST,
    ROLE_APPROVER,
    VALID_ROLES,
    authenticate,
    create_operator,
    get_current_operator,
    issue_session,
    require_role,
)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class RegisterOperatorRequest(BaseModel):
    username: str
    password: str
    role: str = ROLE_ANALYST


class OperatorPublic(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Log in and obtain a bearer session token",
    description=(
        "Public endpoint. Exchanges username/password for an opaque bearer token, valid for "
        "12 hours, to send as `Authorization: Bearer <token>` on every other request."
    ),
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    operator = authenticate(db, request.username, request.password)
    if not operator:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    token = issue_session(db, operator)
    return LoginResponse(access_token=token, role=operator.role, username=operator.username)


@router.get(
    "/auth/me",
    response_model=OperatorPublic,
    summary="Get the currently authenticated operator",
)
def me(current_operator: OperatorModel = Depends(get_current_operator)):
    return OperatorPublic(
        id=current_operator.id,
        username=current_operator.username,
        role=current_operator.role,
        is_active=current_operator.is_active,
    )


@router.post(
    "/auth/register",
    response_model=OperatorPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new operator account (approver role required)",
    description="Restricted to existing approvers, so account creation itself can't be self-service.",
)
def register(
    request: RegisterOperatorRequest,
    db: Session = Depends(get_db),
    current_operator: OperatorModel = Depends(require_role(ROLE_APPROVER)),
):
    if request.role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"role must be one of {VALID_ROLES}.")
    existing = db.query(OperatorModel).filter(OperatorModel.username == request.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
    operator = create_operator(db, username=request.username, password=request.password, role=request.role)
    return OperatorPublic(id=operator.id, username=operator.username, role=operator.role, is_active=operator.is_active)


@router.post(
    "/auth/register-first",
    response_model=OperatorPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create the initial local operator account",
    description="Public first-run setup endpoint. It is available only while the database has no operators.",
)
def register_first_operator(request: RegisterOperatorRequest, db: Session = Depends(get_db)):
    if db.query(OperatorModel).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Initial operator account already exists.")
    operator = create_operator(db, username=request.username, password=request.password, role=ROLE_APPROVER)
    return OperatorPublic(id=operator.id, username=operator.username, role=operator.role, is_active=operator.is_active)

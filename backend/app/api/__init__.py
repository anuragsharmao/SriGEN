"""API endpoints package for SriGEN.

Authentication is wired at the router-include level (item 1 of the security
remediation brief), not per-endpoint, specifically so a route added later
can never be accidentally left unauthenticated: every router below except
`auth_router` carries `dependencies=[Depends(get_current_operator)]`.
`auth_router` itself gates its own non-login routes (`/auth/me`,
`/auth/register`) individually, since `/auth/login` must remain public.
"""
from fastapi import APIRouter, Depends
from app.api.routes_auth import router as auth_router
from app.api.routes_generate import router as generate_router
from app.api.routes_verify import router as verify_router
from app.api.routes_refine import router as refine_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_ledger import router as ledger_router
from app.api.routes_disclosure import router as disclosure_router
from app.services.auth import get_current_operator

_AUTH = [Depends(get_current_operator)]

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api", tags=["Auth"])
api_router.include_router(generate_router, prefix="/api", tags=["Transformation Mode"], dependencies=_AUTH)
api_router.include_router(verify_router, prefix="/api", tags=["Verification Mode (alias)"], dependencies=_AUTH)
api_router.include_router(refine_router, prefix="/api", tags=["Refine Mode"], dependencies=_AUTH)
api_router.include_router(dashboard_router, prefix="/api", tags=["Operator Dashboard"], dependencies=_AUTH)
api_router.include_router(ledger_router, prefix="/api", tags=["Provenance Ledger"], dependencies=_AUTH)
api_router.include_router(disclosure_router, prefix="/api", tags=["Disclosure Control"], dependencies=_AUTH)
api_router.include_router(disclosure_router, tags=["Disclosure Control (Direct)"], dependencies=_AUTH)
api_router.include_router(dashboard_router, tags=["Operator Dashboard (Direct)"], dependencies=_AUTH)

__all__ = ["api_router"]

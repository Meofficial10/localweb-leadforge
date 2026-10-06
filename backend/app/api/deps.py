"""FastAPI dependencies: auth, session, compliance services."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.compliance import ComplianceService
from app.core.suppression import SuppressionService
from app.db import get_session

_bearer = HTTPBearer(auto_error=False)


def require_token(creds: HTTPAuthorizationCredentials | None = Security(_bearer)) -> str:
    if creds is None:
        raise HTTPException(status_code=401, detail="missing credentials")
    if creds.scheme.lower() != "bearer" or creds.credentials not in settings.token_list():
        raise HTTPException(status_code=401, detail="invalid token")
    return creds.credentials


def require_admin(creds: HTTPAuthorizationCredentials | None = Security(_bearer)) -> str:
    token = require_token(creds)
    if token not in settings.admin_token_list():
        raise HTTPException(status_code=403, detail="admin privileges required")
    return token


def get_suppression_service(db: Session = Depends(get_session)) -> SuppressionService:
    return SuppressionService(db)


def get_compliance_service(db: Session = Depends(get_session)) -> ComplianceService:
    return ComplianceService(suppression=SuppressionService(db), force_dry_run=settings.force_dry_run)

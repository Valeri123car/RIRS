"""Skupne FastAPI odvisnosti (prijavljen uporabnik ...)."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import InvalidTokenError, decode_token
from app.db.session import get_db
from app.models.user import User

DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]

_bearer = HTTPBearer(auto_error=False)


def unauthorized(detail: str = "Prijava je potrebna.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        user_id = decode_token(credentials.credentials, "access", settings)
    except InvalidTokenError:
        raise unauthorized("Seja je potekla ali ni veljavna.") from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized("Seja je potekla ali ni veljavna.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from threading import Lock

from fastapi import Cookie, Depends, HTTPException, status

from app.config import settings
from app.security import api_key_header


ACCESS_CODE_TTL_SECONDS = 300
SESSION_COOKIE_NAME = "tytus_session"


@dataclass(frozen=True)
class AccessCode:
    digest: str
    expires_at: int


@dataclass(frozen=True)
class RedeemedSession:
    token: str
    expires_at: int


_access_codes: dict[str, AccessCode] = {}
_issued_code_digests: set[str] = set()
_access_code_lock = Lock()


def _sign(value: str) -> str:
    return hmac.new(
        settings.app_api_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_access_code() -> str:
    if not settings.app_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access-code service is not configured",
        )

    now = int(time.time())
    with _access_code_lock:
        expired = [
            key
            for key, value in _access_codes.items()
            if value.expires_at <= now
        ]
        for key in expired:
            _access_codes.pop(key, None)

        while True:
            code = f"{secrets.randbelow(1_000_000):06d}"
            digest = _sign(code)
            if digest not in _issued_code_digests:
                break

        _issued_code_digests.add(digest)
        _access_codes[digest] = AccessCode(
            digest=digest,
            expires_at=now + ACCESS_CODE_TTL_SECONDS,
        )
    return code


def redeem_access_code(code: str) -> RedeemedSession:
    if len(code) != 6 or not code.isdigit() or not settings.app_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access code",
        )

    digest = _sign(code)
    with _access_code_lock:
        stored = _access_codes.pop(digest, None)
    now = int(time.time())
    if stored is None or stored.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access code",
        )

    expiry = stored.expires_at
    payload = f"{expiry}.{secrets.token_hex(12)}"
    return RedeemedSession(
        token=f"{payload}.{_sign(payload)}",
        expires_at=expiry,
    )


def valid_session(token: str | None) -> bool:
    if token is None or not settings.app_api_key:
        return False

    try:
        expiry, nonce, signature = token.split(".", 2)
        payload = f"{expiry}.{nonce}"
        return int(expiry) > int(time.time()) and hmac.compare_digest(
            signature,
            _sign(payload),
        )
    except (TypeError, ValueError):
        return False


def session_remaining_seconds(token: str | None) -> int:
    if not valid_session(token):
        return 0
    try:
        expiry = int(token.split(".", 1)[0])
        return max(0, expiry - int(time.time()))
    except (TypeError, ValueError):
        return 0


def require_chat_access(
    provided_api_key: str | None = Depends(api_key_header),
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE_NAME,
    ),
) -> None:
    if not settings.app_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        )

    has_master_key = bool(
        provided_api_key
        and settings.app_api_key
        and hmac.compare_digest(provided_api_key, settings.app_api_key)
    )
    if not has_master_key and not valid_session(session_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

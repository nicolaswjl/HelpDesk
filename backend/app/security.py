import threading
import time
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_WINDOW_SECONDS,
    SECRET_KEY,
)
from .database import get_db
from .models import User

password_hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)

# Hash descartável usado para gastar o mesmo tempo quando o e-mail não existe,
# evitando que a diferença de tempo de resposta revele quais e-mails estão cadastrados.
_DUMMY_HASH = password_hasher.hash("senha-descartavel-nao-utilizada")


class LoginRateLimiter:
    """Limitador de tentativas de login em memória (processo único).

    Suficiente para estudo e instalações pequenas. Com vários processos ou
    atrás de um proxy reverso, use um armazenamento compartilhado (ex.: Redis)
    e leia o IP real do cliente.
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        recent = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def retry_after(self, key: str) -> int:
        """Segundos até nova tentativa; 0 quando o login está liberado."""
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            if len(recent) < self.max_attempts:
                return 0
            return max(1, int(self.window_seconds - (now - recent[0])) + 1)

    def register_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = self._recent(key, now)
            recent.append(now)
            self._failures[key] = recent
            if len(self._failures) > 10_000:  # evita crescimento ilimitado
                for key_ in list(self._failures):
                    self._recent(key_, now)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._failures.clear()
            else:
                self._failures.pop(key, None)


login_limiter = LoginRateLimiter(LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError, TypeError):
        return False

def burn_password_check(password: str) -> None:
    """Executa uma verificação de hash inútil para igualar o tempo de resposta."""
    verify_password(password, _DUMMY_HASH)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.isdigit():
            raise jwt.InvalidTokenError("Identificador inválido")
        user_id = int(subject)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.", headers={"WWW-Authenticate": "Bearer"}) from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário inválido ou inativo.")
    return user

def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Permissão insuficiente.")
        return user
    return checker

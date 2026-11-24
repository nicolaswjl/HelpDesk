import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./helpdesk.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-this-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
# Limite de tentativas de login falhas por (IP, e-mail) dentro da janela, em segundos.
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))

if ACCESS_TOKEN_EXPIRE_MINUTES < 1:
    raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES precisa ser maior que zero.")
if LOGIN_MAX_ATTEMPTS < 1 or LOGIN_WINDOW_SECONDS < 1:
    raise ValueError("LOGIN_MAX_ATTEMPTS e LOGIN_WINDOW_SECONDS precisam ser maiores que zero.")
if ENVIRONMENT == "production" and (
    len(SECRET_KEY) < 32
    or SECRET_KEY in {
        "dev-only-change-this-secret-key",
        "troque-por-uma-chave-aleatoria-longa",
    }
):
    raise RuntimeError("Defina uma SECRET_KEY aleatória com pelo menos 32 caracteres antes de executar em produção.")
if "*" in CORS_ORIGINS and ENVIRONMENT == "production":
    raise RuntimeError("CORS_ORIGINS não pode usar '*' em produção.")

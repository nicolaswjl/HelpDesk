from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func

from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password

EMAIL_ADAPTER = TypeAdapter(EmailStr)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        name = input("Nome do administrador: ").strip()
        email = input("E-mail: ").strip().lower()
        password = getpass("Senha (mínimo 10 caracteres): ")
        confirmation = getpass("Confirme a senha: ")

        if len(name) < 2 or len(name) > 120:
            raise SystemExit("O nome precisa ter entre 2 e 120 caracteres.")
        try:
            email = str(EMAIL_ADAPTER.validate_python(email)).lower()
        except ValidationError:
            raise SystemExit("Informe um e-mail válido.") from None
        if len(email) > 255:
            raise SystemExit("O e-mail pode ter no máximo 255 caracteres.")
        if len(password) < 10 or len(password) > 128:
            raise SystemExit("A senha precisa ter entre 10 e 128 caracteres.")
        if password != confirmation:
            raise SystemExit("As senhas não coincidem.")
        if db.query(User).filter(func.lower(User.email) == email).first():
            raise SystemExit("Já existe um usuário com esse e-mail.")

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print("Administrador criado com sucesso.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

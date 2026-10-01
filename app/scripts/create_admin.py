"""Crea el usuario administrador inicial.

Uso:
    python -m app.scripts.create_admin --email admin@cafeteria.com --password "secreto123"
"""

import argparse
import sys

from app.core.database import SessionLocal
from app.models import RoleEnum
from app.schemas.auth import UserCreate
from app.services.auth_service import AuthService


def main() -> int:
    """Punto de entrada del script."""
    parser = argparse.ArgumentParser(description="Crear el administrador inicial")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default="Administrador")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        service = AuthService(session)
        if service.users.email_exists(args.email):
            print(f"El email {args.email} ya está registrado.")
            return 1
        user = service.register(
            UserCreate(
                email=args.email,
                password=args.password,
                full_name=args.full_name,
                role=RoleEnum.ADMIN,
            )
        )
        print(f"Administrador creado con id {user.id}.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

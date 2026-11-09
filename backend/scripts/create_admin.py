"""python -m scripts.create_admin <email> [--role superadmin|admin|editor] [--reset-password]

Reads the password from ADMIN_PASSWORD, or asks for it. There are no default credentials.
"""

import argparse
import getpass
import os
import re
import sys

from sqlalchemy import select

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.models import ROLE_SUPERADMIN, ROLES, AdminUser
from app.services.admin import audit, auth

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _read_password() -> str:
    password = os.environ.get("ADMIN_PASSWORD")
    if password is not None:
        return password
    password = getpass.getpass("Contraseña: ")
    if password != getpass.getpass("Repite la contraseña: "):
        raise SystemExit("Las contraseñas no coinciden")
    return password


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Crea un usuario del panel admin")
    parser.add_argument("email")
    parser.add_argument("--role", choices=ROLES, default=ROLE_SUPERADMIN)
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Cambia la contraseña de un usuario existente y cierra sus sesiones",
    )
    args = parser.parse_args(argv)

    email = auth.normalize_email(args.email)
    if not _EMAIL.fullmatch(email) or len(email) > 254:
        raise SystemExit("Correo inválido")
    password = _read_password()
    if len(password) < auth.MIN_PASSWORD_LENGTH:
        raise SystemExit(f"La contraseña debe tener al menos {auth.MIN_PASSWORD_LENGTH} caracteres")

    engine = make_engine(get_settings().resolved_database_url)
    try:
        with make_session_factory(engine)() as session, session.begin():
            user = session.scalar(select(AdminUser).where(AdminUser.email == email))
            if user is None:
                user = AdminUser(
                    email=email, password_hash=auth.hash_password(password), role=args.role
                )
                session.add(user)
                session.flush()
                audit.record(session, None, "create", "admin_user", user.id, {"role": [None, user.role]})
                message = f"Usuario creado: {email} ({user.role})"
            elif args.reset_password:
                user.password_hash = auth.hash_password(password)
                auth.revoke_all_sessions(session, user)
                audit.record(session, None, "reset_password", "admin_user", user.id)
                message = f"Contraseña actualizada: {email}"
            else:
                print(f"{email} ya existe; usa --reset-password para cambiarla", file=sys.stderr)
                raise SystemExit(1)
    finally:
        engine.dispose()
    print(message)


if __name__ == "__main__":
    main()

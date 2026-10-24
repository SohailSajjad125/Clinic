"""python -m app.cli create-superadmin you@example.com 'Full Name' (prompts for the password)."""
import getpass
import sys

from sqlalchemy import select

from .core.database import SessionLocal
from .core.security import hash_password
from .models import User


def main():
    if len(sys.argv) != 4 or sys.argv[1] != "create-superadmin":
        sys.exit("usage: python -m app.cli create-superadmin EMAIL 'FULL NAME'")
    email, name = sys.argv[2].lower(), sys.argv[3]
    pw = getpass.getpass("Password (min 12 chars): ")
    if len(pw) < 12 or len(pw.encode()) > 72:
        sys.exit("Password must be 12-72 characters.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            sys.exit("A user with this email already exists.")
        db.add(User(email=email, full_name=name, password_hash=hash_password(pw), is_superadmin=True, email_verified=True))
        db.commit()
    print("Super admin created. Sign in at the web app login page.")


if __name__ == "__main__":
    main()

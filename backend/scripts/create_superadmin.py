#!/usr/bin/env python3
"""
CLI script to bootstrap the FIRST Superadmin user on a fresh database.

SECURITY NOTE: Passwords are NEVER accepted as command-line arguments (to prevent credential
leakage in process listings or shell history).

Run interactively on server host or container:
  python backend/scripts/create_superadmin.py --email admin@college.edu --name "Platform Superadmin"

Or set env variable in a private subshell:
  SUPERADMIN_INITIAL_EMAIL="admin@college.edu" \
  SUPERADMIN_INITIAL_PASSWORD="..." \
  python backend/scripts/create_superadmin.py
"""
import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from sqlalchemy import select
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.utils.security import get_password_hash, validate_password_strength


async def create_superadmin(email: str, password: str, full_name: str) -> None:
    if not validate_password_strength(password):
        print("ERROR: Password must be at least 8 characters long.")
        sys.exit(1)

    async with SessionLocal() as db:
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == email.strip().lower()))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.role == UserRole.superadmin:
                print(f"INFO: Superadmin account '{email}' already exists and is active.")
                print("NOTE: 2FA enrollment will be enforced on next sign-in if not already completed.")
                return
            else:
                print(f"UPGRADING existing user '{email}' to superadmin role...")
                existing_user.role = UserRole.superadmin
                existing_user.invitation_status = "active"
                existing_user.organization_id = None
                existing_user.organization_name = "Platform Team"
                existing_user.hashed_password = get_password_hash(password)
                await db.commit()
                print(f"SUCCESS: Upgraded '{email}' to Superadmin!")
                print("SECURITY: Mandatory 2FA enrollment will be triggered on first sign-in.")
                return

        hashed = get_password_hash(password)
        superadmin = User(
            email=email.strip().lower(),
            full_name=full_name.strip(),
            hashed_password=hashed,
            role=UserRole.superadmin,
            is_active=True,
            invitation_status="active",
            organization_id=None,
            organization_name="Platform Team",
            totp_enabled=False,  # Enforces mandatory 2FA enrollment on first login
        )

        db.add(superadmin)
        await db.commit()
        print("=" * 65)
        print("SUCCESS: Initial Superadmin account created successfully!")
        print("=" * 65)
        print(f"  Email:              {email}")
        print(f"  Role:               superadmin")
        print(f"  Status:             active")
        print(f"  2FA Status:         Enforcement Active (Mandatory setup on first sign-in)")
        print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap the initial Superadmin user on a fresh database safely without command-line password arguments."
    )
    parser.add_argument("--email", help="Superadmin email address")
    parser.add_argument("--name", default="Platform Superadmin", help="Full name for superadmin user")

    args = parser.parse_args()

    email = args.email or os.getenv("SUPERADMIN_INITIAL_EMAIL")
    name = args.name or os.getenv("SUPERADMIN_INITIAL_NAME", "Platform Superadmin")
    password = os.getenv("SUPERADMIN_INITIAL_PASSWORD")

    if not email:
        email = input("Enter initial Superadmin email: ").strip()

    if not password:
        while True:
            p1 = getpass.getpass("Enter initial Superadmin password: ").strip()
            if not p1:
                print("ERROR: Password cannot be empty.")
                continue
            if len(p1) < 8:
                print("ERROR: Password must be at least 8 characters long.")
                continue
            p2 = getpass.getpass("Confirm initial Superadmin password: ").strip()
            if p1 != p2:
                print("ERROR: Passwords do not match. Please try again.")
                continue
            password = p1
            break

    if not email or not password:
        print("ERROR: Both email and password are required.")
        sys.exit(1)

    asyncio.run(create_superadmin(email, password, name))


if __name__ == "__main__":
    main()

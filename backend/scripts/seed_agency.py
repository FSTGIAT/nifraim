"""Seed an agency for smoke-testing.

Creates an Agency, promotes a user to `agency_admin`, and (optionally) binds
ALL other agents to that agency so the super-user has cross-agent data to view.

Usage:
    python -m backend.scripts.seed_agency \\
        --owner-email test@test.com \\
        --name "ד.נ.ר" \\
        --slug "dnr" \\
        --bind-all-agents
"""
import argparse
import asyncio
import sys
import uuid
from pathlib import Path

# Resolve "from app.*" imports when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.agency import Agency


async def main(owner_email: str, name: str, slug: str, bind_all: bool, role: str):
    async with async_session() as db:
        # Find owner
        owner = (await db.execute(select(User).where(User.email == owner_email))).scalar_one_or_none()
        if not owner:
            print(f"ERROR: user {owner_email} not found")
            sys.exit(2)

        # Reuse existing agency by slug if present, else create.
        agency = (await db.execute(select(Agency).where(Agency.slug == slug))).scalar_one_or_none()
        if agency:
            print(f"  ↺ Agency '{agency.name}' (slug={agency.slug}) already exists")
        else:
            agency = Agency(name=name, slug=slug, owner_user_id=owner.id)
            db.add(agency)
            await db.flush()
            print(f"  ✓ Created agency '{name}' (id={agency.id})")

        # Promote owner
        owner.role = role
        owner.agency_id = agency.id
        print(f"  ✓ {owner.email} → role={role}, agency_id={agency.id}")

        if bind_all:
            others = (
                await db.execute(
                    select(User).where(User.id != owner.id, User.agency_id.is_(None))
                )
            ).scalars().all()
            for u in others:
                u.agency_id = agency.id
                u.role = "agent"
            print(f"  ✓ Bound {len(others)} other agents to the agency")

        await db.commit()
        print("\nDone. Login as", owner.email, "and visit /agency.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--owner-email", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--role", default="agency_admin", choices=["agency_admin", "agency_accountant"])
    p.add_argument("--bind-all-agents", action="store_true",
                   help="Bind every other unbounded user as an agent under this agency")
    args = p.parse_args()
    asyncio.run(main(args.owner_email, args.name, args.slug, args.bind_all_agents, args.role))

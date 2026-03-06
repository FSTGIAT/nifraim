import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base
from app.models import User, FileUpload, ClientRecord, CommissionRate, Recruit, CompanyContact

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment variable if available
# Railway provides DATABASE_URL — derive sync URL from it if DATABASE_URL_SYNC not set
db_url = os.environ.get("DATABASE_URL_SYNC")
if not db_url:
    async_url = os.environ.get("DATABASE_URL", "")
    if async_url:
        db_url = async_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        # Railway sometimes provides postgres:// (old Heroku-style)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

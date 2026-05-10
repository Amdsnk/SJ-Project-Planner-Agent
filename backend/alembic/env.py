"""Alembic environment.

Pulls the database URL and the SQLAlchemy metadata from the application
package so migrations and runtime stay in lock-step.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make ``app...`` imports resolve when alembic is invoked from backend/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
from app import models  # noqa: F401,E402  (register models on Base.metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Allow override via env var so prod CI can point at a managed Postgres
# without editing alembic.ini.
db_url = os.getenv("DATABASE_URL", settings.database_url)
config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Alembic environment configuration

This script runs database migrations. For more information on alembic, visit:
https://alembic.sqlalchemy.org/en/latest/
"""

import asyncio
from logging.config import fileConfig
import os
import sys
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Add the app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import app models and config
from app.db.base import Base
from app.core.config import settings

# Alembic config object
config = context.config

# Set sqlalchemy.url from settings if not set in alembic.ini
if not config.get_main_option('sqlalchemy.url'):
    config.set_main_option('sqlalchemy.url', str(settings.SQLALCHEMY_DATABASE_URI))

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# Target metadata for the database
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
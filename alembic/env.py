import os
import sys
# Add project root to PYTHONPATH so Alembic can find models.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import metadata from models
from models import Base

target_metadata = Base.metadata

# Alembic Config object, provides access to .ini values
config = context.config

# Setup Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' (SQL script) mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' (DB API) mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True  # detect type changes
        )
        with context.begin_transaction():
            context.run_migrations()

# Choose offline or online run
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

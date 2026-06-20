import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
from dotenv import load_dotenv

# Add project root to python path to load modules correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load dotenv config
load_dotenv()

# Alembic Config
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models metadata
from api.db_models import Base
target_metadata = Base.metadata

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migrations_offline() -> None:
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    # Use create_engine directly with DATABASE_URL to avoid reading empty config url from alembic.ini
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

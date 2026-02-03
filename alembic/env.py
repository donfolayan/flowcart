import os
from logging.config import fileConfig

from pathlib import Path
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from sqlalchemy import MetaData
from decouple import Config, RepositoryEnv

from app.db.base import Base


def _find_repo_root(max_levels: int = 5) -> str:
    """Find the repository root by looking for the .git directory."""
    current_path = Path(__file__).resolve()

    for _ in range(max_levels):
        if (current_path / ".git").exists():
            return str(current_path)
        current_path = current_path.parent

    raise FileNotFoundError("Could not find repository root")


_repo_root = _find_repo_root()

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

DOT_ENV_PATH = os.path.join(_repo_root, ".env")
env_config = Config(RepositoryEnv(DOT_ENV_PATH))
SYNC_DATABASE_URL = str(env_config("SYNC_DATABASE_URL"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


import app.models.user  # noqa: F401, E402
import app.models.product  # noqa: F401, E402
import app.models.category  # noqa: F401, E402
import app.models.media  # noqa: F401, E402
import app.models.product_media  # noqa: F401, E402
import app.models.product_variant  # noqa: F401, E402
import app.models.cart  # noqa: F401, E402
import app.models.cart_item  # noqa: F401, E402
import app.models.order  # noqa: F401, E402
import app.models.order_item  # noqa: F401, E402
import app.models.address  # noqa: F401, E402
import app.models.payment  # noqa: F401, E402
import app.models.shipping  # noqa: F401, E402
import app.models.promo_code  # noqa: F401, E402
import app.models.webhook_events  # noqa: F401, E402
import app.models.refresh_tokens  # noqa: F401, E402


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata: MetaData = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
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

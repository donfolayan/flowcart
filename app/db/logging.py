"""Database session logging and event handlers."""

import logging
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

logger = logging.getLogger("db")


def setup_db_logging():
    """Configure database-specific logging events."""

    @event.listens_for(Engine, "before_cursor_execute", named=True)
    def receive_before_cursor_execute(**kw: Any) -> None:
        """Log SQL queries before execution (only in DEBUG mode)."""
        statement = kw.get("statement")
        parameters = kw.get("parameters")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Executing SQL",
                extra={
                    "sql": statement,
                    "params": parameters,
                },
            )

    @event.listens_for(Engine, "after_cursor_execute", named=True)
    def receive_after_cursor_execute(**kw: Any) -> None:
        """Log query completion (only in DEBUG mode)."""
        statement = kw.get("statement")

        if logger.isEnabledFor(logging.DEBUG) and statement:
            logger.debug(
                "SQL query completed",
                extra={"sql": statement[:100]},  # First 100 chars
            )

    @event.listens_for(Engine, "handle_error", named=True)
    def receive_handle_error(**kw: Any) -> None:
        """Log database errors."""
        exception = kw.get("exception")
        statement = kw.get("statement")
        parameters = kw.get("parameters")

        logger.error(
            "Database error",
            extra={
                "error": str(exception),
                "error_type": type(exception).__name__,
                "sql": statement,
                "params": parameters,
            },
            exc_info=exception,
        )

    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn: Any, connection_record: Any) -> None:
        """Log new database connections."""
        logger.info("New database connection established")

    @event.listens_for(Pool, "checkout")
    def receive_checkout(
        dbapi_conn: Any, connection_record: Any, connection_proxy: Any
    ) -> None:
        """Log connection checkout from pool (only in DEBUG mode)."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Connection checked out from pool")

    @event.listens_for(Pool, "checkin")
    def receive_checkin(dbapi_conn: Any, connection_record: Any) -> None:
        """Log connection checkin to pool (only in DEBUG mode)."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Connection returned to pool")

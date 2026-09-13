from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    """Return current UTC datetime as an offset-naive datetime for TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass



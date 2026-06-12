import contextvars
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from app.config import settings

org_id_var = contextvars.ContextVar("org_id", default=None)

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=True,
    connect_args={"statement_cache_size": 0},  # Required for Supabase pgbouncer
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

@event.listens_for(Session, "after_begin")
def receive_after_begin(session, transaction, connection):
    org_id = org_id_var.get()
    if org_id:
        connection.execute(
            text("SELECT set_config('app.org_id', :org_id, true)"),
            {"org_id": str(org_id)}
        )


async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

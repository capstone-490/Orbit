from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies.db import SessionLocal


def get_db(
    x_organization_id: Annotated[str | None, Header()] = None,
) -> Generator[Session]:
    """
    Yields a database session per request, sets the PostgreSQL RLS context
    from the X-Organization-ID header (or allows system bypass if specified),
    and guarantees cleanup.
    Overridden in tests/conftest.py when testing without headers.
    """
    db = SessionLocal()
    try:
        if x_organization_id:
            # Set the tenant RLS boundary for this transaction
            db.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"),
                {"org_id": x_organization_id},
            )
        else:
            # Default to unauthenticated/no-tenant if no header is present
            db.execute(text("SELECT set_config('app.current_org_id', '', true)"))

        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]

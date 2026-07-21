"""Dependency provider for a request-scoped database session."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.session import get_db_session

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

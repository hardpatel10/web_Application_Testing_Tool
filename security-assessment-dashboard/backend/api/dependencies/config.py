"""Dependency providers for application configuration."""

from typing import Annotated

from fastapi import Depends

from backend.core.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]

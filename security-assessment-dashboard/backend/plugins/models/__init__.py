"""Pure data models for the plugin framework.

Every model here is a plain Pydantic v2 ``BaseModel`` (or, for the mutable
in-memory registry record, a ``dataclass``) with no I/O, no database
access, and no FastAPI/HTTP awareness. They are shared by every layer of
``backend.plugins`` (loader, registry, manager, validators) and are safe
for plugin authors to import directly.
"""

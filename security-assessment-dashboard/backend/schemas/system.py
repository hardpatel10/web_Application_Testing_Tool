"""Response schemas for the system information endpoint."""

from pydantic import BaseModel, Field


class SystemResponse(BaseModel):
    """Real host system information collected via the standard library and psutil."""

    operating_system: str = Field(description="OS name, e.g. 'Windows', 'Linux'.")
    os_release: str = Field(description="OS release/version string.")
    hostname: str = Field(description="Machine hostname.")
    architecture: str = Field(description="Machine architecture, e.g. 'AMD64', 'x86_64'.")
    cpu_count: int = Field(description="Number of logical CPUs available.")
    total_memory_bytes: int = Field(description="Total physical memory in bytes.")
    available_memory_bytes: int = Field(description="Currently available physical memory in bytes.")

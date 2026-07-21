"""Service layer for real host system information.

Collects data exclusively via the standard library and ``psutil``. No
value here is ever fabricated or estimated.
"""

import os
import platform
import socket

import psutil

from backend.schemas.system import SystemResponse


class SystemInfoService:
    """Reads live operating system and hardware information."""

    def get_system_info(self) -> SystemResponse:
        virtual_memory = psutil.virtual_memory()

        return SystemResponse(
            operating_system=platform.system(),
            os_release=platform.release(),
            hostname=socket.gethostname(),
            architecture=platform.machine(),
            cpu_count=os.cpu_count() or 0,
            total_memory_bytes=virtual_memory.total,
            available_memory_bytes=virtual_memory.available,
        )

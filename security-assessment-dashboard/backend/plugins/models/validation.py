"""Result shape shared by every validator in ``backend.plugins.validators``."""

from pydantic import BaseModel, Field


class PluginValidationResult(BaseModel):
    """Outcome of validating a plugin's manifest, directory, or interface.

    ``warnings`` never block loading/registration; ``errors`` do.
    """

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def merge(self, other: "PluginValidationResult") -> "PluginValidationResult":
        """Combine two results, remaining valid only if both are."""
        return PluginValidationResult(
            valid=self.valid and other.valid,
            errors=[*self.errors, *other.errors],
            warnings=[*self.warnings, *other.warnings],
        )

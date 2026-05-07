"""Error hierarchy used across the pipeline. Messages are in Spanish so the
Streamlit UI can surface them directly to end users."""
from __future__ import annotations


class PipelineError(Exception):
    """Base class for pipeline failures the UI should show as a friendly message."""


class SchemaInvalidError(PipelineError):
    """The Excel does not match the n8n structure."""


class EmptyAfterFilterError(PipelineError):
    """All rows were filtered out — nothing to report on."""


class LogoInvalidError(PipelineError):
    """The provided client logo is not a usable raster image."""


class ClientNameMissingError(PipelineError):
    """Client name is empty / blank."""

"""
Reporting Layer package.

Exposes the Reporting Layer entry point. The orchestrator
implementation itself is added in a subsequent batch; this package
only defines the public surface that callers depend on.
"""

from src.reporting.orchestrator import run_reporting_pipeline

__all__ = ["run_reporting_pipeline"]

"""
Reporting Layer Orchestrator.

Coordinates the complete Reporting Layer: publishing every Analytics
View and every Dimension, then reporting a summary. This module
contains no SQL and no CSV export logic — it only delegates to
``publisher.py``.
"""

import logging

from src.reporting.publisher import publish_dimensions, publish_views

logger = logging.getLogger(__name__)

_SEPARATOR = "=" * 50


def run_reporting_pipeline() -> dict[str, int]:
    """
    Run the complete Reporting Layer pipeline.

    Steps:
        1. Publish every Analytics View via ``publish_views()``.
        2. Publish every Dimension via ``publish_dimensions()``.
        3. Log a summary of the run.

    Returns:
        dict[str, int]: A summary of the run, e.g.
        ``{"views": 16, "dimensions": 6, "datasets": 22, "rows": 4210}``.
    """
    logger.info(_SEPARATOR)
    logger.info("Reporting Layer")
    logger.info(_SEPARATOR)

    views_published, views_rows = publish_views()
    dimensions_published, dimensions_rows = publish_dimensions()

    total_datasets = views_published + dimensions_published
    total_rows = views_rows + dimensions_rows

    logger.info(_SEPARATOR)
    logger.info("Views Published      : %d", views_published)
    logger.info("Dimensions Published : %d", dimensions_published)
    logger.info("Datasets Published   : %d", total_datasets)
    logger.info("Rows Exported        : %d", total_rows)
    logger.info(_SEPARATOR)
    logger.info("Reporting Layer Complete")

    return {
        "views": views_published,
        "dimensions": dimensions_published,
        "datasets": total_datasets,
        "rows": total_rows,
    }

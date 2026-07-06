# Assumptions and Limitations

## Table of Contents

- [Overview](#overview)
- [Purpose](#purpose)
- [Data Assumptions](#data-assumptions)
- [Architectural Assumptions](#architectural-assumptions)
- [Known Limitations](#known-limitations)
  - [1. Gold and Warehouse Layers Are Full Rebuilds, Not Incremental Merges](#1-gold-and-warehouse-layers-are-full-rebuilds-not-incremental-merges)
  - [2. Surrogate Keys Are Not Stable Across Runs](#2-surrogate-keys-are-not-stable-across-runs)
  - [3. Dimension Lookup Failures Are Silently Dropped by Reporting Views](#3-dimension-lookup-failures-are-silently-dropped-by-reporting-views)
  - [4. Business Validation Is Advisory, Not Enforced](#4-business-validation-is-advisory-not-enforced)
  - [5. Datatype Inference Is Heuristic and Column-Name-Agnostic](#5-datatype-inference-is-heuristic-and-column-name-agnostic)
  - [6. Brand and Platform Standardization Uses Hardcoded Lookup Tables](#6-brand-and-platform-standardization-uses-hardcoded-lookup-tables)
  - [7. Business Enrichment Is Implemented Only for Order Summary](#7-business-enrichment-is-implemented-only-for-order-summary)
  - [8. DimDate Is Order-Driven, Not Calendar-Driven](#8-dimdate-is-order-driven-not-calendar-driven)
  - [9. Configuration Layer Is Scaffolded but Unimplemented](#9-configuration-layer-is-scaffolded-but-unimplemented)
  - [10. No Automated Test Suite](#10-no-automated-test-suite)
  - [11. `requirements.txt` Is a Development Environment Freeze, Not a Pinned Dependency List](#11-requirementstxt-is-a-development-environment-freeze-not-a-pinned-dependency-list)
  - [12. Single-Machine, Single-Process Execution Only](#12-single-machine-single-process-execution-only)
  - [13. No Containerization or CI/CD in the Current Repository](#13-no-containerization-or-cicd-in-the-current-repository)
  - [14. Power BI Is Decoupled from the Warehouse](#14-power-bi-is-decoupled-from-the-warehouse)
- [Summary](#summary)

---

## Overview

This document lists the assumptions made during the design of the Restaurant POS ELT Pipeline and the limitations that currently exist in the implementation found in this repository. It is written directly from the source code in `src/`, `main.py`, `config/`, `tests/`, and the existing design notes in `docs/gold_layer.md` and `docs/grain_analysis.md`.

The goal of this document is to give future contributors and interviewers an honest picture of what the system does today, what it deliberately does not attempt, and where the current implementation would need to change before being operated as a continuously running production system.

## Purpose

Every non-trivial engineering decision involves a trade-off. This document exists so that those trade-offs are explicit rather than discovered later through a production incident. It separates:

- **Assumptions** — conditions the pipeline relies on being true about the source data or the operating environment.
- **Limitations** — behaviors of the current implementation that a contributor should be aware of before extending or operating the system.

---

## Data Assumptions

These assumptions were established during the grain analysis phase (see `docs/grain_analysis.md`) and are baked into the Business Silver and Gold layers.

| Assumption | Where It Is Encoded | Consequence if Violated |
|---|---|---|
| `invoice_no` is **not** globally unique; the business key for an order is `restaurant_name + invoice_no`. | `src/gold/dimensions/restaurant.py`, join logic in `src/gold/facts/orders.py` and `src/gold/facts/order_items.py` | If two branches ever share both an identical restaurant name and invoice number for different orders, those orders would be incorrectly treated as the same transaction. |
| `sub_order_type` follows the pattern `"<brand> - <platform>"`, or is a bare channel name (`Dine In`, `Delivery`, `Pick Up`) with no separator. | `src/transformation/business/parser.py` | Any other format (extra separators, different delimiter, missing platform) will parse incorrectly or produce a `None` brand/platform. |
| Only the Order Summary report carries `sub_order_type` and therefore only it can produce `brand`/`platform`. | `src/silver/runner.py` (enrichment is conditionally applied only when `dataset_name == "order_summary"`) | Order Summary Item and KOT records inherit brand/platform only through downstream joins back to Order Summary, not from their own source data. |
| Raw report files are always named consistently and grouped correctly by their parent folder (`order_summary`, `order_summary_item`, `kot_process_time`). | `src/ingestion/discovery.py` | A misplaced file in the wrong folder will be silently ingested and processed under the wrong report type. |
| KOT Excel exports contain a metadata block of variable length above the real header row, and the true header row can be identified by keyword matching. | `src/ingestion/excel_reader.py` | A KOT export whose header does not contain any of the recognized business keywords (`BUSINESS_COLUMN_KEYWORDS`) will raise `HeaderRowNotFoundError` and fail to load. |
| Source files are UTF-8 encoded (with a `utf-8-sig` fallback for BOM-prefixed CSVs). | `src/ingestion/csv_reader.py` | Files in other encodings (e.g. `latin-1`, `cp1252`) will raise `CSVReadError`. |
| A file is considered unchanged only if both its **filename** and its **SHA256 content hash** match a prior run. | `src/storage/hash_manager.py` | Renaming an already-processed file causes it to be reprocessed as if it were new; overwriting a file in place with new content but the same name is correctly detected as changed. |

## Architectural Assumptions

- The pipeline is assumed to run as a **single, sequential batch job** triggered manually or by an external scheduler (there is no scheduler bundled in this repository).
- The working directory is assumed to be the project root, since every path in `main.py` and the layer orchestrators (`Path("data") / "bronze"`, `Path("data/silver")`, `Path("data/warehouse")`, etc.) is relative rather than derived from a configuration source.
- The dataset volumes observed during development (roughly 30K rows/month for Order Summary, 53–56K rows/month for Order Summary Item, per `docs/grain_analysis.md`) are assumed to comfortably fit in memory on a single machine, since every layer operates on in-memory pandas DataFrames.
- DuckDB is assumed to be an acceptable analytical engine for the current data volume; the original grain-analysis document references a PostgreSQL Warehouse as the initially planned target (see [Design Decisions in the Gold Layer documentation](gold_layer.md)), but the implemented warehouse layer (`src/warehouse/writer.py`) uses DuckDB exclusively.

---

## Known Limitations

### 1. Gold and Warehouse Layers Are Full Rebuilds, Not Incremental Merges

`main.py` only passes the **newly written** Bronze files from the current run (`written_files`) into the Silver stage:

```python
silver_result = run_silver_pipeline_stage(written_files=written_files)
```

`src/silver/reader.py::load_bronze_data()` honors this by loading only the given `parquet_files` when a list is supplied, instead of the entire Bronze layer. The Silver DataFrames produced from that limited set are then concatenated and passed directly into `build_gold_layer()`.

Both persistence layers then perform a full overwrite of whatever they are given:

- `src/gold/writer.py` writes each Gold dataset to `data/gold/<prefix><name>/<prefix><name>.parquet`, unconditionally overwriting the existing file.
- `src/warehouse/writer.py` materializes every table using `CREATE OR REPLACE TABLE ... AS SELECT * FROM ...`.

**Consequence:** if the pipeline is run once with the full historical Bronze set and then run again with only a new month's files, the Gold Parquet files and DuckDB tables will contain **only the newest batch** — not the full history plus the new batch. The `should_process()` hash-skip logic in `src/storage/hash_manager.py` only protects the Bronze layer from redundant re-ingestion; it does not by itself keep Gold/Warehouse cumulative once files are skipped in a later run.

In the current single full-load usage pattern (all raw files present on first run, `written_files` therefore equal to the complete Bronze set) this behaves correctly. It becomes a correctness risk the moment the pipeline is operated in a genuinely incremental, drip-fed fashion across multiple runs.

### 2. Surrogate Keys Are Not Stable Across Runs

Every Gold dimension (e.g. `src/gold/dimensions/date.py`) assigns surrogate keys as a fresh sequential range (`range(1, len(dimension) + 1)`) computed at build time, based only on the distinct values present in the current run's Silver input. There is no persisted key registry that is read and extended between runs.

**Consequence:** combined with Limitation 1, a `date_key`, `brand_key`, `item_key`, etc. assigned in one run has no guaranteed relationship to the same value in a previous run. This is acceptable for a full-rebuild batch pipeline but would break any downstream system that stores or caches these keys across pipeline executions.

### 3. Dimension Lookup Failures Are Silently Dropped by Reporting Views

`src/gold/lookup.py::attach_dimension_keys()` uses `how="left"` merges, so a fact row whose business attribute does not match any dimension row keeps `NaN` in the corresponding key column rather than raising an error.

However, the SQL views defined in `src/warehouse/views.py` (the only interface Power BI is designed to query — see the module docstring: *"Power BI consumes only these SQL Views — it never queries the Warehouse tables or Gold directly"*) join facts to dimensions using `INNER JOIN`, for example in `vw_daily_sales`:

```sql
FROM fact_orders AS f
INNER JOIN dim_date AS d ON f.date_key = d.date_key
INNER JOIN dim_restaurant AS r ON f.restaurant_key = r.restaurant_key
```

**Consequence:** any fact row with a `NULL` surrogate key (a failed lookup) is present in the Gold Parquet file and the `fact_*` DuckDB table, but is **silently excluded** from every reporting view and therefore from every Power BI visual. There is no automated alert or count that surfaces how many rows were dropped this way during a normal pipeline run — the only way to detect it is to run the diagnostic script described in [Known Diagnostic Tooling](troubleshooting.md).

### 4. Business Validation Is Advisory, Not Enforced

`src/transformation/business_validator.py::validate_business_rules()` and `src/transformation/business/quality.py::validate_business_attributes()` are explicitly read-only: they return a list of human-readable error strings but never filter, quarantine, or halt processing of the offending rows.

`src/silver/runner.py` prints the validation error count and the error list to stdout for each dataset:

```python
print(f"Validation Errors    : {len(metadata['validation_errors'])}")
print(metadata["validation_errors"])
```

**Consequence:** rows with negative financial values, duplicate or null identifier candidates, impossible dates, unknown brands/platforms, or a brand present without a platform (and vice versa) are still written to Silver, Gold, and the Warehouse. Validation results are not persisted to a file, are not exposed through any API, and do not affect pipeline exit status. A contributor relying on "the pipeline ran successfully" as a data-quality signal will not be alerted to these conditions.

### 5. Datatype Inference Is Heuristic and Column-Name-Agnostic

`src/transformation/datatype_converter.py` deliberately infers column types (`datetime` → `numeric` → `boolean` → leave as text) purely from cell values, with no column-name allowlist or schema definition. A column is only cast to a given type if **100% of its non-null values** parse cleanly under that type.

**Consequence:** this makes the converter resilient to unexpected columns, but also means:

- A text identifier column that happens to be entirely numeric-looking (e.g. an all-digit ticket number) will be silently cast to `Int64`, which can strip leading zeros.
- A column with even a single malformed value in an otherwise clean numeric or date column falls back to remaining text, with no error or warning raised to indicate that inference failed.
- There is no persisted or versioned schema, so type drift between monthly exports is detected only if it happens to produce a visibly different DataFrame `dtype`.

### 6. Brand and Platform Standardization Uses Hardcoded Lookup Tables

`src/transformation/business/brand.py` (`_CANONICAL_BRANDS`) and `src/transformation/business/platform.py` (`_CANONICAL_PLATFORMS`) map known raw-value variants to a canonical form using in-code Python dictionaries. Unrecognized values are passed through unchanged rather than rejected.

**Consequence:** onboarding a new restaurant brand, a new delivery aggregator, or a new naming variant of an existing one requires a source-code change and redeployment — there is no external configuration file, database table, or admin interface for this mapping. This is a deliberate simplicity trade-off (see [Future Enhancements](future_enhancements.md)) but is a real limitation for a growing restaurant group.

### 7. Business Enrichment Is Implemented Only for Order Summary

`src/silver/runner.py` calls `enrich_business_attributes()` only when processing the `order_summary` dataset. Order Summary Item and KOT datasets do not receive `brand`, `platform`, `business_date`, `weekday`, `daypart`, etc. directly; those attributes are recovered for the Item fact only via a join back to Order Summary inside `src/gold/facts/order_items.py`, and the Kitchen fact derives its own `business_date` independently from `punch_time` rather than through enrichment.

**Consequence:** Business Silver enrichment is not a uniform, dataset-agnostic stage — it is currently special-cased to one dataset, and any new report type that needs the same brand/platform/calendar treatment would need equivalent one-off wiring rather than reusing a generic hook.

### 8. DimDate Is Order-Driven, Not Calendar-Driven

`src/gold/dimensions/date.py::build_date_dimension()` builds `DimDate` exclusively from the distinct `business_date` values already present in the enriched Silver Order Summary dataset. It is not generated from a continuous calendar range, and it is not derived from KOT punch-time dates.

**Consequence:** if the kitchen (KOT) dataset contains a preparation event on a date with no corresponding order in Order Summary — or if the pipeline needs pre-populated future dates for planning dashboards — `DimDate` will not contain that date, the `FactKitchen` row's `date_key` lookup will fail, and (per Limitation 3) that row will be silently excluded from `vw_kitchen_performance` and any other view that joins through `dim_date`.

### 9. Configuration Layer Is Scaffolded but Unimplemented

The `config/` package (`settings.py`, `constants.py`, `database.py`, `logging.yaml`, `reports.yaml`) and `src/core/` (`config_loader.py`, `logger.py`) exist as empty files. No module in `src/` imports from `config/` or `src/core/`.

**Consequence:** every path, table name, and threshold used by the pipeline today is a module-level constant hardcoded at its point of use (for example, `BRONZE_ROOT = Path("data") / "bronze"` in `main.py`, and similarly-named constants repeated across `src/storage/parquet_writer.py`, `src/silver/writer.py`, `src/gold/writer.py`, `src/warehouse/writer.py`, and `src/reporting/reporting_config.py`). Changing a root data directory, a database file name, or a logging format currently means editing multiple source files rather than one configuration file.

### 10. No Automated Test Suite

The `tests/` directory contains four files, none of which use `assert` statements or pytest-style `test_`-prefixed functions:

| File | Actual Purpose |
|---|---|
| `tests/test_gold.py` | A manually-run integration script (`python tests/test_gold.py`) that builds the Gold layer and prints shape/key summaries. Its own docstring states it is *"NOT a pytest unit test"*. |
| `tests/test_business_silver.py` | A manually-run script that prints a sample of enriched rows for visual inspection. |
| `tests/debug_gold_lookup_failures.py` | A diagnostic script (not a test) that prints null-key statistics for each fact table. |
| `tests/debug_order_items_merge.py` | A diagnostic script investigating the Order Items → Order Summary join. |

**Consequence:** running `pytest` against this repository collects these files (because of the `test_*.py` naming convention) but finds zero test functions to execute, since none of the module-level functions are named with a `test_` prefix — `pytest` will report zero tests collected rather than passing tests. `pytest` is listed in `requirements.txt`, but there is currently no automated regression suite; every validation described above requires a human to run the script and read its printed output.

### 11. `requirements.txt` Is a Development Environment Freeze, Not a Pinned Dependency List

`requirements.txt` (94 packages) reads as a full `pip freeze` of a local Jupyter/JupyterLab development environment — it includes packages such as `jupyterlab`, `notebook`, `ipykernel`, `black`, `isort`, and `mypy_extensions`, none of which the pipeline code imports. At the same time, it is **missing `duckdb`**, which is imported directly by `src/warehouse/writer.py` and `src/reporting/publisher.py`.

**Consequence:** a clean `pip install -r requirements.txt` followed by `python main.py` will succeed through Bronze, Silver, and Gold, then fail at the Warehouse stage with `ModuleNotFoundError: No module named 'duckdb'`. See [Troubleshooting](troubleshooting.md) for the exact failure point and fix.

### 12. Single-Machine, Single-Process Execution Only

Every stage of the pipeline (`main.py`) runs sequentially in one Python process, using pandas DataFrames held entirely in memory. There is no parallelism across files within a stage, no distributed processing engine, and no queue-based or streaming ingestion path.

**Consequence:** the pipeline's throughput and maximum practical dataset size are bounded by a single machine's memory and single-core pandas performance. This is a reasonable and intentional trade-off at the current data volume (tens of thousands of rows per month) but would need re-architecture (chunked processing, a distributed engine, or a different storage/compute split) before it could handle materially larger POS estates.

### 13. No Containerization or CI/CD in the Current Repository

There is no `Dockerfile`, `docker-compose.yml`, `.github/workflows/` directory, or `Makefile` anywhere in the uploaded repository. The pipeline is invoked directly with `python main.py` from an activated virtual environment (a `.venv` directory is present in the upload).

**Consequence:** there is currently no reproducible container build, no automated CI validation on push/PR, and no single documented command target (`make run`, `make test`, etc.) for common developer operations. Any documentation elsewhere in this project that references Docker or GitHub Actions describes a target end-state rather than the current repository content.

### 14. Power BI Is Decoupled from the Warehouse

Power BI is designed (per the docstring in `src/warehouse/views.py`) to consume only the CSV files published by the Reporting Layer (`data/reporting/views/*.csv`, `data/reporting/dimensions/*.csv`) rather than connecting live to the DuckDB warehouse or Gold layer.

**Consequence:** the `.pbix` file at `powerbi/dashboards/Restaurant_POS_Analytics.pbix` reflects whatever state the CSV exports were in the last time the Reporting Layer ran and the workbook was refreshed against them. There is no live query connection, no scheduled refresh automation, and no versioning of the CSV snapshots — refreshing the dashboard for a new pipeline run is a manual step of re-pointing or re-importing the CSVs in Power BI Desktop.

---

## Summary

The pipeline implements a complete, working Bronze → Silver → Business Silver → Gold → DuckDB Warehouse → Reporting Views → Power BI flow, with genuinely useful engineering touches: content-hash-based Bronze idempotency, evidence-based grain analysis before modeling, a content-based Excel header detector, and dedicated diagnostic scripts for surrogate-key lookup failures.

The most consequential limitations to understand before extending or operating this system are that **Gold and Warehouse are full rebuilds rather than incremental merges**, that **failed dimension lookups are silently excluded by the reporting views rather than surfaced**, and that **data-quality validation is currently advisory rather than enforced**. None of these are defects introduced by accident — they are the natural consequence of a project that prioritized getting an evidence-based, correctly-modeled dimensional warehouse working end-to-end before investing in incremental-load semantics, alerting, and automated testing. The [Future Enhancements](future_enhancements.md) document outlines a realistic path for addressing each of them.

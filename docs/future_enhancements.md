# Future Enhancements

## Table of Contents

- [Overview](#overview)
- [Purpose](#purpose)
- [Prioritization Approach](#prioritization-approach)
- [Near-Term Enhancements](#near-term-enhancements)
  - [1. Fix the Missing `duckdb` Dependency](#1-fix-the-missing-duckdb-dependency)
  - [2. Turn `tests/` Into an Actual Automated Suite](#2-turn-tests-into-an-actual-automated-suite)
  - [3. Surface Dropped Fact Rows Instead of Silently Excluding Them](#3-surface-dropped-fact-rows-instead-of-silently-excluding-them)
  - [4. Persist and Alert on Business Validation Results](#4-persist-and-alert-on-business-validation-results)
- [Medium-Term Enhancements](#medium-term-enhancements)
  - [5. True Incremental Gold and Warehouse Loading](#5-true-incremental-gold-and-warehouse-loading)
  - [6. Stable Surrogate Keys Across Runs](#6-stable-surrogate-keys-across-runs)
  - [7. Externalize Brand and Platform Standardization](#7-externalize-brand-and-platform-standardization)
  - [8. Implement the Scaffolded `config/` and `src/core/` Modules](#8-implement-the-scaffolded-config-and-srccore-modules)
  - [9. Calendar-Driven `DimDate`](#9-calendar-driven-dimdate)
- [Longer-Term Enhancements](#longer-term-enhancements)
  - [10. Containerize the Pipeline](#10-containerize-the-pipeline)
  - [11. CI Pipeline via GitHub Actions](#11-ci-pipeline-via-github-actions)
  - [12. Scheduled, Automated Power BI Refresh](#12-scheduled-automated-power-bi-refresh)
  - [13. Extend Business Enrichment to Order Items and KOT Natively](#13-extend-business-enrichment-to-order-items-and-kot-natively)
  - [14. Schema Contracts for Source Reports](#14-schema-contracts-for-source-reports)
- [Explicitly Out of Scope](#explicitly-out-of-scope)
- [Summary](#summary)

---

## Overview

This document lists realistic, evidence-based next steps for the Restaurant POS ELT Pipeline. Every item here is a direct response to a specific limitation identified in [Assumptions and Limitations](assumptions_and_limitations.md) and is grounded in the actual code structure of this repository — no enhancement below assumes infrastructure, tooling, or architecture that isn't already implied by the existing design (for example, the project already commits to DuckDB and a Star Schema, so enhancements build on that rather than proposing a different warehouse engine).

## Purpose

A portfolio project benefits from showing not just what was built, but that the author understands where the current implementation would need to evolve to be operated as a real, continuously-running production system. This document is that roadmap, written at the level of specificity an interviewer or future contributor would expect: which module changes, in which order, for which reason.

## Prioritization Approach

Enhancements are grouped by the effort/impact trade-off:

- **Near-Term** — small, isolated changes with immediate correctness or reliability benefit.
- **Medium-Term** — changes that touch the core incremental-loading and modeling contracts of the Gold/Warehouse layers.
- **Longer-Term** — operational maturity (CI/CD, containerization, scheduling) that depends on the near/medium-term work being stable first.

---

## Near-Term Enhancements

### 1. Fix the Missing `duckdb` Dependency

`src/warehouse/writer.py` and `src/reporting/publisher.py` both `import duckdb`, but `duckdb` is absent from `requirements.txt`. The immediate fix is to add a pinned `duckdb` entry to `requirements.txt` and, ideally, replace the current `pip freeze`-style dependency list with a minimal, intentional list containing only the packages the pipeline code actually imports (`pandas`, `pyarrow`, `openpyxl`, `duckdb`), separate from development-only tooling (`jupyterlab`, `black`, `isort`, `pytest`) which could live in a `requirements-dev.txt`.

### 2. Turn `tests/` Into an Actual Automated Suite

`tests/test_gold.py` and `tests/test_business_silver.py` already contain the right assertions in spirit — they check dimension/fact counts, key presence, and row-level sampling — but express them as `print()` statements inside a `main()` function rather than `assert` statements inside `test_`-prefixed functions. Converting the existing logic in `_EXPECTED_DIMENSION_COUNT`, `_EXPECTED_FACT_COUNT`, and the per-key null checks in `debug_gold_lookup_failures.py` into real pytest assertions (e.g. `assert null_count == 0, f"{key_column} has {null_count} unmatched rows"`) would let `pytest` actually catch regressions, using fixtures built from the small sample data already present under `data/silver/`.

### 3. Surface Dropped Fact Rows Instead of Silently Excluding Them

Because `src/warehouse/views.py` uses `INNER JOIN` between facts and dimensions, rows with failed lookups (documented in Limitation 3 of [Assumptions and Limitations](assumptions_and_limitations.md)) simply disappear from every Power BI visual. A near-term fix that requires no schema change is to add a lightweight reconciliation step to `src/warehouse/orchestrator.py` that runs a `COUNT(*)` on each `fact_*` table versus its corresponding view and logs (or fails loudly on) any discrepancy, effectively productionizing the logic already prototyped in `tests/debug_gold_lookup_failures.py`.

### 4. Persist and Alert on Business Validation Results

`validate_business_rules()` and `validate_business_attributes()` already produce structured lists of validation error strings; they are simply discarded after being printed. Writing these to a `data/metadata/validation_report.json` (or a small DuckDB `validation_log` table) per pipeline run — including counts by rule and by dataset — would convert the existing read-only validation logic into an auditable data-quality signal without changing any transformation behavior.

## Medium-Term Enhancements

### 5. True Incremental Gold and Warehouse Loading

The most structurally significant enhancement is changing `src/gold/writer.py` and `src/warehouse/writer.py` from unconditional overwrite (`to_parquet` and `CREATE OR REPLACE TABLE`) to a merge/upsert model. Concretely: Gold fact tables would need to be appended to (with duplicate protection on their business grain — `restaurant_name + invoice_no` for orders, as already established in `docs/grain_analysis.md`) rather than replaced outright, and Gold dimensions would need to be extended (new distinct values added, existing surrogate keys preserved) rather than rebuilt from scratch. This directly resolves Limitation 1.

### 6. Stable Surrogate Keys Across Runs

This follows naturally from item 5: once dimensions are no longer rebuilt from zero every run, each `build_*_dimension()` function (e.g. `src/gold/dimensions/date.py`) needs to read the existing dimension table first, identify genuinely new business keys, and assign new surrogate keys starting from `MAX(existing_key) + 1` rather than always starting the range at 1. This is a contained, well-scoped change since the surrogate-key assignment logic is already isolated into a single `_assign_surrogate_key()` style helper per dimension file.

### 7. Externalize Brand and Platform Standardization

`_CANONICAL_BRANDS` in `src/transformation/business/brand.py` and `_CANONICAL_PLATFORMS` in `src/transformation/business/platform.py` are currently Python dictionaries. Moving these into a data file (CSV, JSON, or a small `dim_brand_alias` / `dim_platform_alias` reference table read at startup) would let new brand/platform variants be onboarded by a data change rather than a code change and deployment — a natural fit for the currently-empty `config/` package described in item 8.

### 8. Implement the Scaffolded `config/` and `src/core/` Modules

`config/settings.py`, `config/constants.py`, `config/database.py`, `config/reports.yaml`, `config/logging.yaml`, `src/core/config_loader.py`, and `src/core/logger.py` already exist as placeholders with clear, implied responsibilities from their filenames and their position in the package structure. A realistic next step is to centralize the currently-hardcoded path constants (`Path("data") / "bronze"`, `Path("data/warehouse") / "restaurant_pos.duckdb"`, etc. — repeated across `main.py`, `src/storage/parquet_writer.py`, `src/silver/writer.py`, `src/gold/writer.py`, `src/warehouse/writer.py`, and `src/reporting/reporting_config.py`) into a single `config/settings.py`, loaded once via `src/core/config_loader.py`, and to route the current ad-hoc `logging.basicConfig()` call in `main.py` through a proper `config/logging.yaml`-driven setup in `src/core/logger.py`.

### 9. Calendar-Driven `DimDate`

Rebuilding `build_date_dimension()` to generate a continuous date range (e.g. from the minimum observed business date to some forward-looking horizon) rather than only the distinct dates observed in Order Summary would eliminate the KOT-to-`DimDate` grain mismatch described in Limitation 8, and would also let Power BI dashboards correctly show zero-order days instead of omitting them entirely.

## Longer-Term Enhancements

### 10. Containerize the Pipeline

No `Dockerfile` exists in the current repository. Once the dependency list is cleaned up (item 1), a straightforward `Dockerfile` based on a slim Python image, plus a `docker-compose.yml` mounting `data/` as a volume, would make the pipeline reproducible outside of the developer's local `.venv`.

### 11. CI Pipeline via GitHub Actions

Once item 2 produces real pytest assertions, a `.github/workflows/ci.yml` running `pip install -r requirements.txt` and `pytest` on every push/PR would catch regressions automatically. This is deliberately sequenced after test automation rather than before it, since a CI pipeline that only runs print-based scripts provides no actual regression protection.

### 12. Scheduled, Automated Power BI Refresh

Today, refreshing `powerbi/dashboards/Restaurant_POS_Analytics.pbix` requires a person to re-run the pipeline and manually refresh the Power BI workbook against the newly exported CSVs in `data/reporting/`. A realistic longer-term improvement — once the pipeline is containerized and incremental (items 5 and 10) — is scheduling the pipeline via an external orchestrator (e.g. a cron job or a lightweight scheduler) and either publishing the CSVs to a location Power BI Service can poll, or triggering a Power BI dataset refresh via the Power BI REST API.

### 13. Extend Business Enrichment to Order Items and KOT Natively

Currently only Order Summary receives `enrich_business_attributes()` directly (Limitation 7); Order Items recovers brand/platform via a join in `src/gold/facts/order_items.py`, and KOT never receives it at the Silver stage at all. Generalizing `enrich_business_attributes()` so it can be applied uniformly (where the necessary source columns exist) would reduce the amount of dataset-specific special-casing in `src/silver/runner.py` and `src/gold/facts/`.

### 14. Schema Contracts for Source Reports

`src/transformation/datatype_converter.py` infers types purely from values with no declared schema (Limitation 5). A longer-term improvement is defining an explicit expected-schema contract per report type (column name, expected dtype, nullability) that the pipeline can validate incoming Bronze data against before Silver transformation, raising a clear, actionable error the first time a POS export's structure drifts, rather than allowing silent type-inference fallbacks.

---

## Explicitly Out of Scope

To keep this roadmap honest and grounded in what this repository actually does, the following are **not** proposed, because they are not implied by the current architecture, data volume, or stated project goals:

- Replacing DuckDB with a distributed warehouse (Snowflake, BigQuery, Redshift) — current data volumes (tens of thousands of rows/month per `docs/grain_analysis.md`) do not justify this, and the project's own design notes treat DuckDB as the settled choice.
- Real-time or streaming ingestion — the source data is periodic POS export files (CSV/XLSX), not an event stream.
- Multi-tenant or multi-restaurant-group architecture — the current dimensional model is scoped to a single restaurant group's brands and platforms.

## Summary

The realistic next steps for this project fall into three tiers: fixing small, contained correctness gaps (the missing `duckdb` dependency, un-asserted tests, silent lookup-failure exclusion, discarded validation output); addressing the structural incremental-loading and key-stability gaps in Gold and Warehouse; and finally investing in the operational maturity (containerization, CI, scheduled refresh) that depends on the first two tiers being solid. This sequencing — correctness first, architecture second, operations third — reflects how the project's own documentation (`docs/grain_analysis.md`) already prioritized evidence-based modeling over premature infrastructure investment.

# Restaurant POS ELT Pipeline — Project Overview

## Table of Contents

- [Executive Summary](#executive-summary)
- [Business Problem](#business-problem)
- [Project Objectives](#project-objectives)
- [Scope](#scope)
- [Business Value](#business-value)
- [Technology Stack](#technology-stack)
- [Key Features](#key-features)
- [Pipeline Overview](#pipeline-overview)
- [Deliverables](#deliverables)
- [High-Level Workflow](#high-level-workflow)
- [Repository Highlights](#repository-highlights)

---

## Executive Summary

The Restaurant POS ELT Pipeline is an end-to-end data engineering system that ingests raw Point-of-Sale (POS) exports from a multi-location restaurant brand group and transforms them into a governed, analytics-ready dimensional model. The pipeline follows the **Medallion Architecture** (Bronze → Silver → Gold), materializes the Gold layer into a **DuckDB** analytical warehouse, exposes a curated set of **SQL analytics views**, publishes those views as CSV datasets for downstream consumption, and feeds a set of **Power BI** dashboards used for executive, sales, and operational reporting.

The system currently processes POS exports for **6 restaurant outlets** operating under **2 brands** (Thepla House By Tejals and Homely & Healthy), across **6 order platforms** (Dine In, Pick Up, Delivery, Swiggy, Zomato, and Swiggy via Toing), covering a two-month operating window (May–June 2026) in the committed sample dataset. In that window the pipeline processes **61,838 orders**, **109,428 order line items**, and **107,027 kitchen ticket (KOT) records** into a 6-dimension, 3-fact star schema.

The pipeline is fully containerized (Docker + Docker Compose), automated via a GitHub Actions workflow that runs the pipeline on every push and pull request to `main`, and is designed to be re-run safely and repeatedly: a SHA-256 content-hash mechanism ensures that unchanged raw files are never reprocessed, while changed or new files are always picked up.

## Business Problem

Restaurant groups operating across multiple outlets, multiple ordering platforms (dine-in, pickup, delivery, and third-party aggregators such as Swiggy and Zomato), and multiple sub-brands accumulate operational data in a form that is difficult to analyze directly:

- POS exports arrive as **heterogeneous CSV and Excel files**, one file per report per time period, with inconsistent formatting — Excel exports in particular are exported with a variable-length metadata block (report title, filters, date ranges) sitting above the actual data table.
- The same business concept (brand, platform) is recorded inconsistently across exports — e.g. `"Homely & Healthy"`, `"Homely and Healthy"`, and `"Homely & Healthy App"` all refer to the same brand, and `"Swiggy"` and `"Swiggy (Toing)"` both refer to the same aggregator.
- Order-level financial data (order summary), line-item detail (order summary item), and kitchen operations data (KOT process time) are captured in **three separate, unrelated exports** with no shared surrogate keys, making cross-report analysis (e.g. "which items sell best on Zomato" or "how does prep time affect order status") impossible without an integration layer.
- There is no single, queryable source of truth that a BI tool can connect to. Analysts are left manually opening spreadsheets per outlet, per platform, per month.

Without a structured pipeline, business stakeholders cannot reliably answer operational questions such as: Which restaurant is the top performer this month? Which platform yields the highest average order value? Is kitchen prep time degrading for a given order type? Why are orders being cancelled?

## Project Objectives

1. Build a repeatable, idempotent ELT pipeline that ingests raw POS exports (CSV and Excel) without manual intervention.
2. Preserve raw source data untouched (Bronze) while progressively cleaning, standardizing, and enriching it (Silver) with restaurant-domain business context (brand, platform, calendar, daypart).
3. Model the cleaned data into a conformed dimensional (star) schema (Gold) suitable for BI consumption.
4. Persist the Gold model into a lightweight, embedded analytical warehouse (DuckDB) with zero external database infrastructure.
5. Expose a curated, business-friendly analytics layer (SQL views) on top of the warehouse, decoupling raw table structure from what Power BI actually queries.
6. Publish those analytics views as portable CSV datasets for auditing, ad hoc analysis, or environments without direct DuckDB access.
7. Provide a Power BI dashboard suite (Executive, Sales, Operational) that consumes only the analytics layer, never the raw warehouse tables directly.
8. Make the entire pipeline reproducible via Docker and automatically verified on every code change via CI.

## Scope

**In scope:**
- Ingestion of `order_summary`, `order_summary_item`, and `kot_process_time` POS report families from `data/raw/`.
- Bronze persistence (Parquet), Silver cleaning/standardization/enrichment, Gold dimensional modeling, DuckDB warehouse materialization, SQL analytics views, CSV publishing, and Power BI dashboards built on top of that CSV/warehouse output.
- Incremental processing via SHA-256 file-hash tracking (`data/metadata/processed_files.json`).
- Containerized execution via Docker/Docker Compose and a Makefile-based developer workflow.
- Continuous integration via GitHub Actions (installs dependencies and runs the full pipeline on every push/PR to `main`).

**Out of scope (not implemented in this repository):**
- A live/streaming ingestion path — the pipeline is a batch, file-based ELT job triggered by running `main.py`.
- A hosted or cloud-based data warehouse (Snowflake, BigQuery, Redshift, etc.) — the warehouse is the embedded, file-based DuckDB engine only.
- Automated Power BI publishing/refresh (`.pbix` files and exports are committed as build artifacts under `powerbi/`; there is no scripted publish-to-Power-BI-Service step in this repository).
- A REST or web API layer — there is no application server; the project is a data pipeline invoked from the command line or a container.
- Multi-tenant or multi-brand-group support beyond what is present in the raw POS exports currently checked into `data/raw/`.

## Business Value

| Capability | Business Value |
|---|---|
| Automated Bronze/Silver/Gold pipeline | Removes manual spreadsheet consolidation across outlets, brands, and platforms |
| Brand & platform standardization | Enables accurate cross-brand and cross-platform comparison despite inconsistent POS labeling |
| Business calendar & daypart enrichment | Enables trend analysis by weekday, month, quarter, and meal period without recomputation in BI tools |
| Conformed star schema (Gold) | Gives every downstream consumer (DuckDB, Power BI, CSV) a single consistent definition of "an order," "an item," "a restaurant," etc. |
| DuckDB warehouse + SQL analytics views | Provides fast, SQL-queryable access to curated metrics (daily sales, platform performance, brand performance, kitchen performance) without hand-written joins in every report |
| CSV export layer | Makes governed datasets portable to any tool (Excel, Power BI, ad hoc Python/pandas analysis) without requiring a database connection |
| Incremental hash-based processing | Reduces re-processing cost and pipeline runtime on repeated runs; a re-run only touches new or changed files |
| Docker + CI | Guarantees the pipeline runs identically on any machine and is validated automatically on every code change |

## Technology Stack

| Layer | Technology |
|---|---|
| Programming Language | Python |
| Data Processing | pandas |
| Columnar Storage | Parquet (via PyArrow) |
| Analytical Warehouse | DuckDB |
| Visualization | Power BI |
| Containerization | Docker, Docker Compose |
| Automation / Developer Workflow | Makefile |
| Continuous Integration | GitHub Actions |
| Version Control | Git |

Runtime dependencies are pinned in `requirements/requirements-runtime.txt` (pandas, numpy, pyarrow, duckdb, SQLAlchemy, openpyxl, python-dotenv, PyYAML, loguru, requests); development-only dependencies (testing, linting, notebooks) are isolated in `requirements/requirements-dev.txt` so the production container image stays minimal.

## Key Features

- **Dual-format ingestion** — a single discovery step (`src/ingestion/discovery.py`) recursively scans `data/raw/`, groups files by report type, and dispatches each file to a dedicated CSV or Excel reader.
- **Content-aware Excel header detection** — `src/ingestion/excel_reader.py` scans the first 30 rows of a KOT Excel export and scores each row against a list of known POS business column names (KOT, Item Name, Quantity, Process Time, etc.) to locate the true header row, rather than assuming a fixed row offset. This tolerates POS exports whose metadata block above the table varies in length.
- **SHA-256 incremental ingestion** — every raw file is hashed; a file is only reprocessed if its filename is new or its hash has changed, making repeated pipeline runs cheap and safe.
- **Generic Silver transformation engine** — a five-step, dataset-agnostic pipeline (column standardization → null normalization → datatype inference → business-rule validation → duplicate removal) applied uniformly to every Bronze dataset.
- **Business Silver enrichment** — brand/platform extraction and canonicalization from the `sub_order_type` field, plus derived business calendar attributes (business date, weekday, month, quarter, year) and daypart classification (Breakfast, Lunch, Snacks, Dinner, Late Night), applied specifically to the order summary dataset.
- **Row-level business validation** — every enriched row is checked for unknown brands/platforms, missing calendar/daypart values, and brand/platform consistency, with violations recorded (not silently dropped) in a `business_validation_errors` column.
- **Star-schema Gold layer** — 6 conformed dimensions (Date, Restaurant, Brand, Platform, Category, Item) and 3 facts (Orders, Order Items, Kitchen), joined via generated surrogate keys rather than natural keys.
- **DuckDB warehouse materialization** — Gold DataFrames are registered directly with DuckDB and materialized via `CREATE OR REPLACE TABLE ... AS SELECT`, avoiding slower `DataFrame.to_sql()`-style inserts.
- **Analytics view layer** — a dedicated SQL layer (`src/warehouse/views.py`) that Power BI and the reporting layer query exclusively, keeping BI tools decoupled from the physical `dim_*`/`fact_*` table structure.
- **CSV publishing layer** — every analytics view and every dimension is exported to `data/reporting/` as CSV, giving a portable, warehouse-independent snapshot of the curated data.
- **Containerized, CI-verified execution** — the entire pipeline runs identically via `docker compose up` locally and via GitHub Actions on every push/PR.

## Pipeline Overview

```
data/raw (CSV / Excel)
        |
        v
   Discovery & Loading        (src/ingestion)
        |
        v
   Bronze Layer (Parquet)     (src/storage)
        |
        v
   Generic Silver Layer       (src/transformation)
        |
        v
   Business Silver Layer      (src/transformation/business)
        |
        v
   Gold Layer (Star Schema)   (src/gold)
        |
        v
   DuckDB Warehouse           (src/warehouse)
        |
        v
   Analytics SQL Views        (src/warehouse/views.py)
        |
        v
   Reporting CSV Exports      (src/reporting)
        |
        v
   Power BI Dashboards        (powerbi/)
```

Each stage is implemented as an independent, single-responsibility package under `src/`, coordinated by a thin orchestrator per stage and driven end-to-end by `main.py`.

## Deliverables

- A runnable Python pipeline (`main.py`) that executes the complete Bronze → Silver → Gold → Warehouse → Reporting flow in a single invocation.
- A populated Bronze, Silver, and Gold data lake under `data/`, reflecting the current committed sample of two months of POS exports.
- A DuckDB warehouse file (`data/warehouse/restaurant_pos.duckdb`) containing 9 physical tables (6 dimensions, 3 facts) and a set of analytics views built on top of them.
- Published CSV datasets under `data/reporting/views/` and `data/reporting/dimensions/`, ready for direct consumption by Power BI or any spreadsheet tool.
- A Power BI dashboard file (`powerbi/dashboards/Restaurant_POS_Analytics.pbix`), an exported PDF of the dashboards (`powerbi/exports/dashboards.pdf`), dashboard screenshots, and a custom Power BI theme (`powerbi/themes/Theme.json`).
- A Docker image definition and Docker Compose service for running the pipeline in an isolated, reproducible environment.
- A GitHub Actions workflow that installs dependencies and executes the pipeline on every push and pull request to `main`, acting as a continuous, executable regression check.
- Two standalone validation scripts (`tests/test_business_silver.py`, `tests/test_gold.py`) that exercise the Business Silver enrichment and the Gold layer build against real committed data.

## High-Level Workflow

1. A developer or CI job places new POS export files (CSV/Excel) under the appropriate `data/raw/<report_name>/` folder.
2. Running `python main.py` (or `docker compose up`) triggers `run_pipeline()`, which:
   - Discovers and loads all raw files.
   - Hashes each file and skips any that are unchanged since the last run.
   - Writes new/changed files to the Bronze layer as Parquet.
   - Runs every Bronze dataset through the generic Silver transformation pipeline, applying Business Silver enrichment to the order summary dataset.
   - Writes the resulting Silver datasets to disk.
   - Builds the Gold star schema (6 dimensions, 3 facts) from the enriched Silver data and writes it to Parquet.
   - Materializes the Gold layer into DuckDB and (re)creates the analytics SQL views.
   - Publishes every analytics view and dimension to CSV under `data/reporting/`.
3. Power BI (already configured against the DuckDB analytics views or the published CSVs) is refreshed to reflect the latest data.
4. If no new or changed raw files are found, the pipeline reports the Bronze stage as complete and explicitly skips the Silver, Gold, and Warehouse stages for that run, avoiding unnecessary recomputation.

## Repository Highlights

- **Layered, single-responsibility packages** — `src/ingestion`, `src/storage`, `src/transformation`, `src/silver`, `src/gold`, `src/warehouse`, and `src/reporting` each own exactly one concern, coordinated by a thin `orchestrator.py` per stage; no package reaches into another package's internal helpers.
- **Pure transformation modules** — nearly every module in `src/transformation/business/` (parser, brand, platform, calendar, daypart, quality) is a dependency-free, side-effect-free function operating on plain Python or pandas values, making them trivially unit-testable in isolation.
- **Explicit architectural boundary between the Warehouse and the Analytics Layer** — `src/warehouse/writer.py` (physical `dim_*`/`fact_*` tables) and `src/warehouse/views.py` (analytics SQL views) are deliberately separated, and the codebase documents this as a frozen decision: Power BI consumes only the views, never the physical tables directly.
- **Real committed data, not synthetic samples** — the repository ships with real Bronze/Silver/Gold Parquet files and a real DuckDB warehouse file reflecting two months of actual POS exports from six outlets, so the pipeline's outputs can be inspected directly.
- **Traceable ingestion metadata** — every ingested source file's name and SHA-256 hash is recorded in `data/metadata/processed_files.json`, giving a complete audit trail of what has been processed and when.

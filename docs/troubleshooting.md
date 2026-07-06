# Troubleshooting Guide

## Table of Contents

- [Overview](#overview)
- [Purpose](#purpose)
- [How to Read This Guide](#how-to-read-this-guide)
- [Setup and Environment Issues](#setup-and-environment-issues)
  - [`ModuleNotFoundError: No module named 'duckdb'`](#modulenotfounderror-no-module-named-duckdb)
  - [`ModuleNotFoundError` for `openpyxl`, `pandas`, or `pyarrow` Despite Installing Requirements](#modulenotfounderror-for-openpyxl-pandas-or-pyarrow-despite-installing-requirements)
  - [`pytest` Reports "no tests ran" or "collected 0 items"](#pytest-reports-no-tests-ran-or-collected-0-items)
- [Ingestion and Discovery Issues](#ingestion-and-discovery-issues)
  - [`RawDirectoryNotFoundError: Raw directory does not exist`](#rawdirectorynotfounderror-raw-directory-does-not-exist)
  - [`NoSupportedFilesFoundError: No supported .csv or .xlsx files found`](#nosupportedfilesfounderror-no-supported-csv-or-xlsx-files-found)
  - [A File Is Ingested Under the Wrong Report Name](#a-file-is-ingested-under-the-wrong-report-name)
  - [`HeaderRowNotFoundError` When Reading a KOT Excel File](#headerrownotfounderror-when-reading-a-kot-excel-file)
  - [`CSVReadError` on a Specific CSV File](#csvreaderror-on-a-specific-csv-file)
- [Bronze Layer / Idempotency Issues](#bronze-layer--idempotency-issues)
  - ["Skipping already processed file" for a File You Expected to Reprocess](#skipping-already-processed-file-for-a-file-you-expected-to-reprocess)
  - [`processed_files.json` Looks Corrupted or `json.JSONDecodeError` Is Raised](#processed_filesjson-looks-corrupted-or-jsonjsondecodeerror-is-raised)
  - [`FileExistsError` When Writing a Bronze Parquet File](#fileexistserror-when-writing-a-bronze-parquet-file)
- [Silver and Business Silver Issues](#silver-and-business-silver-issues)
  - ["No new Bronze datasets detected" — Silver/Gold/Warehouse All Skipped](#no-new-bronze-datasets-detected--silvergoldwarehouse-all-skipped)
  - [`brand` / `platform` Columns Are Missing or All `None`](#brand--platform-columns-are-missing-or-all-none)
  - ["Unknown brand" / "Unknown platform" Appears in Validation Output](#unknown-brand--unknown-platform-appears-in-validation-output)
  - [A Numeric-Looking ID Column Loses Its Leading Zeros](#a-numeric-looking-id-column-loses-its-leading-zeros)
- [Gold Layer Issues](#gold-layer-issues)
  - [Row Counts in a Fact Table Are Lower Than Expected in Power BI](#row-counts-in-a-fact-table-are-lower-than-expected-in-power-bi)
  - [Diagnosing Which Dimension Is Causing Dropped Rows](#diagnosing-which-dimension-is-causing-dropped-rows)
  - [Gold Output Only Reflects the Latest Run, Not Full History](#gold-output-only-reflects-the-latest-run-not-full-history)
- [Warehouse Layer Issues](#warehouse-layer-issues)
  - [`duckdb.IOException` — Database File Is Locked](#duckdbioexception--database-file-is-locked)
  - [A Table Appears Empty or Missing After a Run](#a-table-appears-empty-or-missing-after-a-run)
- [Reporting Layer Issues](#reporting-layer-issues)
  - [`duckdb.Error` When Publishing a View or Dimension](#duckdberror-when-publishing-a-view-or-dimension)
  - [CSV Files in `data/reporting/` Are Stale](#csv-files-in-datareporting-are-stale)
- [Power BI Issues](#power-bi-issues)
  - [Dashboard Numbers Don't Match a Fresh Pipeline Run](#dashboard-numbers-dont-match-a-fresh-pipeline-run)
- [General Debugging Workflow](#general-debugging-workflow)
- [Summary](#summary)

---

## Overview

This guide documents concrete, verifiable failure modes of the Restaurant POS ELT Pipeline, based directly on the exception types raised in the source code, the diagnostic scripts already present under `tests/`, and the architectural behaviors documented in [Assumptions and Limitations](assumptions_and_limitations.md).

## Purpose

Rather than generic advice, each entry below traces back to a specific line of behavior in this repository: the exact exception class, the module that raises it, and the fix that follows from how that module is actually implemented.

## How to Read This Guide

Each issue includes:

- **Symptom** — what you will see (an exception, a log line, or an unexpected output).
- **Where it comes from** — the exact module/function responsible.
- **Resolution** — the concrete fix or diagnostic step.

---

## Setup and Environment Issues

### `ModuleNotFoundError: No module named 'duckdb'`

**Symptom:** `python main.py` runs successfully through Bronze, Silver, and Gold, printing `Starting Gold Layer...`, then fails once it reaches `run_warehouse_pipeline_stage()`.

**Where it comes from:** `src/warehouse/writer.py` and `src/reporting/publisher.py` both `import duckdb` directly. `requirements.txt` does not include `duckdb` — it is a `pip freeze` of a Jupyter development environment that happens to omit it (see [Assumptions and Limitations, Item 11](assumptions_and_limitations.md#11-requirementstxt-is-a-development-environment-freeze-not-a-pinned-dependency-list)).

**Resolution:** install it explicitly:

```bash
pip install duckdb
```

Then re-run `python main.py`. Longer term, add a pinned `duckdb==<version>` line to `requirements.txt`.

### `ModuleNotFoundError` for `openpyxl`, `pandas`, or `pyarrow` Despite Installing Requirements

**Symptom:** import errors for packages that *are* listed in `requirements.txt`.

**Where it comes from:** this typically indicates the wrong Python environment is active. The repository ships a `.venv/` directory built for a specific Python version (`python3.14`, per the interpreter symlinks under `.venv/bin/`).

**Resolution:** confirm the correct virtual environment is activated (`source .venv/bin/activate` on macOS/Linux) or create a fresh one and reinstall:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install duckdb
```

### `pytest` Reports "no tests ran" or "collected 0 items"

**Symptom:** running `pytest` from the project root reports zero tests executed, even though `tests/test_gold.py` and `tests/test_business_silver.py` exist.

**Where it comes from:** neither file defines any `test_`-prefixed function; both define a `main()` function invoked only under `if __name__ == "__main__":`. Per their own docstrings, `tests/test_gold.py` is explicitly *"NOT a pytest unit test"* — it is a manually-run integration validation script.

**Resolution:** run these scripts directly instead of through pytest:

```bash
python tests/test_gold.py
python tests/test_business_silver.py
python tests/debug_gold_lookup_failures.py
python tests/debug_order_items_merge.py
```

Read their printed output for `PASS`/count information. See [Future Enhancements, Item 2](future_enhancements.md#2-turn-tests-into-an-actual-automated-suite) for converting these into real pytest assertions.

---

## Ingestion and Discovery Issues

### `RawDirectoryNotFoundError: Raw directory does not exist`

**Symptom:** raised by `discover_reports()` in `src/ingestion/discovery.py` at the very start of `run_pipeline()`.

**Resolution:** confirm you are running `python main.py` from the project root (the directory containing `main.py` itself), since `RAW_DIR = Path("data") / "raw"` is a relative path. Confirm `data/raw/` exists and contains at least one report subfolder.

### `NoSupportedFilesFoundError: No supported .csv or .xlsx files found`

**Symptom:** raised by the same module when `data/raw/` exists but scanning finds nothing usable.

**Where it comes from:** `discover_reports()` only accepts `.csv` and `.xlsx` extensions (`SUPPORTED_EXTENSIONS`), skips hidden files (dotfiles, per `_is_hidden()`), and skips anything under a directory named `__MACOSX`.

**Resolution:** check for:
- Files with a different extension (`.xls`, `.xlsm`, `.tsv`) — these are not read by `src/ingestion/loader.py`'s `READER_DISPATCH` and would need a new reader registered.
- A macOS Zip export that placed everything under `__MACOSX/` alongside the real folder — re-extract the archive and confirm the real `data/raw/<report_name>/` folders are present at the top level.

### A File Is Ingested Under the Wrong Report Name

**Symptom:** a file shows up grouped under an unexpected report name in the Bronze layer (e.g. `data/bronze/<wrong_name>/`).

**Where it comes from:** `discover_reports()` groups files strictly by **immediate parent folder name** (`path.parent.name`), with no content-based classification. There is no validation that a file's actual columns match the report type implied by its folder.

**Resolution:** verify the file is physically located in the correct subfolder under `data/raw/` (e.g. `data/raw/order_summary/`, `data/raw/order_summary_item/`, `data/raw/kot_process_time/`) before running the pipeline.

### `HeaderRowNotFoundError` When Reading a KOT Excel File

**Symptom:** raised by `read_excel_file()` in `src/ingestion/excel_reader.py` for a `.xlsx` file under `kot_process_time/`.

**Where it comes from:** `_detect_header_row()` scores the first `MAX_HEADER_SCAN_ROWS` (30) rows against `BUSINESS_COLUMN_KEYWORDS` (`kot`, `item name`, `quantity`, `process time`, `brand`, etc.), requiring at least two populated cells and at least one matching keyword. If no row scores above zero within the first 30 rows, this error is raised.

**Resolution:**
1. Open the offending file and manually inspect whether the true header row appears after row 30 — if so, the file's metadata block is unusually long and `MAX_HEADER_SCAN_ROWS` may need to be increased.
2. Check whether the header uses entirely different terminology than the keywords in `BUSINESS_COLUMN_KEYWORDS` — if the POS export format has changed, add the new terminology to that tuple.
3. Confirm the sheet being read (`sheet_name=0` by default) is actually the sheet containing the data table, not a cover/summary sheet.

### `CSVReadError` on a Specific CSV File

**Symptom:** raised by `read_csv_file()` in `src/ingestion/csv_reader.py`.

**Where it comes from:** this wraps four distinct underlying causes, each logged separately before being re-raised as `CSVReadError`:
- `pd.errors.EmptyDataError` — the file has no columns/is empty.
- `pd.errors.ParserError` — malformed CSV structure (e.g. inconsistent column counts).
- A `UnicodeDecodeError` that also fails under the `utf-8-sig` fallback — the file is in a different encoding entirely.
- A generic `OSError`.

**Resolution:** check the application log (see `logging.basicConfig(level=logging.WARNING, ...)` in `main.py`) for the specific underlying exception message, which is included in the wrapped `CSVReadError`. Re-export the source file as UTF-8 CSV if an encoding issue is suspected.

---

## Bronze Layer / Idempotency Issues

### "Skipping already processed file" for a File You Expected to Reprocess

**Symptom:** `main.py` prints `Skipping already processed file: <name>` for a file you believe should be reprocessed.

**Where it comes from:** `should_process()` in `src/storage/hash_manager.py` skips a file only when **both** its filename and SHA256 content hash match an entry already recorded in `data/metadata/processed_files.json`.

**Resolution:**
- If you intended to force a full reprocess, delete or edit the corresponding entry in `data/metadata/processed_files.json`, or delete the whole file to reset all tracking (this will cause every raw file to be reprocessed on the next run).
- If the underlying source data changed but the filename stayed the same, verify the file's content actually changed — an export tool that regenerates a file with identical content (same hash) will correctly be treated as unchanged.

### `processed_files.json` Looks Corrupted or `json.JSONDecodeError` Is Raised

**Symptom:** raised by `load_processed_metadata()` in `src/storage/hash_manager.py`.

**Resolution:** the file is plain JSON at `data/metadata/processed_files.json`; open it and check for a truncated write (e.g. from a killed process mid-run) or manual edits that broke JSON syntax. Restoring from version control or deleting the file (forcing a full Bronze reprocess) both resolve this.

### `FileExistsError` When Writing a Bronze Parquet File

**Symptom:** raised by `write_parquet()` in `src/storage/parquet_writer.py`.

**Where it comes from:** this only occurs if `write_parquet()` is called with `overwrite=False` against an existing destination file. Note that `main.py` always calls it with `overwrite=True`, so this error should not occur during a normal `python main.py` run — it typically indicates custom code or a script calling `write_parquet()` directly with the default `overwrite=False`.

**Resolution:** pass `overwrite=True` explicitly if replacing the file is intended, or delete the existing Bronze Parquet file first.

---

## Silver and Business Silver Issues

### "No new Bronze datasets detected" — Silver/Gold/Warehouse All Skipped

**Symptom:** `main.py` prints:
```
No new Bronze datasets detected.
Skipping Silver Layer.
Skipping Gold Layer.
Skipping Warehouse Layer.
```

**Where it comes from:** `main.py` only proceeds past Bronze if `written_files` (the list of newly-written Bronze Parquet files **this run**) is non-empty. If every discovered raw file was already recorded in `processed_files.json` with a matching hash, `written_files` is empty.

**Resolution:** this is expected behavior when re-running the pipeline with no new or changed source files. If you expected new data to be picked up, confirm the new files were actually placed under `data/raw/<report_name>/` before running, and check whether they were skipped per the previous section.

### `brand` / `platform` Columns Are Missing or All `None`

**Symptom:** the enriched Order Summary Silver dataset has a `brand`/`platform` column, but many or all values are `None`.

**Where it comes from:** `parse_sub_order_type()` in `src/transformation/business/parser.py` only recognizes two shapes: `"<brand> - <platform>"` or a bare channel name with no separator. Any other delimiter (e.g. `"|"`, `"/"`) or an entirely different `sub_order_type` format will not parse as expected, typically leaving `platform` populated (the whole string) and `brand` as `None`.

**Resolution:** inspect the raw `sub_order_type` values in the Bronze/Silver Order Summary data for the affected rows and compare them against the two supported shapes documented in `parser.py`'s docstring. If the source system introduced a new format, `parse_sub_order_type()` will need a corresponding update.

### "Unknown brand" / "Unknown platform" Appears in Validation Output

**Symptom:** `validate_business_attributes()` in `src/transformation/business/quality.py` reports `"Unknown brand"` or `"Unknown platform"` for specific rows.

**Where it comes from:** `_KNOWN_BRANDS` and `_KNOWN_PLATFORMS` in `quality.py` are hardcoded allowlists (currently `{"Thepla House By Tejals", "Homely & Healthy"}` and `{"Swiggy", "Zomato", "Delivery", "Pick Up", "Dine In"}` respectively) maintained independently of the standardization dictionaries in `brand.py`/`platform.py`.

**Resolution:** if a legitimately new brand or platform was onboarded (and correctly added to `_CANONICAL_BRANDS`/`_CANONICAL_PLATFORMS` in `brand.py`/`platform.py`), remember to also add it to `_KNOWN_BRANDS`/`_KNOWN_PLATFORMS` in `quality.py` — these two lookup sets are not automatically kept in sync. Note this validation is advisory only (see [Assumptions and Limitations, Item 4](assumptions_and_limitations.md#4-business-validation-is-advisory-not-enforced)) and will not block the pipeline.

### A Numeric-Looking ID Column Loses Its Leading Zeros

**Symptom:** an identifier column (e.g. a ticket or reference number that happens to be all-digit) appears as an integer without leading zeros after Silver processing.

**Where it comes from:** `convert_datatypes()` in `src/transformation/datatype_converter.py` casts any column whose non-null values are 100% numeric-parseable to `Int64`/`Float64`, regardless of the column's semantic meaning as an identifier (see [Assumptions and Limitations, Item 5](assumptions_and_limitations.md#5-datatype-inference-is-heuristic-and-column-name-agnostic)).

**Resolution:** there is currently no column-name-based override to exempt specific columns from numeric inference. If this becomes an operational problem, the fix belongs in `_convert_column()` — introducing an explicit exemption list (or, per [Future Enhancements, Item 14](future_enhancements.md#14-schema-contracts-for-source-reports), a declared schema) rather than working around it downstream.

---

## Gold Layer Issues

### Row Counts in a Fact Table Are Lower Than Expected in Power BI

**Symptom:** a Power BI visual built on a `vw_*` view shows fewer orders/items/kitchen events than the source data appears to contain, even though the corresponding `fact_*` DuckDB table has the expected row count.

**Where it comes from:** every reporting view in `src/warehouse/views.py` uses `INNER JOIN` between `fact_*` and `dim_*` tables. Any fact row whose surrogate key lookup failed (a `NULL` `date_key`, `brand_key`, `item_key`, etc., attached by the `how="left"` merges in `src/gold/lookup.py`) is present in the table but excluded from the view. See [Assumptions and Limitations, Item 3](assumptions_and_limitations.md#3-dimension-lookup-failures-are-silently-dropped-by-reporting-views).

**Resolution:** compare `SELECT COUNT(*) FROM fact_orders` against `SELECT COUNT(*) FROM vw_daily_sales` (summed) directly in DuckDB, or use the diagnostic script below to identify exactly which key and which business values are failing.

### Diagnosing Which Dimension Is Causing Dropped Rows

**Symptom:** you've confirmed a row-count mismatch per the previous entry and need to know *why* specific rows failed to match a dimension.

**Resolution:** run the diagnostic script already provided for this exact purpose:

```bash
python tests/debug_gold_lookup_failures.py
```

This script (see its module docstring: *"investigate WHY certain surrogate key lookups produced nulls"*) loads the Silver datasets, rebuilds the Gold layer in memory, and for each fact table prints, per surrogate key column: the null count, the null percentage, a distinct-value breakdown of the offending business columns (e.g. which `brand`, `platform`, or `item_name` values are failing to match), and a sample of the affected rows. It performs no writes and is safe to run at any time. `tests/debug_order_items_merge.py` provides a similar diagnostic focused specifically on the Order Items ↔ Order Summary join.

### Gold Output Only Reflects the Latest Run, Not Full History

**Symptom:** after running the pipeline twice — once with historical files, once with a new month's files — the Gold Parquet files and DuckDB tables contain only the newest batch, and previously visible historical rows are gone.

**Where it comes from:** this is expected given the current implementation, not a bug to patch around. `main.py` passes only the current run's newly-written Bronze files into the Silver stage, and both `src/gold/writer.py` and `src/warehouse/writer.py` perform a full overwrite of whatever they are given. See [Assumptions and Limitations, Item 1](assumptions_and_limitations.md#1-gold-and-warehouse-layers-are-full-rebuilds-not-incremental-merges).

**Resolution (operational workaround today):** to rebuild Gold/Warehouse with full history, ensure every historical raw file is present under `data/raw/` and either clear `data/metadata/processed_files.json` (forcing all files to be treated as new) or delete `data/bronze/`, `data/silver/`, `data/gold/`, and `data/metadata/` and re-run the pipeline from a clean state so all files are reprocessed together in one run. A structural fix is tracked in [Future Enhancements, Item 5](future_enhancements.md#5-true-incremental-gold-and-warehouse-loading).

---

## Warehouse Layer Issues

### `duckdb.IOException` — Database File Is Locked

**Symptom:** an I/O or lock-related exception when `_create_connection()` in `src/warehouse/writer.py` attempts to open `data/warehouse/restaurant_pos.duckdb`.

**Where it comes from:** DuckDB uses file-level locking; a second process (commonly Power BI Desktop or a DuckDB CLI session) holding an open connection to the same `.duckdb` file will block a concurrent write connection from the pipeline.

**Resolution:** close any other application or notebook session connected to `restaurant_pos.duckdb` (including Power BI, if it has an open DuckDB connector session) before re-running `python main.py`.

### A Table Appears Empty or Missing After a Run

**Symptom:** a `dim_*` or `fact_*` table is missing or has zero rows after a pipeline run that otherwise reported success.

**Where it comes from:** `write_warehouse()` wraps table materialization in an explicit transaction (`connection.begin()` / `connection.commit()` / `connection.rollback()` on exception). If an exception occurred partway through `_materialize_tables()`, the entire transaction is rolled back — so a genuinely empty or missing table after an apparently successful run more likely indicates the corresponding Gold DataFrame itself was empty (check the printed `Gold Layer` summary line from `main.py` for `0 files written` or a `0` dimension/fact count) rather than a partial warehouse write.

**Resolution:** re-run with the diagnostic scripts in the Gold Layer section above to confirm the Gold DataFrames themselves contain the expected row counts before investigating the warehouse write step further.

---

## Reporting Layer Issues

### `duckdb.Error` When Publishing a View or Dimension

**Symptom:** raised by `fetch_dataset()` in `src/reporting/publisher.py` while running `SELECT * FROM <dataset_name>`.

**Where it comes from:** this occurs if a view or table listed in `REPORTING_VIEWS` / `REPORTING_DIMENSIONS` (`src/reporting/reporting_config.py`) does not actually exist in the DuckDB database at the time the Reporting Layer runs — for example, if the Warehouse stage failed or was skipped (see the "No new Bronze datasets detected" entry above) but the Reporting Layer was invoked independently.

**Resolution:** confirm the Warehouse stage completed successfully and created all expected `dim_*`/`fact_*` tables and `vw_*` views before running the Reporting Layer in isolation. Run `python main.py` end-to-end rather than invoking `run_reporting_pipeline()` on its own against a stale or partially-built database.

### CSV Files in `data/reporting/` Are Stale

**Symptom:** the CSV files under `data/reporting/views/` and `data/reporting/dimensions/` don't reflect the latest data.

**Where it comes from:** `export_dataframe_to_csv()` in `src/reporting/exporter.py` overwrites each CSV unconditionally every time `run_reporting_pipeline()` executes — so staleness indicates the Reporting stage did not actually run in the most recent pipeline execution, most likely because the run short-circuited earlier (see the "No new Bronze datasets detected" entry).

**Resolution:** confirm the pipeline log shows `Starting Reporting Layer...` and a final `Reporting Layer` summary line in the `main.py` output for the run in question.

---

## Power BI Issues

### Dashboard Numbers Don't Match a Fresh Pipeline Run

**Symptom:** `powerbi/dashboards/Restaurant_POS_Analytics.pbix` shows numbers that don't reflect the latest pipeline run.

**Where it comes from:** by design, Power BI in this project reads only the static CSV exports under `data/reporting/` (see the architectural note in `src/warehouse/views.py`: *"Power BI consumes only these SQL Views — it never queries the Warehouse tables or Gold directly"*, exposed to Power BI exclusively through the CSV snapshots). There is no live connection and no scheduled refresh configured in this repository.

**Resolution:** after confirming the Reporting Layer produced fresh CSVs (previous section), manually refresh the data source in Power BI Desktop so it re-reads the updated CSV files.

---

## General Debugging Workflow

When a pipeline run produces unexpected results and the specific symptom isn't listed above, the following sequence follows the pipeline's own architecture and tends to isolate the problem fastest:

1. Re-run `python main.py` and read the full console output — every stage (Bronze, Silver, Gold, Warehouse, Reporting) prints its own summary block, so the first stage that doesn't print its expected summary is where the problem originates.
2. For Silver-stage concerns, check the per-dataset block printed by `src/silver/runner.py`, which includes `Rows Before`, `Rows After`, `Duplicates Removed`, and `Validation Errors` for every file processed.
3. For Gold-stage row-count concerns, run `python tests/debug_gold_lookup_failures.py` and `python tests/debug_order_items_merge.py` — both are safe, read-only diagnostic scripts built specifically for this purpose.
4. For Warehouse/Reporting concerns, connect directly to `data/warehouse/restaurant_pos.duckdb` with the DuckDB CLI or Python and inspect table/view row counts directly (`SELECT COUNT(*) FROM fact_orders;`) before assuming the issue is downstream in Power BI.
5. Cross-reference any unexpected behavior against [Assumptions and Limitations](assumptions_and_limitations.md) — several behaviors that look like bugs (full Gold rebuilds, silently dropped lookup failures, advisory-only validation) are documented, intentional characteristics of the current implementation rather than defects.

## Summary

Most operational issues in this pipeline trace back to one of four root causes: an environment/dependency mismatch (missing `duckdb`), a Bronze-layer idempotency decision (hash-based skip logic), a Silver-layer parsing assumption about `sub_order_type` format, or the full-rebuild nature of the Gold and Warehouse layers combined with `INNER JOIN`-based reporting views. The repository already includes purpose-built diagnostic tooling (`tests/debug_gold_lookup_failures.py`, `tests/debug_order_items_merge.py`) for the most subtle of these — silent dimension lookup failures — and those scripts should be the first stop for any row-count discrepancy between the Gold layer and Power BI.

"""
Silver Layer -- Transformation package.

Modules:
    column_standardizer -- normalize column names
    null_handler         -- normalize / detect null-like values
    datatype_converter    -- infer and cast column dtypes
    business_validator     -- read-only business rule checks
    duplicate_handler       -- row-level de-duplication
    pipeline                 -- orchestrates the above into run_silver_pipeline()
"""

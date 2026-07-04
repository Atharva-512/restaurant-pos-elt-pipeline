import pandas as pd

from src.gold.facts.order_items import _enrich_order_context


orders = pd.concat(
    [
        pd.read_parquet("data/silver/order_summary/Order_Summary_Report_2026-05.parquet"),
        pd.read_parquet("data/silver/order_summary/Order_Summary_Report_2026-06.parquet"),
    ],
    ignore_index=True,
)

items = pd.concat(
    [
        pd.read_parquet("data/silver/order_summary_item/Order_Summary_Item_Report_2026-05.parquet"),
        pd.read_parquet("data/silver/order_summary_item/Order_Summary_Item_Report_2026-06.parquet"),
    ],
    ignore_index=True,
)

merged = _enrich_order_context(items, orders)

failed = merged[
    merged["business_date"].isna()
]

print("=" * 70)
print("FAILED MERGES")
print("=" * 70)

print("Rows:", len(failed))
print()

print(failed[
    [
        "restaurant_name",
        "invoice_no",
        "item_name",
    ]
].head(50).to_string(index=False))
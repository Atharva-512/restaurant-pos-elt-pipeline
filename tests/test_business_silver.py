from pathlib import Path

import pandas as pd

from src.transformation.business.enricher import enrich_business_attributes


def main() -> None:
    file_path = Path(
        "data/silver/order_summary/Order_Summary_Report_2026-05.parquet"
    )

    df = pd.read_parquet(file_path)

    print(f"Rows Loaded: {len(df)}")
    print()

    enriched_df = enrich_business_attributes(
        df,
        timestamp_column="date",
        sub_order_type_column="sub_order_type",
    )

    print("New Columns:")
    print(
        [
            "brand",
            "platform",
            "business_date",
            "weekday",
            "month",
            "month_name",
            "quarter",
            "year",
            "daypart",
            "business_validation_errors",
        ]
    )

    print()

    print(
        enriched_df[
            [
                "sub_order_type",
                "brand",
                "platform",
                "business_date",
                "daypart",
                "business_validation_errors",
            ]
        ].sample(20, random_state=42)
    )


if __name__ == "__main__":
    main()
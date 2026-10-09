import pandas as pd

from extract_paginated import extract_all_products
from watermark import get_watermark


def filter_incremental_records(data, watermark):
    """
    Filter extracted records using the last
    successful source watermark.

    If no previous watermark exists, all records
    are returned for the initial load.
    """

    df = data.copy()

    # Ensure source timestamp is a proper UTC datetime
    df["source_updated_at"] = pd.to_datetime(
        df["source_updated_at"],
        utc=True,
        errors="coerce"
    )

    # --------------------------------------------------
    # Initial load
    # --------------------------------------------------

    if watermark is None:

        print(
            "\nNo previous watermark found."
            "\nInitial load: all extracted records "
            "will be processed."
        )

        return df

    # --------------------------------------------------
    # Incremental load
    # --------------------------------------------------

    watermark = pd.to_datetime(
        watermark,
        utc=True
    )

    incremental_data = df[
        df["source_updated_at"] > watermark
    ].copy()

    print(
        f"\nPrevious watermark: {watermark}"
    )

    print(
        f"Incremental records identified: "
        f"{len(incremental_data)}"
    )

    return incremental_data


if __name__ == "__main__":

    # 1. Read previous successful watermark
    watermark = get_watermark()

    print("\nCurrent stored watermark:")
    print(watermark)

    # 2. Extract current source data
    extracted_data = extract_all_products()

    print(
        f"\nTotal records extracted: "
        f"{len(extracted_data)}"
    )

    # 3. Apply watermark filtering
    incremental_data = filter_incremental_records(
        extracted_data,
        watermark
    )

    print(
        f"\nRecords selected for processing: "
        f"{len(incremental_data)}"
    )

    # 4. Display timestamp range
    if not incremental_data.empty:

        print("\nSelected source timestamp range:")

        print(
            "Minimum:",
            incremental_data["source_updated_at"].min()
        )

        print(
            "Maximum:",
            incremental_data["source_updated_at"].max()
        )

        print("\nFirst 5 selected records:")

        print(
            incremental_data[
                [
                    "id",
                    "title",
                    "source_updated_at"
                ]
            ].head()
        )

    else:

        print(
            "\nNo new or updated records "
            "were found."
        )
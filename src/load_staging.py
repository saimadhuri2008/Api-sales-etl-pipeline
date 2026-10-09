from sqlalchemy import text

from db_config import engine
from extract_paginated import extract_all_products
from transform import transform_products


def load_to_staging(valid_data):
    """
    Load validated product data into the PostgreSQL
    staging table.

    The staging table is refreshed on every full load.
    """

    print(
        f"\nPreparing to load {len(valid_data)} "
        f"product(s) into staging..."
    )

    # Work with a copy before changing column names.
    staging_data = valid_data.copy()

    # Match Pandas/API column names to PostgreSQL naming.
    staging_data = staging_data.rename(
        columns={
            "discountPercentage": "discount_percentage"
        }
    )

    # Clear the previous staging dataset.
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE TABLE stg_products;")
        )

    print("Staging table cleared.")

    # Load the validated records.
    staging_data.to_sql(
        name="stg_products",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=100
    )

    print(
        f"Staging load completed: "
        f"{len(staging_data)} product(s) loaded."
    )

    return len(staging_data)


if __name__ == "__main__":

    # -----------------------------------------
    # Extract
    # -----------------------------------------

    extracted_data = extract_all_products()

    # -----------------------------------------
    # Transform
    # -----------------------------------------

    valid_data, rejected_data = transform_products(
        extracted_data
    )

    # -----------------------------------------
    # Load
    # -----------------------------------------

    loaded_count = load_to_staging(
        valid_data
    )

    print("\nETL staging summary:")
    print(f"Extracted: {len(extracted_data)}")
    print(f"Valid:     {len(valid_data)}")
    print(f"Rejected:  {len(rejected_data)}")
    print(f"Loaded:    {loaded_count}")
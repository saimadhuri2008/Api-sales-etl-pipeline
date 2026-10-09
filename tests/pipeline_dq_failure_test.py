from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import text


# --------------------------------------------------
# PROJECT PATH SETUP
# --------------------------------------------------

project_root = Path(__file__).resolve().parent.parent
src_dir = project_root / "src"

if str(src_dir) not in sys.path:
    sys.path.insert(
        0,
        str(src_dir)
    )


# --------------------------------------------------
# PROJECT IMPORTS
# --------------------------------------------------

from db_config import engine
from extract_paginated import extract_all_products
from incremental import filter_incremental_records
from transform import transform_products
from load_staging import load_to_staging
from load_target import load_target
from watermark import get_watermark
from data_quality import run_data_quality_checks


# --------------------------------------------------
# DQ FAILURE TEST
# --------------------------------------------------

def run_dq_failure_test():
    """
    Prove that a post-load data-quality failure
    prevents the ETL watermark from advancing.

    This is a controlled integration test.
    """

    print(
        "\nTesting DQ failure and "
        "watermark protection...\n"
    )

    # --------------------------------------------------
    # 1. CAPTURE WATERMARK BEFORE TEST
    # --------------------------------------------------

    watermark_before = get_watermark()

    if watermark_before is None:

        raise RuntimeError(
            "The failure test requires an existing "
            "watermark from a previous successful run."
        )

    print(
        "Watermark before test:"
    )

    print(
        watermark_before
    )

    # --------------------------------------------------
    # 2. EXTRACT CURRENT CLEAN SOURCE DATA
    # --------------------------------------------------

    extracted_data = extract_all_products()

    clean_source_data = (
        extracted_data.copy()
    )

    # --------------------------------------------------
    # 3. SIMULATE ONE NEWER SOURCE RECORD
    # --------------------------------------------------

    test_data = extracted_data.copy()

    simulated_timestamp = (
        pd.to_datetime(
            watermark_before,
            utc=True
        )
        + pd.Timedelta(
            minutes=5
        )
    )

    test_data.loc[
        test_data["id"] == 1,
        "source_updated_at"
    ] = simulated_timestamp

    print(
        "\nSimulated Product 1 "
        "source timestamp:"
    )

    print(
        test_data.loc[
            test_data["id"] == 1,
            [
                "id",
                "title",
                "source_updated_at"
            ]
        ]
    )

    # --------------------------------------------------
    # 4. APPLY REAL INCREMENTAL FILTER
    # --------------------------------------------------

    incremental_data = filter_incremental_records(
        test_data,
        watermark_before
    )

    print(
        f"\nIncremental records selected: "
        f"{len(incremental_data)}"
    )

    if len(incremental_data) != 1:

        raise RuntimeError(
            "Failure test expected exactly "
            "1 incremental record."
        )

    # --------------------------------------------------
    # 5. TRANSFORM INCREMENTAL RECORD
    # --------------------------------------------------

    valid_data, rejected_data = transform_products(
        incremental_data
    )

    print(
        f"\nValid incremental records: "
        f"{len(valid_data)}"
    )

    print(
        f"Rejected incremental records: "
        f"{len(rejected_data)}"
    )

    if not rejected_data.empty:

        raise RuntimeError(
            "Unexpected transformation rejection "
            "during failure test."
        )

    # --------------------------------------------------
    # 6. LOAD INCREMENTAL RECORD TO STAGING
    # --------------------------------------------------

    loaded_count = load_to_staging(
        valid_data
    )

    print(
        f"\nIncremental records staged: "
        f"{loaded_count}"
    )

    # --------------------------------------------------
    # 7. RUN NORMAL TARGET LOAD
    # --------------------------------------------------

    affected_rows = load_target()

    print(
        f"Target rows affected before DQ test: "
        f"{affected_rows}"
    )

    # --------------------------------------------------
    # 8. DELIBERATELY CORRUPT STAGING
    # --------------------------------------------------

    print(
        "\nTEST: Introducing invalid "
        "staging price..."
    )

    with engine.begin() as connection:

        connection.execute(
            text(
                """
                UPDATE stg_products
                SET price = -10
                WHERE id = 1
                """
            )
        )

    # --------------------------------------------------
    # 9. VERIFY CONTROLLED CORRUPTION
    # --------------------------------------------------

    with engine.connect() as connection:

        corrupted_price = (
            connection.execute(
                text(
                    """
                    SELECT price
                    FROM stg_products
                    WHERE id = 1
                    """
                )
            )
            .scalar_one()
        )

    print(
        f"Controlled staging price: "
        f"{corrupted_price}"
    )

    # --------------------------------------------------
    # 10. RUN POST-LOAD DATA QUALITY
    # --------------------------------------------------

    quality_passed = run_data_quality_checks(
        expected_staging_count=len(
            valid_data
        )
    )

    expected_failure_detected = (
        quality_passed is False
    )

    if expected_failure_detected:

        print(
            "\nExpected DQ failure detected."
        )

        print(
            "Watermark update intentionally skipped."
        )

    else:

        raise RuntimeError(
            "TEST FAILED: Data-quality validation "
            "did not detect the corrupted staging row."
        )

    # --------------------------------------------------
    # 11. VERIFY WATERMARK DID NOT ADVANCE
    # --------------------------------------------------

    watermark_after = get_watermark()

    print(
        "\nWatermark after DQ failure:"
    )

    print(
        watermark_after
    )

    watermark_protected = (
        watermark_after == watermark_before
    )

    if not watermark_protected:

        raise RuntimeError(
            "TEST FAILED: Watermark changed despite "
            "the data-quality failure."
        )

    # --------------------------------------------------
    # 12. DISPLAY TEST RESULT
    # --------------------------------------------------

    print(
        "\nTEST PASSED"
    )

    print(
        "1. Newer source record was detected."
    )

    print(
        "2. Controlled staging corruption "
        "was detected by DQ."
    )

    print(
        "3. Watermark advancement was skipped."
    )

    print(
        "4. Watermark remained unchanged."
    )

    return clean_source_data


# --------------------------------------------------
# RESTORE STAGING
# --------------------------------------------------

def restore_staging(clean_source_data):
    """
    Restore staging from the clean API snapshot
    after the controlled failure test.
    """

    print(
        "\nRestoring clean staging data..."
    )

    valid_data, rejected_data = transform_products(
        clean_source_data
    )

    if not rejected_data.empty:

        raise RuntimeError(
            "Could not restore staging because "
            "clean source transformation "
            "rejected records."
        )

    loaded_count = load_to_staging(
        valid_data
    )

    print(
        f"Clean staging data restored: "
        f"{loaded_count} record(s)."
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    clean_source_data = None

    try:

        clean_source_data = (
            run_dq_failure_test()
        )

    finally:

        if clean_source_data is not None:

            restore_staging(
                clean_source_data
            )
from pathlib import Path
import sys


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

from extract_paginated import extract_all_products
from transform import transform_products


# --------------------------------------------------
# TRANSFORMATION TEST
# --------------------------------------------------

def run_transform_test():
    """
    Test transformation and rejection handling
    using deliberately invalid source records.
    """

    print(
        "\nTesting transformation validation...\n"
    )

    # --------------------------------------------------
    # 1. GET CLEAN API DATA
    # --------------------------------------------------

    data = extract_all_products()

    test_data = data.copy()

    # --------------------------------------------------
    # 2. INJECT DELIBERATELY INVALID RECORDS
    # --------------------------------------------------

    # Product 1:
    # invalid negative price + invalid rating
    test_data.loc[
        0,
        "price"
    ] = -10

    test_data.loc[
        0,
        "rating"
    ] = 8

    # Product 2:
    # invalid rating
    test_data.loc[
        1,
        "rating"
    ] = 8

    # Product 3:
    # missing required title
    test_data.loc[
        2,
        "title"
    ] = None

    # Product 4:
    # invalid negative stock
    test_data.loc[
        3,
        "stock"
    ] = -5

    # Product 5:
    # duplicate SKU
    test_data.loc[
        4,
        "sku"
    ] = test_data.loc[
        5,
        "sku"
    ]

    # --------------------------------------------------
    # 3. RUN TRANSFORMATION
    # --------------------------------------------------

    valid_data, rejected_data = transform_products(
        test_data
    )

    # --------------------------------------------------
    # 4. DISPLAY SUMMARY
    # --------------------------------------------------

    print(
        "\nTest results:"
    )

    print(
        f"Valid products: "
        f"{len(valid_data)}"
    )

    print(
        f"Rejected products: "
        f"{len(rejected_data)}"
    )

    # --------------------------------------------------
    # 5. DISPLAY REJECTED RECORDS
    # --------------------------------------------------

    print(
        "\nRejected records:"
    )

    if rejected_data.empty:

        print(
            "No rejected records."
        )

    else:

        print(
            rejected_data[
                [
                    "id",
                    "title",
                    "price",
                    "rating",
                    "stock",
                    "sku",
                    "rejection_reason"
                ]
            ]
        )

    # --------------------------------------------------
    # 6. DISPLAY REJECTION SUMMARY
    # --------------------------------------------------

    if not rejected_data.empty:

        print(
            "\nRejection summary:"
        )

        rejection_summary = (
            rejected_data[
                "rejection_reason"
            ]
            .str.split("; ")
            .explode()
            .value_counts()
        )

        print(
            rejection_summary
        )

    # --------------------------------------------------
    # 7. VALIDATE EXPECTED RESULT
    # --------------------------------------------------

    expected_rejected_records = 5

    if len(rejected_data) != expected_rejected_records:

        raise RuntimeError(
            "TEST FAILED: Expected "
            f"{expected_rejected_records} rejected "
            f"record(s), but found "
            f"{len(rejected_data)}."
        )

    print(
        "\nTEST PASSED: "
        "Transformation validation correctly "
        "identified the injected bad records."
    )

    return 0


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    raise SystemExit(
        run_transform_test()
    )
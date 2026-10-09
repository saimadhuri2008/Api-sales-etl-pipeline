from pathlib import Path
import sys

import pandas as pd


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
from incremental import filter_incremental_records
from watermark import get_watermark


# --------------------------------------------------
# INCREMENTAL TEST
# --------------------------------------------------

def run_incremental_test():
    """
    Test watermark-based incremental detection
    by simulating one newer source record.
    """

    print(
        "\nTesting incremental change detection...\n"
    )

    # --------------------------------------------------
    # 1. READ CURRENT WATERMARK
    # --------------------------------------------------

    watermark = get_watermark()

    if watermark is None:

        raise RuntimeError(
            "Incremental test requires an existing "
            "watermark from a previous successful run."
        )

    print(
        "Current watermark:"
    )

    print(
        watermark
    )

    # --------------------------------------------------
    # 2. EXTRACT CURRENT SOURCE DATA
    # --------------------------------------------------

    data = extract_all_products()

    test_data = data.copy()

    # --------------------------------------------------
    # 3. SIMULATE ONE SOURCE RECORD BEING UPDATED
    # --------------------------------------------------

    new_timestamp = (
        pd.to_datetime(
            watermark,
            utc=True
        )
        + pd.Timedelta(
            minutes=5
        )
    )

    test_data.loc[
        test_data["id"] == 1,
        "source_updated_at"
    ] = new_timestamp

    print(
        "\nSimulated source change:"
    )

    print(
        test_data.loc[
            test_data["id"] == 1,
            [
                "id",
                "title",
                "stock",
                "source_updated_at"
            ]
        ]
    )

    # --------------------------------------------------
    # 4. APPLY INCREMENTAL FILTER
    # --------------------------------------------------

    incremental_data = filter_incremental_records(
        test_data,
        watermark
    )

    # --------------------------------------------------
    # 5. DISPLAY TEST RESULTS
    # --------------------------------------------------

    print(
        "\nIncremental test results:"
    )

    print(
        f"Total source records: "
        f"{len(test_data)}"
    )

    print(
        f"Records selected: "
        f"{len(incremental_data)}"
    )

    print(
        "\nSelected records:"
    )

    if incremental_data.empty:

        print(
            "No records selected."
        )

    else:

        print(
            incremental_data[
                [
                    "id",
                    "title",
                    "stock",
                    "source_updated_at"
                ]
            ]
        )

    # --------------------------------------------------
    # 6. VALIDATE EXPECTED RESULT
    # --------------------------------------------------

    test_passed = (
        len(incremental_data) == 1
        and incremental_data.iloc[0]["id"] == 1
    )

    if not test_passed:

        raise RuntimeError(
            "TEST FAILED: Expected exactly "
            "one changed product with id=1."
        )

    print(
        "\nTEST PASSED: "
        "Only the simulated changed record "
        "was selected."
    )

    return 0


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    raise SystemExit(
        run_incremental_test()
    )
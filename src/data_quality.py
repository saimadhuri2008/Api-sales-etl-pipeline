from sqlalchemy import text

from db_config import engine


def run_data_quality_checks(expected_staging_count=None):
    """
    Run post-load data-quality checks against
    staging and target product tables.

    Args:
        expected_staging_count:
            Number of records the current ETL run
            expected to load into staging.

            If None, the current staging row count
            is reported without reconciliation.

    Returns:
        True if all checks pass, otherwise False.
    """

    print("\nRunning data-quality checks...\n")

    results = []

    with engine.connect() as connection:

        # --------------------------------------------------
        # 1. STAGING ROW COUNT / RECONCILIATION
        # --------------------------------------------------

        staging_count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM stg_products
                """
            )
        ).scalar_one()

        if expected_staging_count is None:

            staging_pass = staging_count >= 0

            staging_message = (
                f"Staging row count - "
                f"rows={staging_count}"
            )

        else:

            staging_pass = (
                staging_count == expected_staging_count
            )

            staging_message = (
                "Staging reconciliation - "
                f"expected={expected_staging_count}, "
                f"actual={staging_count}"
            )

        results.append(
            (
                staging_pass,
                staging_message
            )
        )

        # --------------------------------------------------
        # 2. STAGING NULL CRITICAL FIELDS
        # --------------------------------------------------

        staging_null_records = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM stg_products
                WHERE id IS NULL
                   OR title IS NULL
                   OR category IS NULL
                   OR price IS NULL
                   OR stock IS NULL
                   OR sku IS NULL
                   OR source_updated_at IS NULL
                """
            )
        ).scalar_one()

        results.append(
            (
                staging_null_records == 0,
                (
                    "Staging NULL critical fields - "
                    f"null_records={staging_null_records}"
                )
            )
        )

        # --------------------------------------------------
        # 3. STAGING INVALID BUSINESS VALUES
        # --------------------------------------------------

        staging_invalid_records = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM stg_products
                WHERE price <= 0
                   OR discount_percentage < 0
                   OR discount_percentage > 100
                   OR rating < 0
                   OR rating > 5
                   OR stock < 0
                """
            )
        ).scalar_one()

        results.append(
            (
                staging_invalid_records == 0,
                (
                    "Staging invalid business values - "
                    f"invalid_records="
                    f"{staging_invalid_records}"
                )
            )
        )

        # --------------------------------------------------
        # 4. DUPLICATE TARGET PRODUCT IDs
        # --------------------------------------------------

        duplicate_ids = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT product_id
                    FROM products
                    GROUP BY product_id
                    HAVING COUNT(*) > 1
                ) AS duplicates
                """
            )
        ).scalar_one()

        results.append(
            (
                duplicate_ids == 0,
                (
                    "Duplicate target product IDs - "
                    f"duplicates={duplicate_ids}"
                )
            )
        )

        # --------------------------------------------------
        # 5. DUPLICATE TARGET SKUs
        # --------------------------------------------------

        duplicate_skus = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT sku
                    FROM products
                    GROUP BY sku
                    HAVING COUNT(*) > 1
                ) AS duplicates
                """
            )
        ).scalar_one()

        results.append(
            (
                duplicate_skus == 0,
                (
                    "Duplicate target SKUs - "
                    f"duplicates={duplicate_skus}"
                )
            )
        )

        # --------------------------------------------------
        # 6. NULL CRITICAL TARGET FIELDS
        # --------------------------------------------------

        target_null_records = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM products
                WHERE product_id IS NULL
                   OR title IS NULL
                   OR category IS NULL
                   OR price IS NULL
                   OR stock IS NULL
                   OR sku IS NULL
                """
            )
        ).scalar_one()

        results.append(
            (
                target_null_records == 0,
                (
                    "Target NULL critical fields - "
                    f"null_records={target_null_records}"
                )
            )
        )

        # --------------------------------------------------
        # 7. INVALID TARGET BUSINESS VALUES
        # --------------------------------------------------

        target_invalid_records = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM products
                WHERE price <= 0
                   OR discount_percentage < 0
                   OR discount_percentage > 100
                   OR rating < 0
                   OR rating > 5
                   OR stock < 0
                """
            )
        ).scalar_one()

        results.append(
            (
                target_invalid_records == 0,
                (
                    "Target invalid business values - "
                    f"invalid_records="
                    f"{target_invalid_records}"
                )
            )
        )

        # --------------------------------------------------
        # 8. TARGET MUST CONTAIN DATA
        # --------------------------------------------------

        target_count = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM products
                """
            )
        ).scalar_one()

        results.append(
            (
                target_count > 0,
                (
                    "Target row count - "
                    f"rows={target_count}"
                )
            )
        )

    # --------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------

    checks_passed = 0

    for passed, message in results:

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"[{status}] {message}"
        )

        if passed:
            checks_passed += 1

    total_checks = len(results)

    print(
        f"\nData quality: "
        f"{checks_passed}/{total_checks} "
        f"checks passed."
    )

    return (
        checks_passed
        == total_checks
    )


# --------------------------------------------------
# STANDALONE EXECUTION
# --------------------------------------------------

if __name__ == "__main__":

    passed = run_data_quality_checks()

    if passed:

        print(
            "\nData-quality validation PASSED."
        )

        raise SystemExit(0)

    print(
        "\nData-quality validation FAILED."
    )

    raise SystemExit(1)
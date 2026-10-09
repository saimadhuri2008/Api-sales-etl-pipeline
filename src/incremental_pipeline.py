from pathlib import Path
from datetime import datetime, timezone

import time
import pandas as pd

from extract_paginated import extract_all_products
from incremental import filter_incremental_records
from transform import transform_products
from load_staging import load_to_staging
from load_target import load_target
from watermark import get_watermark, update_watermark
from data_quality import run_data_quality_checks
from logger import get_logger


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

project_dir = Path(__file__).resolve().parent.parent

log_file = project_dir / "logs" / "pipeline_runs.csv"


# --------------------------------------------------
# LOGGER
# --------------------------------------------------

logger = get_logger()


# --------------------------------------------------
# INCREMENTAL PIPELINE
# --------------------------------------------------

def run_incremental_pipeline():
    """
    Run the product ETL pipeline using a stored
    source timestamp watermark.

    The watermark is advanced only after:
        1. extraction succeeds
        2. transformation succeeds
        3. staging load succeeds
        4. target load succeeds
        5. post-load data-quality checks pass
    """

    run_timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    start_time = time.perf_counter()

    status = "SUCCESS"

    error_message = ""

    rows_extracted = 0
    rows_selected = 0
    rows_valid = 0
    rows_rejected = 0
    rows_staged = 0
    target_affected = 0

    watermark_before = None
    watermark_after = None

    print(
        "\nStarting incremental products ETL...\n"
    )

    logger.info(
        "Incremental products ETL started."
    )

    try:

        # --------------------------------------------------
        # 1. READ CURRENT WATERMARK
        # --------------------------------------------------

        watermark_before = get_watermark()

        print(
            f"Current watermark: "
            f"{watermark_before}"
        )

        logger.info(
            "Current watermark: %s",
            watermark_before
        )

        # --------------------------------------------------
        # 2. EXTRACT CURRENT SOURCE SNAPSHOT
        # --------------------------------------------------

        extracted_data = extract_all_products()

        rows_extracted = len(
            extracted_data
        )

        print(
            f"\nExtracted records: "
            f"{rows_extracted}"
        )

        logger.info(
            "Extraction completed: %d record(s).",
            rows_extracted
        )

        # --------------------------------------------------
        # 3. FILTER INCREMENTAL RECORDS
        # --------------------------------------------------

        incremental_data = filter_incremental_records(
            extracted_data,
            watermark_before
        )

        rows_selected = len(
            incremental_data
        )

        print(
            f"Records selected for processing: "
            f"{rows_selected}"
        )

        logger.info(
            "Incremental filtering completed: "
            "%d record(s) selected.",
            rows_selected
        )

        # --------------------------------------------------
        # 4. HANDLE NO-CHANGE RUN
        # --------------------------------------------------

        if incremental_data.empty:

            print(
                "\nNo new or updated records found. "
                "Nothing to process."
            )

            watermark_after = watermark_before

            logger.info(
                "No incremental records found. "
                "Pipeline completed with no data changes."
            )

            return 0

        # Candidate watermark captured BEFORE transform.
        new_watermark = incremental_data[
            "source_updated_at"
        ].max()

        logger.info(
            "Candidate watermark identified: %s",
            new_watermark
        )

        # --------------------------------------------------
        # 5. TRANSFORM
        # --------------------------------------------------

        valid_data, rejected_data = transform_products(
            incremental_data
        )

        rows_valid = len(
            valid_data
        )

        rows_rejected = len(
            rejected_data
        )

        logger.info(
            "Transformation completed: "
            "%d valid, %d rejected.",
            rows_valid,
            rows_rejected
        )

        if not rejected_data.empty:

            raise RuntimeError(
                f"Incremental pipeline rejected "
                f"{rows_rejected} product(s). "
                "Watermark will not be advanced."
            )

        # --------------------------------------------------
        # 6. LOAD STAGING
        # --------------------------------------------------

        rows_staged = load_to_staging(
            valid_data
        )

        logger.info(
            "Staging load completed: "
            "%d record(s) loaded.",
            rows_staged
        )

        # --------------------------------------------------
        # 7. LOAD TARGET
        # --------------------------------------------------

        target_affected = load_target()

        logger.info(
            "Target load completed: "
            "%d row(s) affected.",
            target_affected
        )

        # --------------------------------------------------
        # 8. POST-LOAD DATA QUALITY
        # --------------------------------------------------

        quality_passed = run_data_quality_checks(
            expected_staging_count=rows_valid
        )

        if not quality_passed:

            raise RuntimeError(
                "Post-load data-quality validation failed. "
                "Watermark will not be advanced."
            )

        print(
            "\nPost-load data-quality validation passed."
        )

        logger.info(
            "Post-load data-quality validation passed."
        )

        # --------------------------------------------------
        # 9. ADVANCE WATERMARK
        # --------------------------------------------------

        update_watermark(
            new_watermark
        )

        watermark_after = new_watermark

        print(
            f"\nWatermark advanced to: "
            f"{watermark_after}"
        )

        logger.info(
            "Watermark advanced from %s to %s.",
            watermark_before,
            watermark_after
        )

        # --------------------------------------------------
        # 10. SUCCESS SUMMARY
        # --------------------------------------------------

        print(
            "\nIncremental ETL summary:"
        )

        print(
            f"Extracted:       "
            f"{rows_extracted}"
        )

        print(
            f"Selected:        "
            f"{rows_selected}"
        )

        print(
            f"Valid:           "
            f"{rows_valid}"
        )

        print(
            f"Rejected:        "
            f"{rows_rejected}"
        )

        print(
            f"Staged:          "
            f"{rows_staged}"
        )

        print(
            f"Target affected: "
            f"{target_affected}"
        )

        print(
            "\nIncremental products ETL completed "
            "successfully."
        )

        logger.info(
            "Incremental products ETL completed "
            "successfully."
        )

        return 0

    except Exception as error:

        status = "FAILED"

        error_message = str(
            error
        )

        watermark_after = watermark_before

        print(
            "\nIncremental products ETL FAILED."
        )

        print(
            f"Error: {error_message}"
        )

        print(
            "Watermark was not advanced."
        )

        logger.exception(
            "Incremental products ETL failed: %s",
            error_message
        )

        return 1

    finally:

        # --------------------------------------------------
        # 11. CALCULATE PIPELINE DURATION
        # --------------------------------------------------

        duration_seconds = round(
            time.perf_counter() - start_time,
            3
        )

        # --------------------------------------------------
        # 12. WRITE PIPELINE RUN METRICS
        # --------------------------------------------------

        log_row = pd.DataFrame(
            [
                {
                    "run_timestamp": run_timestamp,
                    "status": status,
                    "rows_extracted": rows_extracted,
                    "rows_selected": rows_selected,
                    "rows_valid": rows_valid,
                    "rows_rejected": rows_rejected,
                    "rows_staged": rows_staged,
                    "target_affected": target_affected,
                    "watermark_before": watermark_before,
                    "watermark_after": watermark_after,
                    "duration_seconds": duration_seconds,
                    "error_message": error_message
                }
            ]
        )

        log_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        file_exists = log_file.exists()

        log_row.to_csv(
            log_file,
            mode="a",
            header=not file_exists,
            index=False
        )

        logger.info(
            "Pipeline run finished: "
            "status=%s, extracted=%d, selected=%d, "
            "valid=%d, rejected=%d, staged=%d, "
            "target_affected=%d, duration=%.3f seconds.",
            status,
            rows_extracted,
            rows_selected,
            rows_valid,
            rows_rejected,
            rows_staged,
            target_affected,
            duration_seconds
        )

        print(
            f"\nPipeline run logged to "
            f"{log_file.name}"
        )

        print(
            f"Pipeline duration: "
            f"{duration_seconds} second(s)"
        )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    raise SystemExit(
        run_incremental_pipeline()
    )
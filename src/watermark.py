from datetime import datetime, timezone

from sqlalchemy import text

from db_config import engine


PIPELINE_NAME = "products_api_etl"


def get_watermark():
    """
    Read the last successful watermark for the
    products API ETL pipeline.

    Returns:
        datetime or None
    """

    query = text(
        """
        SELECT last_watermark
        FROM etl_watermark
        WHERE pipeline_name = :pipeline_name
        """
    )

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {
                "pipeline_name": PIPELINE_NAME
            }
        )

        watermark = result.scalar_one_or_none()

    return watermark


def update_watermark(new_watermark):
    """
    Update the pipeline watermark after a
    successful ETL run.
    """

    query = text(
        """
        UPDATE etl_watermark
        SET
            last_watermark = :new_watermark,
            last_run_at = :last_run_at,
            status = 'SUCCESS'
        WHERE pipeline_name = :pipeline_name
        """
    )

    with engine.begin() as connection:

        connection.execute(
            query,
            {
                "new_watermark": new_watermark,
                "last_run_at": datetime.now(timezone.utc),
                "pipeline_name": PIPELINE_NAME
            }
        )


if __name__ == "__main__":

    watermark = get_watermark()

    print("\nPipeline:")
    print(PIPELINE_NAME)

    print("\nCurrent watermark:")
    print(watermark)

    if watermark is None:
        print(
            "\nNo previous watermark found. "
            "The next run will behave as an initial load."
        )
    else:
        print(
            "\nPrevious watermark found. "
            "The next run can perform incremental processing."
        )
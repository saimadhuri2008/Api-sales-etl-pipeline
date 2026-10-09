from pathlib import Path

from sqlalchemy import text

from db_config import engine


def load_target():
    """
    Upsert staged product records into the
    persistent products target table.
    """

    print("\nStarting staging-to-target load...")

    project_dir = Path(__file__).resolve().parent.parent
    sql_file = project_dir / "sql" / "upsert_products.sql"

    if not sql_file.exists():
        raise FileNotFoundError(
            f"SQL file not found: {sql_file}"
        )

    upsert_sql = sql_file.read_text(
        encoding="utf-8"
    )

    with engine.begin() as connection:

        result = connection.execute(
            text(upsert_sql)
        )

        affected_rows = result.rowcount

    print(
        f"Target load completed: "
        f"{affected_rows} row(s) affected."
    )

    return affected_rows


if __name__ == "__main__":

    load_target()
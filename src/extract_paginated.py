import requests
import pandas as pd

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --------------------------------------------------
# API CONFIGURATION
# --------------------------------------------------

API_URL = "https://dummyjson.com/products"


# --------------------------------------------------
# CREATE RETRY-ENABLED SESSION
# --------------------------------------------------

def create_session():
    """
    Create a requests session with retry handling
    for temporary HTTP failures.
    """

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504
        ],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy
    )

    session = requests.Session()

    session.mount(
        "https://",
        adapter
    )

    return session


# --------------------------------------------------
# PAGINATED API EXTRACTION
# --------------------------------------------------

def extract_all_products():
    """
    Extract all products from the API using
    offset-based pagination.

    Returns:
        Pandas DataFrame containing selected
        product fields and source update timestamp.
    """

    session = create_session()

    all_products = []

    limit = 30
    skip = 0
    total = None

    print("Starting paginated API extraction...\n")

    while total is None or skip < total:

        params = {
            "limit": limit,
            "skip": skip
        }

        try:

            response = session.get(
                API_URL,
                params=params,
                timeout=30
            )

            response.raise_for_status()

        except requests.exceptions.RequestException as error:

            print(
                f"\nAPI request failed at skip={skip}."
            )

            raise RuntimeError(
                "Paginated API extraction failed."
            ) from error

        # Convert API JSON response to Python dictionary
        data = response.json()

        products = data["products"]
        total = data["total"]

        # ------------------------------------------
        # Protect against unexpected empty pages
        # ------------------------------------------

        if not products:

            print(
                f"No products returned at skip={skip}. "
                "Stopping pagination."
            )

            break

        # Add current page to complete product list
        all_products.extend(products)

        print(
            f"Fetched {len(products)} product(s) "
            f"with skip={skip}."
        )

        # Advance by the number of records
        # actually returned by the API
        skip += len(products)

    # --------------------------------------------------
    # EXTRACTION COMPLETENESS VALIDATION
    # --------------------------------------------------

    print(
        f"\nPagination finished: "
        f"{len(all_products)} product(s) retrieved."
    )

    if total is None:

        raise RuntimeError(
            "API extraction completed without receiving "
            "a total record count."
        )

    if len(all_products) != total:

        raise RuntimeError(
            f"Incomplete API extraction: "
            f"expected {total} product(s), "
            f"but retrieved {len(all_products)}."
        )

    print(
        f"Extraction validated: "
        f"{len(all_products)}/{total} product(s) retrieved."
    )

    # --------------------------------------------------
    # CONVERT JSON RECORDS TO DATAFRAME
    # --------------------------------------------------

    df = pd.DataFrame(all_products)

    # --------------------------------------------------
    # FLATTEN SOURCE UPDATE TIMESTAMP
    # --------------------------------------------------

    df["source_updated_at"] = df["meta"].apply(
        lambda meta: meta.get("updatedAt")
        if isinstance(meta, dict)
        else None
    )

    # Convert timestamp text into a real UTC datetime
    df["source_updated_at"] = pd.to_datetime(
        df["source_updated_at"],
        errors="coerce",
        utc=True
    )

    # --------------------------------------------------
    # SELECT FIELDS REQUIRED BY ETL PIPELINE
    # --------------------------------------------------

    selected_columns = [
        "id",
        "title",
        "category",
        "price",
        "discountPercentage",
        "rating",
        "stock",
        "brand",
        "sku",
        "source_updated_at"
    ]

    products_df = df[
        selected_columns
    ].copy()

    return products_df


# --------------------------------------------------
# STANDALONE TEST
# --------------------------------------------------

if __name__ == "__main__":

    products_df = extract_all_products()

    print("\nFinal DataFrame shape:")
    print(products_df.shape)

    print("\nFirst 5 products:")
    print(products_df.head())

    print("\nLast 5 products:")
    print(products_df.tail())

    print("\nSource update timestamps:")
    print(
        products_df[
            [
                "id",
                "title",
                "source_updated_at"
            ]
        ].head()
    )

    print("\nTimestamp data type:")
    print(
        products_df["source_updated_at"].dtype
    )

    print("\nSource timestamp range:")

    print(
        "Minimum source_updated_at:",
        products_df["source_updated_at"].min()
    )

    print(
        "Maximum source_updated_at:",
        products_df["source_updated_at"].max()
    )

    print(
        "Distinct source_updated_at values:",
        products_df["source_updated_at"].nunique()
    )
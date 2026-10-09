import requests
import pandas as pd


# --------------------------------------------------
# API CONFIGURATION
# --------------------------------------------------

API_URL = "https://dummyjson.com/products"


# --------------------------------------------------
# EXTRACT PRODUCTS
# --------------------------------------------------

def extract_products():
    """
    Extract product data from the DummyJSON API
    and return selected fields as a Pandas DataFrame.
    """

    print("Extracting products from API...")

    # Send GET request to API
    response = requests.get(
        API_URL,
        timeout=30
    )

    # Raise an exception for HTTP errors
    response.raise_for_status()

    # Convert JSON response to Python dictionary
    data = response.json()

    total_products = data["total"]
    skip = data["skip"]
    limit = data["limit"]

    print(f"Total products available: {total_products}")
    print(f"Products skipped: {skip}")
    print(f"API page limit: {limit}")

    # Extract product records
    products = data["products"]

    print(
        f"Received {len(products)} product(s) "
        f"from API."
    )

    # Convert product records to DataFrame
    df = pd.DataFrame(products)

    # Select fields required by the pipeline
    selected_columns = [
        "id",
        "title",
        "category",
        "price",
        "discountPercentage",
        "rating",
        "stock",
        "brand",
        "sku"
    ]

    products_df = df[selected_columns].copy()

    return products_df


# --------------------------------------------------
# STANDALONE TEST
# --------------------------------------------------

if __name__ == "__main__":

    products_df = extract_products()

    print("\nExtracted product data:")
    print(products_df.head())

    print(
        f"\nExtracted DataFrame shape: "
        f"{products_df.shape}"
    )
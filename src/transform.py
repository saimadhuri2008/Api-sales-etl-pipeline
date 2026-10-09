import pandas as pd


def transform_products(data):
    """
    Clean and validate product data extracted from the API.

    Returns:
        valid_data: cleaned records that passed validation
        rejected_data: records that failed validation
    """

    print(
        f"Received {len(data)} product(s) "
        f"for transformation."
    )

    df = data.copy()

    # -----------------------------------------
    # 1. Standardize text fields
    # -----------------------------------------

    text_columns = [
        "title",
        "category",
        "brand",
        "sku"
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
        )

    # Brand is optional in the source API.
    df["brand"] = df["brand"].fillna("Unknown")

    # -----------------------------------------
    # 2. Enforce numeric data types
    # -----------------------------------------

    numeric_columns = [
        "id",
        "price",
        "discountPercentage",
        "rating",
        "stock"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # -----------------------------------------
    # 3. Build field-specific validation masks
    # -----------------------------------------

    missing_id = df["id"].isna()

    missing_title = (
        df["title"].isna()
        | df["title"].eq("")
    )

    missing_category = (
        df["category"].isna()
        | df["category"].eq("")
    )

    missing_price = df["price"].isna()

    missing_sku = (
        df["sku"].isna()
        | df["sku"].eq("")
    )

    invalid_id = (
        df["id"].notna()
        & (df["id"] <= 0)
    )

    invalid_price = (
        df["price"].notna()
        & (df["price"] <= 0)
    )

    invalid_discount = (
        df["discountPercentage"].isna()
        | (df["discountPercentage"] < 0)
        | (df["discountPercentage"] > 100)
    )

    invalid_rating = (
        df["rating"].isna()
        | (df["rating"] < 0)
        | (df["rating"] > 5)
    )

    invalid_stock = (
        df["stock"].isna()
        | (df["stock"] < 0)
    )

    duplicate_ids = df["id"].duplicated(
        keep="first"
    )

    duplicate_skus = df["sku"].duplicated(
        keep="first"
    )

    # -----------------------------------------
    # 4. Create rejection reasons
    # -----------------------------------------

    rejection_reasons = pd.Series(
        [[] for _ in range(len(df))],
        index=df.index,
        dtype="object"
    )

    def add_reason(mask, reason):
        for index in df.index[mask]:
            rejection_reasons.at[index].append(reason)

    add_reason(
        missing_id,
        "Missing product ID"
    )

    add_reason(
        missing_title,
        "Missing title"
    )

    add_reason(
        missing_category,
        "Missing category"
    )

    add_reason(
        missing_price,
        "Missing price"
    )

    add_reason(
        missing_sku,
        "Missing SKU"
    )

    add_reason(
        invalid_id,
        "Invalid product ID"
    )

    add_reason(
        invalid_price,
        "Invalid price"
    )

    add_reason(
        invalid_discount,
        "Invalid discount percentage"
    )

    add_reason(
        invalid_rating,
        "Invalid rating"
    )

    add_reason(
        invalid_stock,
        "Invalid stock"
    )

    add_reason(
        duplicate_ids,
        "Duplicate product ID"
    )

    add_reason(
        duplicate_skus,
        "Duplicate SKU"
    )

    # Convert list of reasons into readable text
    df["rejection_reason"] = rejection_reasons.apply(
        lambda reasons: "; ".join(reasons)
    )

    # -----------------------------------------
    # 5. Separate valid and rejected records
    # -----------------------------------------

    reject_mask = df["rejection_reason"].ne("")

    rejected_data = df[
        reject_mask
    ].copy()

    valid_data = df[
        ~reject_mask
    ].copy()

    # Valid rows do not need rejection metadata
    valid_data = valid_data.drop(
        columns=["rejection_reason"]
    )

    # -----------------------------------------
    # 6. Transformation summary
    # -----------------------------------------

    print(
        f"Transformation completed: "
        f"{len(valid_data)} valid product(s), "
        f"{len(rejected_data)} rejected product(s)."
    )

    if not rejected_data.empty:

        print("\nRejected records by reason:")

        reason_summary = (
            rejected_data["rejection_reason"]
            .str.split("; ")
            .explode()
            .value_counts()
        )

        print(reason_summary)

    return valid_data, rejected_data


# --------------------------------------------------
# Standalone test
# --------------------------------------------------

if __name__ == "__main__":

    from extract_paginated import extract_all_products

    extracted_data = extract_all_products()

    valid_data, rejected_data = transform_products(
        extracted_data
    )

    print("\nValid products:")
    print(valid_data.head())

    print("\nValid DataFrame shape:")
    print(valid_data.shape)

    print("\nRejected DataFrame shape:")
    print(rejected_data.shape)

    print("\nBrand values after standardization:")
    print(
        valid_data["brand"]
        .value_counts(dropna=False)
        .head(10)
    )

    if not rejected_data.empty:

        print("\nRejected records:")

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
from extract_paginated import extract_all_products


df = extract_all_products()


print("\nData types:")
print(df.dtypes)


print("\nMissing values:")
print(df.isna().sum())


print("\nDuplicate product IDs:")
print(df["id"].duplicated().sum())


print("\nDuplicate SKUs:")
print(df["sku"].duplicated().sum())


print("\nBasic numeric summary:")
print(
    df[
        [
            "price",
            "discountPercentage",
            "rating",
            "stock"
        ]
    ].describe()
)
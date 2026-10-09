INSERT INTO products (
    product_id,
    title,
    category,
    price,
    discount_percentage,
    rating,
    stock,
    brand,
    sku
)
SELECT
    id,
    title,
    category,
    price,
    discount_percentage,
    rating,
    stock,
    brand,
    sku
FROM stg_products

ON CONFLICT (product_id)
DO UPDATE SET
    title = EXCLUDED.title,
    category = EXCLUDED.category,
    price = EXCLUDED.price,
    discount_percentage = EXCLUDED.discount_percentage,
    rating = EXCLUDED.rating,
    stock = EXCLUDED.stock,
    brand = EXCLUDED.brand,
    sku = EXCLUDED.sku,
    updated_at = CURRENT_TIMESTAMP

WHERE
    products.title IS DISTINCT FROM EXCLUDED.title
    OR products.category IS DISTINCT FROM EXCLUDED.category
    OR products.price IS DISTINCT FROM EXCLUDED.price
    OR products.discount_percentage
        IS DISTINCT FROM EXCLUDED.discount_percentage
    OR products.rating IS DISTINCT FROM EXCLUDED.rating
    OR products.stock IS DISTINCT FROM EXCLUDED.stock
    OR products.brand IS DISTINCT FROM EXCLUDED.brand
    OR products.sku IS DISTINCT FROM EXCLUDED.sku;
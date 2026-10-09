-- ============================================================
-- API Sales ETL Pipeline
-- PostgreSQL Database Objects
-- ============================================================


-- ============================================================
-- 1. STAGING TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_products (
    id INTEGER,
    title VARCHAR(255),
    category VARCHAR(100),
    price NUMERIC(12, 2),
    discount_percentage NUMERIC(5, 2),
    rating NUMERIC(3, 2),
    stock INTEGER,
    brand VARCHAR(255),
    sku VARCHAR(100),
    source_updated_at TIMESTAMPTZ
);


-- ============================================================
-- 2. TARGET TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,

    title VARCHAR(255) NOT NULL,

    category VARCHAR(100) NOT NULL,

    price NUMERIC(12, 2) NOT NULL
        CHECK (
            price > 0
        ),

    discount_percentage NUMERIC(5, 2)
        CHECK (
            discount_percentage >= 0
            AND discount_percentage <= 100
        ),

    rating NUMERIC(3, 2)
        CHECK (
            rating >= 0
            AND rating <= 5
        ),

    stock INTEGER NOT NULL
        CHECK (
            stock >= 0
        ),

    brand VARCHAR(255),

    sku VARCHAR(100) NOT NULL UNIQUE,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- 3. ETL WATERMARK CONTROL TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS etl_watermark (
    pipeline_name VARCHAR(100) PRIMARY KEY,

    last_watermark TIMESTAMPTZ,

    last_run_at TIMESTAMPTZ,

    status VARCHAR(50) NOT NULL
        DEFAULT 'NEVER_RUN'
);


-- ============================================================
-- 4. INITIALIZE PRODUCTS PIPELINE WATERMARK
-- ============================================================

INSERT INTO etl_watermark (
    pipeline_name,
    last_watermark,
    last_run_at,
    status
)
VALUES (
    'products_api_etl',
    NULL,
    NULL,
    'NEVER_RUN'
)
ON CONFLICT (pipeline_name)
DO NOTHING;
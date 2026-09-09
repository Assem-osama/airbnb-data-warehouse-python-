import os
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from sql_server_connection import get_sql_server_engine


# CONFIGURATION

BASE_DIR = Path(__file__).resolve().parents[2]

STAGING_DIR = BASE_DIR / "data" / "staging"

LISTINGS_FILE = STAGING_DIR / "stg_listings.csv"
REVIEWS_FILE = STAGING_DIR / "stg_reviews.csv"
NEIGHBOURHOODS_FILE = STAGING_DIR / "stg_neighbourhoods.csv"
CALENDAR_FILE = STAGING_DIR / "stg_calendar.csv"

CHUNK_SIZE = 10_000

def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def check_file_exists(file_path):
    if not file_path.exists():
        raise FileNotFoundError(
            f"Staging file not found: {file_path}"
        )


def get_existing_row_count(engine, table_name):
    query = text(f"""
        SELECT COUNT(*)
        FROM dw.{table_name}
    """)

    with engine.connect() as connection:
        return connection.execute(query).scalar()


# LOAD DIMENSION: NEIGHBOURHOOD

def load_dim_neighbourhood(engine):

    print_section("LOADING DIM_NEIGHBOURHOOD")

    df = pd.read_csv(NEIGHBOURHOODS_FILE)

    print(f"Source rows: {len(df):,}")

    # Keep only required DW columns
    df = df[
        [
            "neighbourhood",
            "neighbourhood_group"
        ]
    ].copy()

    # Remove duplicate neighbourhoods
    df = df.drop_duplicates(
        subset=["neighbourhood"]
    )

    # Remove invalid records
    df = df.dropna(
        subset=[
            "neighbourhood",
            "neighbourhood_group"
        ]
    )

    print(f"Rows after cleaning: {len(df):,}")

    # Insert into SQL Server
    df.to_sql(
        name="DimNeighbourhood",
        con=engine,
        schema="dw",
        if_exists="append",
        index=False,
        chunksize=1000
    )

    count = get_existing_row_count(engine,"DimNeighbourhood")

    print(f"DimNeighbourhood rows in DW: {count:,}")


# ============================================================
# LOAD DIMENSION: DATE
# ============================================================

def generate_date_dimension(calendar_file, reviews_file):

    print_section("GENERATING DIM_DATE")

    calendar_dates = pd.read_csv(
        calendar_file,
        usecols=["date"],
        parse_dates=["date"]
    )

    review_dates = pd.read_csv(
        reviews_file,
        usecols=["date"],
        parse_dates=["date"]
    )

    dates = pd.concat(
        [
            calendar_dates,
            review_dates
        ],
        ignore_index=True
    )

    dates = dates.drop_duplicates()

    dates = dates.dropna(
        subset=["date"]
    )

    print(
        f"Unique dates found: {len(dates):,}"
    )

    dates["full_date"] = dates["date"]

    dates["date_key"] = (
        dates["full_date"]
        .dt.strftime("%Y%m%d")
        .astype(int)
    )

    dates["day"] = dates["full_date"].dt.day

    dates["month"] = dates["full_date"].dt.month

    dates["month_name"] = (
        dates["full_date"].dt.month_name()
    )

    dates["quarter"] = (
        dates["full_date"].dt.quarter
    )

    dates["year"] = (
        dates["full_date"].dt.year
    )

    dates["day_name"] = (
        dates["full_date"].dt.day_name()
    )

    dates["day_of_week"] = (
        dates["full_date"].dt.dayofweek + 1
    )

    dates["week_of_year"] = (
        dates["full_date"]
        .dt.isocalendar()
        .week
        .astype(int)
    )

    return dates[
        [
            "date_key",
            "full_date",
            "day",
            "month",
            "month_name",
            "quarter",
            "year",
            "day_name",
            "day_of_week",
            "week_of_year"
        ]
    ]

def load_dim_date(engine):

    dates = generate_date_dimension(
        CALENDAR_FILE,
        REVIEWS_FILE
    )

    print(f"Loading {len(dates):,} dates...")

    dates.to_sql(
        name="DimDate",
        con=engine,
        schema="dw",
        if_exists="append",
        index=False,
        chunksize=1000
    )

    count = get_existing_row_count(
        engine,
        "DimDate"
    )

    print(
        f"DimDate rows in DW: {count:,}"
    )


# ============================================================
# LOAD DIMENSION: LISTING
# ============================================================

def load_dim_listing(engine):

    print_section("LOADING DIM_LISTING")

    listings = pd.read_csv(
        LISTINGS_FILE,
        parse_dates=["host_since"]
    )

    print(
        f"Source listing rows: {len(listings):,}"
    )

    listings = listings[
        [
            "listing_id",
            "host_id",
            "host_name",
            "price",
            "host_is_superhost",
            "neighbourhood",
            "latitude",
            "longitude",
            "property_type",
            "room_type",
            "accommodates",
            "bathrooms",
            "bedrooms",
            "beds"
        ]
    ].copy()

    listings = listings.drop_duplicates(
        subset=["listing_id"]
    )

    if "price" in listings.columns:
        listings["price"] = (
            listings["price"]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        listings["price"] = pd.to_numeric(listings["price"], errors="coerce")

    # Lookup neighbourhood surrogate key

    dim_neighbourhood = pd.read_sql(
        """
        SELECT
            neighbourhood_key,
            neighbourhood
        FROM dw.DimNeighbourhood
        """,
        engine
    )

    listings = listings.merge(
        dim_neighbourhood,
        on="neighbourhood",
        how="left"
    )

    # Validate lookup

    missing_neighbourhood_keys = (
        listings["neighbourhood_key"]
        .isna()
        .sum()
    )

    print(
        "Listings without neighbourhood key:",
        missing_neighbourhood_keys
    )

    if missing_neighbourhood_keys > 0:

        missing = listings[
            listings["neighbourhood_key"].isna()
        ][
            [
                "listing_id",
                "neighbourhood"
            ]
        ]

        print(
            "WARNING: Some listings could not be "
            "matched to a neighbourhood."
        )

        print(missing.head())


    # Prepare final DW dataframe

    listings = listings[
        [
            "listing_id",
            "host_id",
            "host_name",
            "price",
            "host_is_superhost",
            "neighbourhood_key",
            "latitude",
            "longitude",
            "property_type",
            "room_type",
            "accommodates",
            "bathrooms",
            "bedrooms",
            "beds"
        ]
    ]

    # Convert boolean to SQL Server BIT compatible values
    listings["host_is_superhost"] = (
        listings["host_is_superhost"]
        .map({
            True: 1,
            False: 0,
            "t": 1,
            "f": 0
        })
    )

    print(
        f"Final listing rows: {len(listings):,}"
    )

    listings.to_sql(
        name="DimListing",
        con=engine,
        schema="dw",
        if_exists="append",
        index=False,
        chunksize=1000
    )

    count = get_existing_row_count(
        engine,
        "DimListing"
    )

    print(
        f"DimListing rows in DW: {count:,}"
    )


# ============================================================
# LOAD FACT: REVIEWS
# ============================================================

def load_fact_reviews(engine):

    print_section("LOADING FACT_REVIEWS")

    # Load lookup table

    listing_lookup = pd.read_sql(
        """
        SELECT
            listing_key,
            listing_id
        FROM dw.DimListing
        """,
        engine
    )

    print(
        f"Listing lookup rows: "
        f"{len(listing_lookup):,}"
    )

    # Process reviews in chunks

    total_loaded = 0

    for chunk_number, reviews in enumerate(
        pd.read_csv(
            REVIEWS_FILE,
            chunksize=CHUNK_SIZE,
            parse_dates=["date"]
        ),
        start=1
    ):

        print(
            f"Processing reviews chunk "
            f"{chunk_number}..."
        )

        reviews = reviews[
            [
                "listing_id",
                "review_id",
                "date",
                "reviewer_id"
            ]
        ].copy()

        reviews = reviews.merge(
            listing_lookup,
            on="listing_id",
            how="inner"
        )
        
        reviews["date_key"] = (
            reviews["date"]
            .dt.strftime("%Y%m%d")
            .astype(int)
        )

        # Add measure

        reviews["review_count"] = 1

        # Final columns

        reviews = reviews[
            [
                "listing_key",
                "date_key",
                "review_id",
                "reviewer_id",
                "review_count"
            ]
        ]

        reviews.to_sql(
            name="FactReviews",
            con=engine,
            schema="dw",
            if_exists="append",
            index=False,
            chunksize=CHUNK_SIZE,
            method=None
        )

        total_loaded += len(reviews)

        print(
            f"Loaded so far: {total_loaded:,}"
        )

    count = get_existing_row_count(
        engine,
        "FactReviews"
    )

    print(
        f"FactReviews rows in DW: {count:,}"
    )


# ============================================================
# LOAD FACT: AVAILABILITY
# ============================================================

def load_fact_availability(engine):

    print_section("LOADING FACT_AVAILABILITY")

    listing_lookup = pd.read_sql(
        """
        SELECT
            listing_key,
            listing_id
        FROM dw.DimListing
        """,
        engine
    )

    print(
        f"Listing lookup rows: "
        f"{len(listing_lookup):,}"
    )

    total_loaded = 0

    # Process calendar in chunks
    for chunk_number, calendar in enumerate(
        pd.read_csv(
            CALENDAR_FILE,
            chunksize=CHUNK_SIZE,
            parse_dates=["date"]
        ),
        start=1
    ):

        print(
            f"Processing calendar chunk "
            f"{chunk_number}..."
        )

        
        calendar = calendar[
            [
                "listing_id",
                "date",
                "available",
                "minimum_nights",
                "maximum_nights"
            ]
        ].copy()

        calendar = calendar.merge(
            listing_lookup,
            on="listing_id",
            how="inner"
        )

        # Create date_key
        calendar["date_key"] = (
            calendar["date"]
            .dt.strftime("%Y%m%d")
            .astype(int)
        )

        # Convert availability

        calendar["available"] = (
            calendar["available"]
            .map({
                "t": 1,
                "f": 0,
                True: 1,
                False: 0
            })
        )

        # Final columns
        calendar = calendar[
            [
                "listing_key",
                "date_key",
                "available",
                "minimum_nights",
                "maximum_nights"
            ]
        ]

        # Remove duplicate listing/date
        calendar = calendar.drop_duplicates(
            subset=[
                "listing_key",
                "date_key"
            ]
        )

        calendar.to_sql(
            name="FactAvailability",
            con=engine,
            schema="dw",
            if_exists="append",
            index=False,
            chunksize=CHUNK_SIZE,
            method=None
        )

        total_loaded += len(calendar)

        print(
            f"Loaded so far: {total_loaded:,}"
        )

    count = get_existing_row_count(
        engine,
        "FactAvailability"
    )

    print(
        f"FactAvailability rows in DW: {count:,}"
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_dw(engine):

    print_section("DATA WAREHOUSE VALIDATION")

    tables = [
        "DimNeighbourhood",
        "DimListing",
        "DimDate",
        "FactReviews",
        "FactAvailability"
    ]

    for table in tables:

        count = get_existing_row_count(
            engine,
            table
        )

        print(
            f"{table:<25} {count:>12,} rows"
        )

    # Check orphan reviews
    with engine.connect() as connection:

        orphan_reviews = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM dw.FactReviews fr
                LEFT JOIN dw.DimListing dl
                    ON fr.listing_key = dl.listing_key
                WHERE dl.listing_key IS NULL
            """)
        ).scalar()

        print(
            f"\nOrphan FactReviews: "
            f"{orphan_reviews:,}"
        )

        # Check orphan availability
        orphan_availability = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM dw.FactAvailability fa
                LEFT JOIN dw.DimListing dl
                    ON fa.listing_key = dl.listing_key
                WHERE dl.listing_key IS NULL
            """)
        ).scalar()

        print(
            f"Orphan FactAvailability: "
            f"{orphan_availability:,}"
        )

        # Check invalid dates
        invalid_review_dates = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM dw.FactReviews fr
                LEFT JOIN dw.DimDate dd
                    ON fr.date_key = dd.date_key
                WHERE dd.date_key IS NULL
            """)
        ).scalar()

        print(
            f"Invalid review date keys: "
            f"{invalid_review_dates:,}"
        )

        invalid_calendar_dates = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM dw.FactAvailability fa
                LEFT JOIN dw.DimDate dd
                    ON fa.date_key = dd.date_key
                WHERE dd.date_key IS NULL
            """)
        ).scalar()

        print(
            f"Invalid availability date keys: "
            f"{invalid_calendar_dates:,}"
        )

def clear_dwh(engine):
    print_section("CLEARING OLD DATA (RESETTING DWH)")
    
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dw.FactAvailability"))
        print("Truncated table: dw.FactAvailability")
        
        conn.execute(text("TRUNCATE TABLE dw.FactReviews"))
        print("Truncated table: dw.FactReviews")

        conn.execute(text("DELETE FROM dw.DimListing"))
        print("Cleared table: dw.DimListing")
        
        conn.execute(text("DELETE FROM dw.DimDate"))
        print("Cleared table: dw.DimDate")
        
        conn.execute(text("DELETE FROM dw.DimNeighbourhood"))
        print("Cleared table: dw.DimNeighbourhood")


# ============================================================
# MAIN ETL PIPELINE
# ============================================================

def main():

    start_time = time.time()

    print("=" * 70)
    print("AIRBNB BARCELONA - DATA WAREHOUSE LOAD")
    print("=" * 70)

    # Check staging files

    print_section("CHECKING STAGING FILES")

    files = [
        LISTINGS_FILE,
        REVIEWS_FILE,
        NEIGHBOURHOODS_FILE,
        CALENDAR_FILE
    ]

    for file in files:

        check_file_exists(file)

        print(f"OK: {file}")

    # Connect to SQL Server

    print_section("CONNECTING TO SQL SERVER")

    engine = get_sql_server_engine()

    with engine.connect() as connection:

        connection.execute(
            text("SELECT 1")
        )

    print("SQL Server connection successful.")

    clear_dwh(engine)

    # Load dimensions & facts
    load_dim_neighbourhood(engine)

    load_dim_date(engine)

    load_dim_listing(engine)

    load_fact_reviews(engine)

    load_fact_availability(engine)

    # Validate
    validate_dw(engine)

    # Finish
    
    elapsed = time.time() - start_time

    print_section("ETL COMPLETED")

    print(
        f"Total execution time: "
        f"{elapsed / 60:.2f} minutes"
    )


if __name__ == "__main__":
    main()
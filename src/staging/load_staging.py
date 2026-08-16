import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
STAGING_DIR = BASE_DIR / "data" / "staging"

STAGING_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. LOAD RAW DATA
# ============================================================

def load_raw_data():
    print("LOADING RAW DATA")

    listings = pd.read_csv(RAW_DIR / "listings.csv.gz", compression='gzip')
    reviews = pd.read_csv(RAW_DIR / "reviews.csv.gz", compression='gzip')
    calendar = pd.read_csv(RAW_DIR / "calendar.csv.gz", compression='gzip')
    neighbourhoods = pd.read_csv(RAW_DIR / "neighbourhoods.csv")

    return listings, reviews, calendar, neighbourhoods

# ============================================================
# 3. TRANSFORM LISTINGS
# ============================================================

def transform_listings(listings):

    print("TRANSFORMING LISTINGS")

    # Select columns needed for our Data Warehouse
    listing_columns = [
        "id",
        "host_id",
        "host_name",
        "host_since",
        "host_is_superhost",

        "neighbourhood_cleansed",
        "neighbourhood_group_cleansed",

        "latitude",
        "longitude",

        "property_type",
        "room_type",

        "accommodates",
        "bathrooms",
        "bedrooms",
        "beds",

        "price",
        "minimum_nights",
        "maximum_nights",

        "availability_30",
        "availability_60",
        "availability_90",
        "availability_365",

        "number_of_reviews",
        "number_of_reviews_ltm",
        "number_of_reviews_l30d",

        "first_review",
        "last_review",

        "review_scores_rating",
        "reviews_per_month",

        "calculated_host_listings_count"
    ]

    stg_listings = listings[listing_columns].copy()

    # Rename columns

    stg_listings = stg_listings.rename(
        columns={
            "id": "listing_id",
            "neighbourhood_cleansed": "neighbourhood",
            "neighbourhood_group_cleansed": "neighbourhood_group"
        }
    )

    # ID columns

    stg_listings["listing_id"] = (
        stg_listings["listing_id"].astype("Int64")
    )

    stg_listings["host_id"] = (
        stg_listings["host_id"].astype("Int64")
    )

    # Date columns

    date_columns = [
        "host_since",
        "first_review",
        "last_review"
    ]

    for column in date_columns:
        stg_listings[column] = pd.to_datetime(
            stg_listings[column],
            errors="coerce"
        )

    # Price

    stg_listings["price"] = (
        stg_listings["price"]
        .astype("string")
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
    )

    stg_listings["price"] = pd.to_numeric(
        stg_listings["price"],
        errors="coerce"
    )

    # Boolean columns

    stg_listings["host_is_superhost"] = (
        stg_listings["host_is_superhost"]
        .map({
            "t": True,
            "f": False
        })
    )

    # Remove unnecessary whitespace

    string_columns = [
        "host_name",
        "neighbourhood",
        "neighbourhood_group",
        "property_type",
        "room_type"
    ]

    for column in string_columns:
        stg_listings[column] = (
            stg_listings[column]
            .astype("string")
            .str.strip()
        )

    print(
        f"Listings after transformation: "
        f"{len(stg_listings):,}"
    )



    return stg_listings


# ============================================================
# 4. TRANSFORM REVIEWS
# ============================================================

def transform_reviews(reviews):

    print("TRANSFORMING REVIEWS")

    stg_reviews = reviews.copy()

    # Rename / standardize columns

    stg_reviews = stg_reviews.rename(
        columns={
            "id": "review_id"
        }
    )

    # IDs

    stg_reviews["listing_id"] = (
        stg_reviews["listing_id"].astype("Int64")
    )

    stg_reviews["review_id"] = (
        stg_reviews["review_id"].astype("Int64")
    )

    stg_reviews["reviewer_id"] = (
        stg_reviews["reviewer_id"].astype("Int64")
    )

    # Date

    stg_reviews["date"] = pd.to_datetime(
        stg_reviews["date"],
        errors="coerce"
    )

    # String cleaning

    stg_reviews["reviewer_name"] = (
        stg_reviews["reviewer_name"]
        .astype("string")
        .str.strip()
    )

    stg_reviews["comments"] = (
        stg_reviews["comments"]
        .astype("string")
        .str.strip()
    )

    print(
        f"Reviews after transformation: "
        f"{len(stg_reviews):,}"
    )

    return stg_reviews


# ============================================================
# 5. TRANSFORM NEIGHBOURHOODS
# ============================================================

def transform_neighbourhoods(neighbourhoods):

    print("TRANSFORMING NEIGHBOURHOODS")

    stg_neighbourhoods = neighbourhoods.copy()

    # Clean column names

    stg_neighbourhoods.columns = [
        column.strip().lower()
        for column in stg_neighbourhoods.columns
    ]

    # Clean string values

    for column in [
        "neighbourhood_group",
        "neighbourhood"
    ]:
        stg_neighbourhoods[column] = (
            stg_neighbourhoods[column]
            .astype("string")
            .str.strip()
        )

    # Remove exact duplicates

    stg_neighbourhoods = (
        stg_neighbourhoods
        .drop_duplicates()
        .reset_index(drop=True)
    )

    print(
        f"Neighbourhoods after transformation: "
        f"{len(stg_neighbourhoods):,}"
    )

    return stg_neighbourhoods

# 6. TRANSFORM CALENDAR

def transform_calendar(calendar):

    print("TRANSFORMING CALENDAR")

    stg_calendar = calendar.copy()

    # IDs

    stg_calendar["listing_id"] = (
        stg_calendar["listing_id"].astype("Int64")
    )

    # Date

    stg_calendar["date"] = pd.to_datetime(
        stg_calendar["date"],
        errors="coerce"
    )

    # Available

    stg_calendar["available"] = (
        stg_calendar["available"]
        .map({
            "t": True,
            "f": False
        })
    )

    # Numeric columns

    numeric_columns = [
        "minimum_nights",
        "maximum_nights"
    ]

    for column in numeric_columns:
        stg_calendar[column] = pd.to_numeric(
            stg_calendar[column],
            errors="coerce"
        )

    # Remove exact duplicate rows

    stg_calendar = (
        stg_calendar
        .drop_duplicates()
        .reset_index(drop=True)
    )

    print(
        f"Calendar after transformation: "
        f"{len(stg_calendar):,}"
    )

    return stg_calendar




# ============================================================
# CLEAN INVALID DATA
# ============================================================

def clean_invalid_data(listings, reviews, calendar):

    print("CLEANING INVALID DATA (DROPPING BAD RECORDS)")

    initial_listings = len(listings)
    clean_listings = listings[
        listings["minimum_nights"] <= listings["maximum_nights"]
    ].copy()
    
    dropped_listings = initial_listings - len(clean_listings)
    print(f"Dropped {dropped_listings} invalid listings.")

    valid_listing_ids = set(clean_listings["listing_id"].dropna())

    initial_reviews = len(reviews)
    clean_reviews = reviews[
        reviews["listing_id"].isin(valid_listing_ids)
    ].copy()
    
    dropped_reviews = initial_reviews - len(clean_reviews)
    print(f"Dropped {dropped_reviews:,} orphaned review records.")

    initial_calendar = len(calendar)
    clean_calendar = calendar[
        calendar["listing_id"].isin(valid_listing_ids)
    ].copy()
    
    dropped_calendar = initial_calendar - len(clean_calendar)
    print(f"Dropped {dropped_calendar:,} orphaned calendar records.")

    return clean_listings, clean_reviews, clean_calendar




# 7. VALIDATE LISTINGS

def validate_listings(listings):

    print("VALIDATING LISTINGS")

    # Listing ID must be unique
    duplicate_ids = listings["listing_id"].duplicated().sum()

    print(f"Duplicate listing IDs: {duplicate_ids}")

    assert duplicate_ids == 0, \
        "Duplicate listing IDs found!"

    # Listing ID cannot be NULL
    missing_ids = listings["listing_id"].isna().sum()

    print(f"Missing listing IDs: {missing_ids}")

    assert missing_ids == 0, \
        "Missing listing IDs found!"

    # Price cannot be negative
    negative_prices = (listings["price"] < 0).sum()

    print(f"Negative prices: {negative_prices}")

    assert negative_prices == 0, \
        "Negative prices found!"

    # Accommodates must be positive
    invalid_accommodates = (listings["accommodates"] <= 0).sum()

    print(
        f"Invalid accommodates: "
        f"{invalid_accommodates}"
    )

    assert invalid_accommodates == 0, \
        "Invalid accommodates found!"

    # Bedrooms cannot be negative
    invalid_bedrooms = (
        listings["bedrooms"] < 0
    ).sum()

    print(
        f"Negative bedrooms: "
        f"{invalid_bedrooms}"
    )

    assert invalid_bedrooms == 0, \
        "Negative bedrooms found!"

    # Minimum nights <= Maximum nights
    invalid_nights = (
        listings["minimum_nights"]
        > listings["maximum_nights"]
    ).sum()

    print(
        f"Invalid minimum/maximum nights: "
        f"{invalid_nights}"
    )

    # We report these instead of immediately deleting them
    if invalid_nights > 0:
        print(
            "WARNING: Some listings have "
            "minimum_nights > maximum_nights."
        )

    # Review rating must be between 1 and 5
    invalid_ratings = (
        (
            listings["review_scores_rating"] < 1
        )
        |
        (
            listings["review_scores_rating"] > 5
        )
    ).sum()

    print(
        f"Invalid review ratings: "
        f"{invalid_ratings}"
    )

    assert invalid_ratings == 0, \
        "Invalid review ratings found!"

    print("Listings validation completed.")


# 8. VALIDATE REVIEWS

def validate_reviews(reviews):

    print("VALIDATING REVIEWS")

    # Review ID should be unique
    duplicate_review_ids = (
        reviews["review_id"]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicate review IDs: "
        f"{duplicate_review_ids}"
    )

    assert duplicate_review_ids == 0, \
        "Duplicate review IDs found!"

    # Listing ID cannot be NULL
    missing_listing_ids = (
        reviews["listing_id"]
        .isna()
        .sum()
    )

    print(
        f"Missing listing IDs: "
        f"{missing_listing_ids}"
    )

    assert missing_listing_ids == 0, \
        "Reviews contain missing listing IDs!"

    # Date cannot be NULL
    missing_dates = (
        reviews["date"]
        .isna()
        .sum()
    )

    print(
        f"Missing review dates: "
        f"{missing_dates}"
    )

    assert missing_dates == 0, \
        "Reviews contain invalid dates!"

    print("Reviews validation completed.")


# 9. VALIDATE NEIGHBOURHOODS

def validate_neighbourhoods(neighbourhoods):

    print("VALIDATING NEIGHBOURHOODS")

    missing_names = (
        neighbourhoods["neighbourhood"]
        .isna()
        .sum()
    )

    missing_groups = (
        neighbourhoods["neighbourhood_group"]
        .isna()
        .sum()
    )

    print(
        f"Missing neighbourhood names: "
        f"{missing_names}"
    )

    print(
        f"Missing neighbourhood groups: "
        f"{missing_groups}"
    )

    assert missing_names == 0, \
        "Missing neighbourhood names found!"

    assert missing_groups == 0, \
        "Missing neighbourhood groups found!"

    # Neighbourhood should be unique
    duplicate_neighbourhoods = (
        neighbourhoods["neighbourhood"]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicate neighbourhoods: "
        f"{duplicate_neighbourhoods}"
    )

    assert duplicate_neighbourhoods == 0, \
        "Duplicate neighbourhood names found!"

    print(
        "Neighbourhood validation completed."
    )


# 10. VALIDATE CALENDAR

def validate_calendar(calendar):

    print("VALIDATING CALENDAR")

    # Listing ID cannot be NULL
    missing_listing_ids = (
        calendar["listing_id"]
        .isna()
        .sum()
    )

    print(
        f"Missing listing IDs: "
        f"{missing_listing_ids}"
    )

    assert missing_listing_ids == 0, \
        "Calendar contains missing listing IDs!"

    # Date cannot be NULL
    missing_dates = (
        calendar["date"]
        .isna()
        .sum()
    )

    print(
        f"Missing dates: "
        f"{missing_dates}"
    )

    assert missing_dates == 0, \
        "Calendar contains invalid dates!"

    # Available should not be NULL
    missing_available = (
        calendar["available"]
        .isna()
        .sum()
    )

    print(
        f"Missing availability values: "
        f"{missing_available}"
    )

    assert missing_available == 0, \
        "Calendar contains invalid availability values!"

    # Listing + Date should be unique
    duplicate_listing_dates = (
        calendar
        .duplicated(
            subset=["listing_id", "date"]
        )
        .sum()
    )

    print(
        f"Duplicate listing/date records: "
        f"{duplicate_listing_dates}"
    )

    assert duplicate_listing_dates == 0, \
        "Duplicate listing/date records found!"

    print("Calendar validation completed.")


# ============================================================
# 11. REFERENTIAL INTEGRITY
# ============================================================

def validate_relationships(listings,reviews,calendar):

    print("VALIDATING RELATIONSHIPS")

    listing_ids = set(
        listings["listing_id"].dropna()
    )

    # --------------------------------------------------------
    # Reviews -> Listings
    # --------------------------------------------------------

    review_listing_ids = set(
        reviews["listing_id"].dropna()
    )

    missing_review_listings = (
        review_listing_ids - listing_ids
    )

    print(
        "Listings missing from reviews: "
        f"{len(missing_review_listings)}"
    )

    # --------------------------------------------------------
    # Calendar -> Listings
    # --------------------------------------------------------

    calendar_listing_ids = set(
        calendar["listing_id"].dropna()
    )

    missing_calendar_listings = (
        calendar_listing_ids - listing_ids
    )

    print(
        "Listings missing from calendar: "
        f"{len(missing_calendar_listings)}"
    )

    if missing_calendar_listings:
        print(
            "WARNING: Calendar contains listing IDs "
            "that are not present in listings."
        )

    print("Relationship validation completed.")


# ============================================================
# 12. SAVE STAGING DATA
# ============================================================

def save_staging_data(listings,reviews,neighbourhoods,calendar):

    print("SAVING STAGING DATA")

    listings.to_csv(
        STAGING_DIR / "stg_listings.csv",
        index=False
    )

    reviews.to_csv(
        STAGING_DIR / "stg_reviews.csv",
        index=False
    )

    neighbourhoods.to_csv(
        STAGING_DIR / "stg_neighbourhoods.csv",
        index=False
    )

    calendar.to_csv(
        STAGING_DIR / "stg_calendar.csv",
        index=False
    )

    print("Staging files saved successfully!")


# 13. MAIN PIPELINE

def main():

    print("\n")
    print("AIRBNB BARCELONA - STAGING PIPELINE")

    (
        listings,
        reviews,
        calendar,
        neighbourhoods
    ) = load_raw_data()

    # Transform
    stg_listings = transform_listings(listings)
    stg_reviews = transform_reviews(reviews)
    stg_neighbourhoods = transform_neighbourhoods(neighbourhoods)
    stg_calendar = transform_calendar(calendar)

    # Clean
    stg_listings, stg_reviews, stg_calendar = clean_invalid_data(
        stg_listings, 
        stg_reviews, 
        stg_calendar
    )

    # Validate
    validate_listings(stg_listings)
    validate_reviews(stg_reviews)
    validate_neighbourhoods(stg_neighbourhoods)
    validate_calendar(stg_calendar)

    # Relationships
    validate_relationships(
        stg_listings,
        stg_reviews,
        stg_calendar
    )

    # Save
    save_staging_data(
        stg_listings,
        stg_reviews,
        stg_neighbourhoods,
        stg_calendar
    )

    print("STAGING PIPELINE COMPLETED SUCCESSFULLY")
    

# RUN PIPELINE

if __name__ == "__main__":
    main()
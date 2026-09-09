
SELECT
    COUNT(*) AS total_listings,
    COUNT(DISTINCT listing_id) AS unique_listings
FROM dw.DimListing;

SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT neighbourhood) AS unique_neighbourhoods
FROM dw.DimNeighbourhood;


SELECT
    COUNT(*) AS total_reviews,
    COUNT(DISTINCT review_id) AS unique_reviews
FROM dw.FactReviews;


SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT CONCAT(listing_key, '-', date_key))
        AS unique_listing_date
FROM dw.FactAvailability;
USE AirbnbDWH;
GO

-- 1. What was the cheapest most available listing in Jan 2027?
SELECT TOP 1
    l.listing_id,
    l.price,
    SUM(CAST(a.available AS INT)) AS days_available_in_jan
FROM dw.FactAvailability a
JOIN dw.DimDate d ON a.date_key = d.date_key
JOIN dw.DimListing l ON a.listing_key = l.listing_key
WHERE d.year = 2027 
  AND d.month = 1
  AND a.available = 1
GROUP BY 
    l.listing_id, 
    l.price
ORDER BY 
    days_available_in_jan DESC, 
    l.price ASC;


-- 2. What are the most reviewed listings in November 2026?
SELECT TOP 10
    l.listing_id,
    COUNT(r.review_id) AS total_reviews
FROM dw.FactReviews r
JOIN dw.DimDate d ON r.date_key = d.date_key
JOIN dw.DimListing l ON r.listing_key = l.listing_key
WHERE d.year = 2026 
  AND d.month = 11
GROUP BY 
    l.listing_id
ORDER BY 
    total_reviews DESC;


-- 3. What is the most expensive neighbourhood in Barcelona?
SELECT TOP 1
    n.neighbourhood,
    AVG(CAST(l.price AS FLOAT)) AS avg_neighborhood_price
FROM dw.DimListing l
JOIN dw.DimNeighbourhood n ON l.neighbourhood_key = n.neighbourhood_key
GROUP BY 
    n.neighbourhood
ORDER BY 
    avg_neighborhood_price DESC;


-- 4. Recommendation for a family of 4 looking for a 1-week vacation around March 2027
SELECT TOP 5
    l.listing_id,
    n.neighbourhood,
    l.accommodates,
    l.price,
    SUM(CAST(a.available AS INT)) AS available_days_in_march
FROM dw.FactAvailability a
JOIN dw.DimDate d ON a.date_key = d.date_key
JOIN dw.DimListing l ON a.listing_key = l.listing_key
JOIN dw.DimNeighbourhood n ON l.neighbourhood_key = n.neighbourhood_key
WHERE d.year = 2027
  AND d.month = 3
  AND a.available = 1
  AND l.accommodates >= 4
GROUP BY 
    l.listing_id, 
    n.neighbourhood, 
    l.accommodates, 
    l.price
HAVING SUM(CAST(a.available AS INT)) >= 7
ORDER BY 
    l.price ASC;


-- 5. Budget recommendation for 5 college students for New Year's Eve (Dec 29, 2026 - Jan 2, 2027)
SELECT TOP 5
    l.listing_id,
    n.neighbourhood,
    l.accommodates,
    l.price,
    SUM(CAST(a.available AS INT)) AS days_available_around_nye
FROM dw.FactAvailability a
JOIN dw.DimDate d ON a.date_key = d.date_key
JOIN dw.DimListing l ON a.listing_key = l.listing_key
JOIN dw.DimNeighbourhood n ON l.neighbourhood_key = n.neighbourhood_key
WHERE d.full_date BETWEEN '2026-12-29' AND '2027-01-02'
  AND a.available = 1
  AND l.accommodates >= 5
GROUP BY 
    l.listing_id, 
    n.neighbourhood, 
    l.accommodates, 
    l.price
HAVING SUM(CAST(a.available AS INT)) = 5
ORDER BY 
    l.price ASC;
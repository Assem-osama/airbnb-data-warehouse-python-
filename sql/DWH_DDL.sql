CREATE DATABASE AirbnbDWH;
GO

USE AirbnbDWH;
GO

CREATE SCHEMA dw;
GO

CREATE TABLE dw.DimNeighbourhood
(
    neighbourhood_key INT IDENTITY(1,1)
        CONSTRAINT PK_DimNeighbourhood
        PRIMARY KEY,

    neighbourhood NVARCHAR(255) NOT NULL,

    neighbourhood_group NVARCHAR(255) NOT NULL,

    CONSTRAINT UQ_DimNeighbourhood_Name
        UNIQUE (neighbourhood)
);
GO

CREATE TABLE dw.DimListing
(
    listing_key INT IDENTITY(1,1)
        CONSTRAINT PK_DimListing
        PRIMARY KEY,

    listing_id BIGINT NOT NULL,

    host_id BIGINT NULL,

    host_name NVARCHAR(255) NULL,

    price float NULL,

    host_is_superhost BIT NULL,

    neighbourhood_key INT NULL,

    latitude DECIMAL(9,6) NULL,

    longitude DECIMAL(9,6) NULL,

    property_type NVARCHAR(255) NULL,

    room_type NVARCHAR(100) NULL,

    accommodates INT NULL,

    bathrooms DECIMAL(4,1) NULL,

    bedrooms INT NULL,

    beds INT NULL,

    CONSTRAINT UQ_DimListing_ListingID
        UNIQUE (listing_id),

    CONSTRAINT FK_DimListing_Neighbourhood
        FOREIGN KEY (neighbourhood_key)
        REFERENCES dw.DimNeighbourhood(neighbourhood_key)
);
GO

CREATE TABLE dw.DimDate
(
    date_key INT
        CONSTRAINT PK_DimDate
        PRIMARY KEY,

    full_date DATE NOT NULL,

    day INT NOT NULL,

    month INT NOT NULL,

    month_name NVARCHAR(20) NOT NULL,

    quarter INT NOT NULL,

    year INT NOT NULL,

    day_name NVARCHAR(20) NOT NULL,

    day_of_week INT NOT NULL,

    week_of_year INT NOT NULL,

    CONSTRAINT UQ_DimDate_FullDate
        UNIQUE (full_date)
);
GO

CREATE TABLE dw.FactReviews
(
    review_key BIGINT IDENTITY(1,1)
        CONSTRAINT PK_FactReviews
        PRIMARY KEY,

    listing_key INT NOT NULL,

    date_key INT NOT NULL,

    review_id BIGINT NOT NULL,

    reviewer_id BIGINT NULL,

    review_count INT NOT NULL
        CONSTRAINT DF_FactReviews_ReviewCount
        DEFAULT 1,

    CONSTRAINT UQ_FactReviews_ReviewID
        UNIQUE (review_id),

    CONSTRAINT FK_FactReviews_Listing
        FOREIGN KEY (listing_key)
        REFERENCES dw.DimListing(listing_key),

    CONSTRAINT FK_FactReviews_Date
        FOREIGN KEY (date_key)
        REFERENCES dw.DimDate(date_key)
);
GO

CREATE TABLE dw.FactAvailability
(
    availability_key BIGINT IDENTITY(1,1)
        CONSTRAINT PK_FactAvailability
        PRIMARY KEY,

    listing_key INT NOT NULL,

    date_key INT NOT NULL,

    available BIT NOT NULL,

    minimum_nights INT NULL,

    maximum_nights INT NULL,

    CONSTRAINT FK_FactAvailability_Listing
        FOREIGN KEY (listing_key)
        REFERENCES dw.DimListing(listing_key),

    CONSTRAINT FK_FactAvailability_Date
        FOREIGN KEY (date_key)
        REFERENCES dw.DimDate(date_key),

    CONSTRAINT UQ_FactAvailability_ListingDate
        UNIQUE (listing_key, date_key)
);
GO
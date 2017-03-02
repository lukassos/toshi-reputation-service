CREATE TABLE IF NOT EXISTS reviews (
    reviewer_address VARCHAR NOT NULL,
    reviewee_address VARCHAR NOT NULL,

    rating DECIMAL,
    review VARCHAR,

    created TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),

    PRIMARY KEY (reviewer_address, reviewee_address)
);

CREATE INDEX IF NOT EXISTS idx_reviews_reviewer ON reviews (reviewer_address);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewee ON reviews (reviewee_address);

CREATE INDEX IF NOT EXISTS idx_reviews_sort_by_updated ON reviews (updated DESC);
CREATE INDEX IF NOT EXISTS idx_review_reviewer_sorted ON reviews (reviewer_address, updated DESC);
CREATE INDEX IF NOT EXISTS idx_review_reviewee_sorted ON reviews (reviewee_address, updated DESC);
CREATE INDEX IF NOT EXISTS idx_review_reviewer_and_reviewee_sorted ON reviews (reviewer_address, reviewee_address, updated DESC);

UPDATE database_version SET version_number = 0;

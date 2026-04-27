from datetime import datetime, timezone

from backend.app.routes.marketplace import _listing_from_row


def test_listing_from_row_accepts_datetime_values_for_timestamp_fields():
    now = datetime(2026, 4, 27, 5, 0, 0, tzinfo=timezone.utc)
    row = {
        "listing_id": "lst_test123",
        "creator_user_id": "usr_123",
        "title": "Test Listing",
        "description": "desc",
        "category": "Research",
        "pricing_model": "free",
        "price_amount": 0,
        "price_token": "ASND",
        "status": "published",
        "tags_json": '["alpha", "beta"]',
        "created_at": now,
        "updated_at": now,
        "published_at": now,
    }

    listing = _listing_from_row(row)

    assert listing.created_at == now.isoformat()
    assert listing.updated_at == now.isoformat()
    assert listing.published_at == now.isoformat()
    assert listing.tags == ["alpha", "beta"]


def test_listing_from_row_handles_invalid_tags_json_gracefully():
    row = {
        "listing_id": "lst_test124",
        "creator_user_id": "usr_124",
        "title": "Broken Tags",
        "description": "desc",
        "category": "Research",
        "pricing_model": "free",
        "price_amount": 0,
        "price_token": "ASND",
        "status": "published",
        "tags_json": '{bad json',
        "created_at": "2026-04-27T05:00:00+00:00",
        "updated_at": "2026-04-27T05:00:00+00:00",
        "published_at": "2026-04-27T05:00:00+00:00",
    }

    listing = _listing_from_row(row)

    assert listing.tags == []

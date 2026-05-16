import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Ensure the API package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Flask test client
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create a Flask test app with mocked DB connection."""
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
    from route.route_properties import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client for making requests without a running server."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Mock database cursor / connection
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_conn():
    """A mock psycopg connection + cursor pair."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# Sample API response factories
# ---------------------------------------------------------------------------

@pytest.fixture
def carto_response_factory():
    """Factory to build mock Carto API JSON responses."""
    def _make(rows, total_count=None):
        return {
            "rows": rows,
            "time": 0.01,
            "fields": {},
            "total_rows": total_count or len(rows),
        }
    return _make


@pytest.fixture
def sample_tax_record():
    """A single raw tax delinquency record as returned by the Carto API."""
    return {
        "opa_number": "88888801",
        "owner": "TEST OWNER",
        "street_address": "100 TEST ST",
        "zip_code": "19104",
        "principal_due": "1000.00",
        "penalty_due": "200.00",
        "interest_due": "150.00",
        "other_charges_due": "50.00",
        "total_due": "1400.00",
        "num_years_owed": "3",
        "most_recent_year_owed": "2024",
        "oldest_year_owed": "2022",
        "most_recent_payment_date": "2023-06-15T04:00:00Z",
        "is_actionable": "true",
        "payment_agreement": "false",
        "sheriff_sale": "N",
        "bankruptcy": "false",
        "building_category": "residential",
    }


@pytest.fixture
def sample_crime_record():
    """A single raw crime incident record as returned by the Carto API."""
    return {
        "dc_key": "202512345678",
        "dc_dist": "18",
        "psa": "3",
        "dispatch_date_time": "2025-04-10T14:30:00Z",
        "dispatch_date": "2025-04-10",
        "dispatch_time": "14:30:00",
        "ucr_general": "600",
        "text_general_code": "Thefts",
        "location_block": "3400 BLOCK WALNUT ST",
        "lat": 39.9523,
        "lng": -75.1914,
    }


@pytest.fixture
def sample_property_intelligence_row():
    """A mock row from the property_intelligence table (as returned by cursor.fetchone)."""
    return (
        "88888801",          # opa_account_num
        "100 TEST ST",       # address
        "TEST OWNER",        # owner_name
        "LOCAL",             # landlord_locality
        2,                   # violation_count
        1,                   # open_violation_count
        3,                   # permit_count
        True,                # has_rental_license
        True,                # rental_license_active
        False,               # is_owner_occupied
        30,                  # property_age
        "B",                 # exterior_condition
        "B",                 # interior_condition
        3,                   # bedrooms
        1,                   # bathrooms
        None,                # livable_area
        True,                # has_central_air
        False,               # has_tax_delinquency
        0,                   # tax_total_due
        0,                   # tax_num_years_owed
        False,               # tax_sheriff_sale
        5,                   # nearby_crime_count
        0,                   # nearby_violent_crime_count
        75,                  # safety_score
        87,                  # maintenance_score
        100,                 # landlord_score
        84,                  # trustability_score
        "LOW",               # risk_level
        [],                  # risk_flags
        [],                  # student_warnings
        "2025-05-15T00:00:00+00:00",  # updated_at
    )

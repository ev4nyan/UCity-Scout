"""Tests for the property details API endpoint."""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestGetPropertyDetails:
    """GET /api/property/<opa_account_num>"""

    @patch("route.route_properties.get_db_connection")
    def test_returns_property_when_found(self, mock_get_conn, client, sample_property_intelligence_row):
        """Should return 200 with property JSON when OPA number exists."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = sample_property_intelligence_row
        mock_cursor.description = [
            ("opa_account_num",), ("address",), ("owner_name",),
            ("landlord_locality",), ("violation_count",), ("open_violation_count",),
            ("permit_count",), ("has_rental_license",), ("rental_license_active",),
            ("is_owner_occupied",), ("property_age",), ("exterior_condition",),
            ("interior_condition",), ("bedrooms",), ("bathrooms",),
            ("livable_area",), ("has_central_air",),
            ("has_tax_delinquency",), ("tax_total_due",),
            ("tax_num_years_owed",), ("tax_sheriff_sale",),
            ("nearby_crime_count",), ("nearby_violent_crime_count",),
            ("safety_score",), ("maintenance_score",),
            ("landlord_score",), ("trustability_score",),
            ("risk_level",), ("risk_flags",), ("student_warnings",),
            ("updated_at",),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        response = client.get("/api/property/88888801")
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data["opa_account_num"] == "88888801"
        assert data["address"] == "100 TEST ST"
        assert data["safety_score"] == 75
        assert data["risk_level"] == "LOW"

    @patch("route.route_properties.get_db_connection")
    def test_returns_404_when_not_found(self, mock_get_conn, client):
        """Should return 404 when property OPA number doesn't exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        response = client.get("/api/property/00000000")
        data = json.loads(response.data)

        assert response.status_code == 404
        assert "error" in data

    @patch("route.route_properties.get_db_connection")
    def test_returns_500_on_db_error(self, mock_get_conn, client):
        """Should return 500 when the database connection fails."""
        mock_get_conn.side_effect = Exception("Connection refused")

        response = client.get("/api/property/88888801")
        data = json.loads(response.data)

        assert response.status_code == 500
        assert "error" in data

    @patch("route.route_properties.get_db_connection")
    def test_query_uses_parameterized_input(self, mock_get_conn, client):
        """Should use parameterized query, not string interpolation (SQL injection safety)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        client.get("/api/property/'; DROP TABLE property_intelligence;--")

        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        # Query should use %s placeholder, not interpolated value
        assert "%s" in query
        assert "'; DROP TABLE" not in query
        assert params == ("'; DROP TABLE property_intelligence;--",)


class TestSearchPropertiesByAddress:
    """GET /api/properties/search?q=<address>"""

    SEARCH_COLUMNS = [
        ("opa_account_num",), ("address",), ("owner_name",),
        ("bedrooms",), ("bathrooms",), ("livable_area",),
        ("risk_level",), ("trustability_score",),
    ]

    @patch("route.route_properties.get_db_connection")
    def test_returns_matching_properties(self, mock_get_conn, client):
        """Should return 200 with a list of matching properties."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("88888801", "100 TEST ST", "TEST OWNER", 3, 1, None, "LOW", 84),
            ("88888802", "200 TEST ST", "OWNER TWO", 2, 1, 900, "MEDIUM", 60),
        ]
        mock_cursor.description = self.SEARCH_COLUMNS

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        response = client.get("/api/properties/search?q=test st")
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data["count"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["address"] == "100 TEST ST"
        assert data["results"][1]["opa_account_num"] == "88888802"

    @patch("route.route_properties.get_db_connection")
    def test_returns_empty_list_when_no_match(self, mock_get_conn, client):
        """Should return 200 with empty results when no address matches."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        response = client.get("/api/properties/search?q=nonexistent blvd")
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data["count"] == 0
        assert data["results"] == []

    def test_returns_400_when_q_missing(self, client):
        """Should return 400 when the 'q' query parameter is absent."""
        response = client.get("/api/properties/search")
        data = json.loads(response.data)

        assert response.status_code == 400
        assert "error" in data

    def test_returns_400_when_q_too_short(self, client):
        """Should return 400 when query is under 3 characters."""
        response = client.get("/api/properties/search?q=ab")
        data = json.loads(response.data)

        assert response.status_code == 400
        assert "error" in data

    @patch("route.route_properties.get_db_connection")
    def test_returns_500_on_db_error(self, mock_get_conn, client):
        """Should return 500 when the database blows up."""
        mock_get_conn.side_effect = Exception("Connection refused")

        response = client.get("/api/properties/search?q=market st")
        data = json.loads(response.data)

        assert response.status_code == 500
        assert "error" in data

    @patch("route.route_properties.get_db_connection")
    def test_query_uses_ilike_with_parameterized_input(self, mock_get_conn, client):
        """Should use ILIKE with %s placeholder for SQL injection safety."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        client.get("/api/properties/search?q='; DROP TABLE property_intelligence;--")

        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]

        assert "ILIKE" in query
        assert "%s" in query
        assert "'; DROP TABLE" not in query
        assert params == ("%'; DROP TABLE property_intelligence;--%",)

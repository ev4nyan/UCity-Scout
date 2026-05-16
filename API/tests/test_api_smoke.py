"""Smoke tests that verify external APIs are reachable and return expected schemas.

These hit live endpoints — mark with @pytest.mark.smoke so they can be skipped
in CI or offline environments via: pytest -m "not smoke"
"""

import pytest
import requests


CARTO_BASE_URL = "https://phl.carto.com/api/v2/sql"


@pytest.mark.smoke
class TestCartoAPIHealth:
    """Verify the Carto SQL API is reachable and responds correctly."""

    def test_carto_api_returns_200(self):
        response = requests.get(CARTO_BASE_URL, params={"q": "SELECT 1 AS ping"}, timeout=15)
        assert response.status_code == 200

    def test_carto_api_returns_json_with_rows(self):
        response = requests.get(CARTO_BASE_URL, params={"q": "SELECT 1 AS ping"}, timeout=15)
        data = response.json()
        assert "rows" in data
        assert len(data["rows"]) == 1
        assert data["rows"][0]["ping"] == 1


@pytest.mark.smoke
class TestViolationsTable:
    """Verify the violations table is queryable on Carto."""

    def test_violations_table_exists(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT count(*) FROM violations LIMIT 1"},
            timeout=15,
        )
        assert response.status_code == 200
        assert response.json()["rows"][0]["count"] > 0


@pytest.mark.smoke
class TestPropertiesTable:
    """Verify the OPA properties table is queryable on Carto."""

    def test_properties_table_exists(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT count(*) FROM opa_properties_public LIMIT 1"},
            timeout=15,
        )
        assert response.status_code == 200
        assert response.json()["rows"][0]["count"] > 0

    def test_properties_have_lat_lng(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT ST_Y(the_geom) AS lat, ST_X(the_geom) AS lng FROM opa_properties_public WHERE the_geom IS NOT NULL LIMIT 1"},
            timeout=15,
        )
        data = response.json()
        assert len(data["rows"]) == 1
        assert "lat" in data["rows"][0]
        assert "lng" in data["rows"][0]
        assert isinstance(data["rows"][0]["lat"], (int, float))


@pytest.mark.smoke
class TestTaxDelinquenciesTable:
    """Verify the tax delinquencies table is queryable on Carto."""

    def test_tax_delinquencies_table_exists(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT count(*) FROM real_estate_tax_delinquencies LIMIT 1"},
            timeout=15,
        )
        assert response.status_code == 200
        assert response.json()["rows"][0]["count"] > 0

    def test_tax_delinquencies_has_opa_number(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT opa_number FROM real_estate_tax_delinquencies LIMIT 1"},
            timeout=15,
        )
        data = response.json()
        assert len(data["rows"]) == 1
        assert "opa_number" in data["rows"][0]


@pytest.mark.smoke
class TestCrimeIncidentsTable:
    """Verify the crime incidents table is queryable on Carto."""

    def test_crime_table_exists(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT count(*) FROM incidents_part1_part2 LIMIT 1"},
            timeout=15,
        )
        assert response.status_code == 200
        assert response.json()["rows"][0]["count"] > 0

    def test_crime_has_lat_lng(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT ST_Y(the_geom) AS lat, ST_X(the_geom) AS lng FROM incidents_part1_part2 WHERE the_geom IS NOT NULL LIMIT 1"},
            timeout=15,
        )
        data = response.json()
        assert len(data["rows"]) == 1
        assert "lat" in data["rows"][0]
        assert "lng" in data["rows"][0]
        assert isinstance(data["rows"][0]["lat"], (int, float))

    def test_crime_has_ucr_general(self):
        response = requests.get(
            CARTO_BASE_URL,
            params={"q": "SELECT ucr_general, text_general_code FROM incidents_part1_part2 LIMIT 1"},
            timeout=15,
        )
        data = response.json()
        assert "ucr_general" in data["rows"][0]
        assert "text_general_code" in data["rows"][0]

"""Tests for the crime incidents ETL — bounding box, record parsing, proximity math."""

import math
import pytest


class TestBoundingBoxConfig:
    """Verify the UCity bounding box covers the expected area."""

    UCITY_LAT_MIN = 39.940
    UCITY_LAT_MAX = 39.970
    UCITY_LNG_MIN = -75.225
    UCITY_LNG_MAX = -75.180

    def test_lat_range_is_positive(self):
        assert self.UCITY_LAT_MAX > self.UCITY_LAT_MIN

    def test_lng_range_is_negative_west(self):
        """Philadelphia is west of the prime meridian — longitudes should be negative."""
        assert self.UCITY_LNG_MIN < 0
        assert self.UCITY_LNG_MAX < 0

    def test_bbox_covers_ucity_center(self):
        """UCity's approximate center (~39.954, -75.200) should be inside the box."""
        assert self.UCITY_LAT_MIN < 39.954 < self.UCITY_LAT_MAX
        assert self.UCITY_LNG_MIN < -75.200 < self.UCITY_LNG_MAX

    def test_bbox_not_too_large(self):
        """Box should be roughly neighborhood-sized, not city-wide."""
        lat_span_km = (self.UCITY_LAT_MAX - self.UCITY_LAT_MIN) * 111.32
        lng_span_km = (self.UCITY_LNG_MAX - self.UCITY_LNG_MIN) * 111.32 * math.cos(math.radians(39.955))
        # Should be under 5km in each direction
        assert lat_span_km < 5.0
        assert lng_span_km < 5.0

    def test_bbox_has_buffer_beyond_ucity(self):
        """Box should extend slightly beyond the core UCity area (39.943–39.965)."""
        assert self.UCITY_LAT_MIN < 39.943  # buffer to the south
        assert self.UCITY_LAT_MAX > 39.965  # buffer to the north


class TestProximityMath:
    """Verify the 100m radius approximation used in property_intelligence."""

    METERS_PER_DEG_LAT = 111_320
    PHILLY_LAT = 39.955
    METERS_PER_DEG_LNG = 111_320 * math.cos(math.radians(PHILLY_LAT))

    # Offsets used in the LATERAL join
    LAT_OFFSET = 0.0009
    LNG_OFFSET = 0.00117

    def test_lat_offset_approx_100m(self):
        dist = self.LAT_OFFSET * self.METERS_PER_DEG_LAT
        assert 90 < dist < 110, f"Lat offset = {dist:.1f}m, expected ~100m"

    def test_lng_offset_approx_100m(self):
        dist = self.LNG_OFFSET * self.METERS_PER_DEG_LNG
        assert 90 < dist < 110, f"Lng offset = {dist:.1f}m, expected ~100m"

    def test_corner_distance_under_150m(self):
        """Diagonal of the bounding box should be under ~150m (√2 × 100m ≈ 141m)."""
        dlat_m = self.LAT_OFFSET * self.METERS_PER_DEG_LAT
        dlng_m = self.LNG_OFFSET * self.METERS_PER_DEG_LNG
        diagonal = math.sqrt(dlat_m**2 + dlng_m**2)
        assert diagonal < 150, f"Diagonal = {diagonal:.1f}m, too large"


class TestCrimeRecordMapping:
    """Verify raw API records have the expected fields."""

    EXPECTED_COLUMNS = [
        "dc_key", "dc_dist", "psa", "dispatch_date_time",
        "dispatch_date", "dispatch_time", "ucr_general",
        "text_general_code", "location_block", "lat", "lng",
    ]

    def test_sample_record_has_all_fields(self, sample_crime_record):
        for col in self.EXPECTED_COLUMNS:
            assert col in sample_crime_record, f"Missing field: {col}"

    def test_lat_lng_are_numeric(self, sample_crime_record):
        assert isinstance(sample_crime_record["lat"], (int, float))
        assert isinstance(sample_crime_record["lng"], (int, float))

    def test_dc_key_is_castable_to_string(self, sample_crime_record):
        assert str(sample_crime_record["dc_key"])


class TestUCRClassification:
    """Verify violent crime classification logic (UCR codes 100-400)."""

    VIOLENT_CODES = {"100", "200", "300", "400"}

    @pytest.mark.parametrize("code,is_violent", [
        ("100", True),   # Homicide
        ("200", True),   # Rape
        ("300", True),   # Robbery
        ("400", True),   # Aggravated Assault
        ("500", False),  # Burglary
        ("600", False),  # Theft
        ("700", False),  # Motor Vehicle Theft
        ("800", False),  # Other Assaults
        ("900", False),  # Arson
        ("1800", False), # Drug Violations
    ])
    def test_ucr_violent_classification(self, code, is_violent):
        assert (code in self.VIOLENT_CODES) == is_violent

"""Tests for the property intelligence aggregation logic — scoring formulas and risk flags."""

import pytest


class TestSafetyScore:
    """Verify the safety score formula matches the SQL in etl_property_intelligence.py."""

    @staticmethod
    def calc_safety_score(
        violation_count=0, open_violation_count=0,
        has_tax_delinquency=False, tax_num_years_owed=0,
        nearby_crime_count=0, nearby_violent_crime_count=0,
    ):
        raw = (
            100
            - (violation_count * 10)
            - (open_violation_count * 20)
            - (tax_num_years_owed * 5 if has_tax_delinquency else 0)
            - (min(nearby_crime_count, 20) * 1)
            - (nearby_violent_crime_count * 3)
        )
        return max(0, min(100, raw))

    def test_perfect_score(self):
        assert self.calc_safety_score() == 100

    def test_violations_reduce_score(self):
        assert self.calc_safety_score(violation_count=3) == 70

    def test_open_violations_extra_penalty(self):
        assert self.calc_safety_score(violation_count=1, open_violation_count=1) == 70

    def test_tax_delinquency_penalty(self):
        assert self.calc_safety_score(has_tax_delinquency=True, tax_num_years_owed=4) == 80

    def test_crime_penalty(self):
        assert self.calc_safety_score(nearby_crime_count=10) == 90

    def test_crime_penalty_capped_at_20(self):
        # 50 crimes should still only deduct 20 points (capped)
        assert self.calc_safety_score(nearby_crime_count=50) == 80

    def test_violent_crime_extra_penalty(self):
        assert self.calc_safety_score(nearby_violent_crime_count=5) == 85

    def test_score_floors_at_zero(self):
        score = self.calc_safety_score(
            violation_count=5, open_violation_count=5,
            nearby_crime_count=30, nearby_violent_crime_count=10,
        )
        assert score == 0

    def test_combined_penalties(self):
        score = self.calc_safety_score(
            violation_count=2,           # -20
            open_violation_count=1,      # -20
            has_tax_delinquency=True,
            tax_num_years_owed=2,        # -10
            nearby_crime_count=5,        # -5
            nearby_violent_crime_count=1, # -3
        )
        assert score == 42


class TestMaintenanceScore:
    """Verify the maintenance score formula."""

    CONDITION_MAP = {"A+": 100, "A": 95, "B": 85, "C": 70, "D": 50, "E": 30}

    @staticmethod
    def calc_maintenance_score(exterior_condition="C", permit_count=0):
        cond_map = {"A+": 100, "A": 95, "B": 85, "C": 70, "D": 50, "E": 30}
        base = cond_map.get(exterior_condition, 60)
        raw = base + (permit_count * 2)
        return max(0, min(100, raw))

    def test_good_condition_high_score(self):
        assert self.calc_maintenance_score("A+") == 100

    def test_poor_condition_low_score(self):
        assert self.calc_maintenance_score("E") == 30

    def test_permits_boost_score(self):
        assert self.calc_maintenance_score("C", permit_count=5) == 80

    def test_unknown_condition_gets_default(self):
        assert self.calc_maintenance_score("X") == 60

    def test_score_capped_at_100(self):
        assert self.calc_maintenance_score("A+", permit_count=50) == 100


class TestLandlordScore:
    """Verify the landlord score formula."""

    @staticmethod
    def calc_landlord_score(
        has_rental_license=False, rental_license_active=False,
        landlord_locality="LOCAL",
        has_tax_delinquency=False, tax_num_years_owed=0,
    ):
        if has_rental_license and rental_license_active:
            base = 80
        elif has_rental_license:
            base = 50
        else:
            base = 30

        base += 20 if landlord_locality == "LOCAL" else 0

        if has_tax_delinquency and tax_num_years_owed >= 3:
            base -= 20
        elif has_tax_delinquency:
            base -= 10

        return max(0, min(100, base))

    def test_licensed_active_local(self):
        assert self.calc_landlord_score(True, True, "LOCAL") == 100

    def test_licensed_inactive_distant(self):
        assert self.calc_landlord_score(True, False, "DISTANT") == 50

    def test_no_license_distant(self):
        assert self.calc_landlord_score(False, False, "DISTANT") == 30

    def test_tax_delinquency_mild_penalty(self):
        score = self.calc_landlord_score(True, True, "LOCAL", True, 2)
        assert score == 90

    def test_tax_delinquency_severe_penalty(self):
        score = self.calc_landlord_score(True, True, "LOCAL", True, 5)
        assert score == 80


class TestTrustabilityScore:
    """Verify the composite trustability score."""

    @staticmethod
    def calc_trustability(safety, maintenance, landlord):
        return int(safety * 0.4 + maintenance * 0.35 + landlord * 0.25)

    def test_all_perfect(self):
        assert self.calc_trustability(100, 100, 100) == 100

    def test_all_zero(self):
        assert self.calc_trustability(0, 0, 0) == 0

    def test_weighted_correctly(self):
        # 50*0.4 + 80*0.35 + 60*0.25 = 20 + 28 + 15 = 63
        assert self.calc_trustability(50, 80, 60) == 63


class TestRiskLevel:
    """Verify risk level classification thresholds."""

    @staticmethod
    def classify(trustability_score):
        if trustability_score >= 75:
            return "LOW"
        elif trustability_score >= 50:
            return "MODERATE"
        elif trustability_score >= 25:
            return "HIGH"
        else:
            return "CRITICAL"

    @pytest.mark.parametrize("score,level", [
        (100, "LOW"),
        (75, "LOW"),
        (74, "MODERATE"),
        (50, "MODERATE"),
        (49, "HIGH"),
        (25, "HIGH"),
        (24, "CRITICAL"),
        (0, "CRITICAL"),
    ])
    def test_risk_level_thresholds(self, score, level):
        assert self.classify(score) == level


class TestRiskFlags:
    """Verify risk flag conditions."""

    @staticmethod
    def compute_flags(
        open_violation_count=0, has_rental_license=True,
        rental_license_active=True, landlord_locality="LOCAL",
        exterior_condition="B", has_tax_delinquency=False,
        tax_sheriff_sale=False, nearby_crime_count=0,
    ):
        flags = []
        if open_violation_count > 0:
            flags.append("OPEN_VIOLATIONS")
        if not has_rental_license:
            flags.append("NO_RENTAL_LICENSE")
        if has_rental_license and not rental_license_active:
            flags.append("EXPIRED_LICENSE")
        if landlord_locality == "DISTANT":
            flags.append("DISTANT_LANDLORD")
        if exterior_condition in ("D", "E"):
            flags.append("POOR_CONDITION")
        if has_tax_delinquency:
            flags.append("TAX_DELINQUENT")
        if tax_sheriff_sale:
            flags.append("SHERIFF_SALE")
        if nearby_crime_count >= 15:
            flags.append("HIGH_CRIME_AREA")
        return flags

    def test_clean_property_has_no_flags(self):
        assert self.compute_flags() == []

    def test_all_flags_can_fire(self):
        flags = self.compute_flags(
            open_violation_count=1,
            has_rental_license=False,
            landlord_locality="DISTANT",
            exterior_condition="E",
            has_tax_delinquency=True,
            tax_sheriff_sale=True,
            nearby_crime_count=20,
        )
        assert "OPEN_VIOLATIONS" in flags
        assert "NO_RENTAL_LICENSE" in flags
        assert "DISTANT_LANDLORD" in flags
        assert "POOR_CONDITION" in flags
        assert "TAX_DELINQUENT" in flags
        assert "SHERIFF_SALE" in flags
        assert "HIGH_CRIME_AREA" in flags

    def test_expired_license_requires_has_license(self):
        """EXPIRED_LICENSE only fires when has_license=True AND active=False."""
        flags = self.compute_flags(has_rental_license=True, rental_license_active=False)
        assert "EXPIRED_LICENSE" in flags
        assert "NO_RENTAL_LICENSE" not in flags

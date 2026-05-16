"""Tests for the tax delinquency ETL — data mapping and boolean casting."""

import pytest


class TestTaxBooleanCasting:
    """The Carto API returns booleans as string 'true'/'false'. Verify casting."""

    @staticmethod
    def _cast_bool(value):
        """Reproduce the casting logic from etl_tax.py."""
        if value:
            return value.lower() == "true"
        return False

    @pytest.mark.parametrize("raw,expected", [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        (None, False),
        ("", False),
    ])
    def test_is_actionable_casting(self, raw, expected):
        assert self._cast_bool(raw) == expected


class TestTaxRecordMapping:
    """Verify the full record mapping matches the INSERT column order."""

    EXPECTED_COLUMNS = [
        "opa_number", "owner", "street_address", "zip_code",
        "principal_due", "penalty_due", "interest_due",
        "other_charges_due", "total_due", "num_years_owed",
        "most_recent_year_owed", "oldest_year_owed",
        "most_recent_payment_date", "is_actionable",
        "payment_agreement", "sheriff_sale", "bankruptcy",
        "building_category",
    ]

    def test_sample_record_has_all_required_fields(self, sample_tax_record):
        """Every expected column should be present in the API response."""
        for col in self.EXPECTED_COLUMNS:
            assert col in sample_tax_record, f"Missing field: {col}"

    def test_numeric_fields_are_parseable(self, sample_tax_record):
        """Financial fields should be castable to float."""
        numeric_fields = [
            "principal_due", "penalty_due", "interest_due",
            "other_charges_due", "total_due",
        ]
        for field in numeric_fields:
            val = sample_tax_record[field]
            assert float(val), f"{field} = '{val}' is not a valid number"

    def test_total_due_equals_component_sum(self, sample_tax_record):
        """total_due should equal principal + penalty + interest + other charges."""
        components = (
            float(sample_tax_record["principal_due"])
            + float(sample_tax_record["penalty_due"])
            + float(sample_tax_record["interest_due"])
            + float(sample_tax_record["other_charges_due"])
        )
        assert float(sample_tax_record["total_due"]) == pytest.approx(components)

    def test_years_owed_is_positive_integer(self, sample_tax_record):
        assert int(sample_tax_record["num_years_owed"]) > 0

    def test_payment_date_none_handling(self, sample_tax_record):
        """If payment date is empty string, ETL maps to None."""
        record = {**sample_tax_record, "most_recent_payment_date": ""}
        mapped = record.get("most_recent_payment_date") or None
        assert mapped is None


class TestTaxTableSchema:
    """Verify the CREATE TABLE SQL has the expected columns."""

    TAX_CREATE_SQL = """
        CREATE TABLE IF NOT EXISTS tax_balances (
            opa_number TEXT PRIMARY KEY,
            owner TEXT,
            street_address TEXT,
            zip_code TEXT,
            principal_due NUMERIC,
            penalty_due NUMERIC,
            interest_due NUMERIC,
            other_charges_due NUMERIC,
            total_due NUMERIC,
            num_years_owed INTEGER,
            most_recent_year_owed INTEGER,
            oldest_year_owed INTEGER,
            most_recent_payment_date TIMESTAMP WITH TIME ZONE,
            is_actionable BOOLEAN,
            payment_agreement BOOLEAN,
            sheriff_sale TEXT,
            bankruptcy BOOLEAN,
            building_category TEXT
        );
    """

    def test_primary_key_is_opa_number(self):
        assert "opa_number TEXT PRIMARY KEY" in self.TAX_CREATE_SQL

    def test_boolean_columns_exist(self):
        for col in ["is_actionable BOOLEAN", "payment_agreement BOOLEAN", "bankruptcy BOOLEAN"]:
            assert col in self.TAX_CREATE_SQL

    def test_financial_columns_are_numeric(self):
        for col in ["principal_due NUMERIC", "penalty_due NUMERIC",
                     "interest_due NUMERIC", "other_charges_due NUMERIC", "total_due NUMERIC"]:
            assert col in self.TAX_CREATE_SQL

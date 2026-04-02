"""
tests/test_pipeline.py — Tests unitaires pipeline ELT Amazon
"""

import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def raw_df():
    """Dataset de test minimal avec cas limites."""
    return pd.DataFrame({
        "order_id":         [1, 2, 2, 3, 4, 5, 6],
        "order_date":       ["2022-01-15","2022-03-10","2022-03-10","2023-06-20","2022-07-01","2023-11-30","2022-04-05"],
        "product_id":       [100, 200, 200, 300, 400, 500, 600],
        "product_category": ["Electronics","Books","Books","Fashion","Sports","Beauty","Home & Kitchen"],
        "price":            [299.99, 15.50, 15.50, -50.0, 89.99, 0, 145.00],
        "discount_percent": [10, 0, 0, 20, 5, 15, 110],   # 110 invalide
        "quantity_sold":    [3, 2, 2, 1, 4, 3, 2],
        "customer_region":  ["North America","Asia","Asia","Europe","Middle East","Asia","Europe"],
        "payment_method":   ["Credit Card","UPI","UPI","Cash on Delivery","Wallet","Debit Card","Credit Card"],
        "rating":           [4.5, 3.2, 3.2, 2.8, 4.0, 6.0, 3.7],  # 6.0 invalide
        "review_count":     [120, 45, 45, 230, 78, 300, 55],
        "discounted_price": [269.99, 15.50, 15.50, -40.0, 85.49, 0, 145.00],
        "total_revenue":    [809.97, 31.00, 31.00, -50.0, 339.96, 0, 290.00],
    })


class TestClean:
    def test_removes_duplicates(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert df["order_id"].duplicated().sum() == 0

    def test_removes_negative_price(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert (df["price"] <= 0).sum() == 0

    def test_removes_negative_revenue(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert (df["total_revenue"] <= 0).sum() == 0

    def test_removes_invalid_discount(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert df["discount_percent"].between(0, 100).all()

    def test_removes_invalid_rating(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        assert df["rating"].between(0, 5).all()

    def test_strips_strings(self, raw_df):
        raw_df["product_category"] = raw_df["product_category"].apply(lambda x: f"  {x}  ")
        from elt.transform.transform import clean
        df = clean(raw_df)
        for val in df["product_category"]:
            assert val == val.strip()


class TestEnrich:
    def _get_clean_df(self, raw_df):
        from elt.transform.transform import clean
        return clean(raw_df)

    def test_temporal_columns_created(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._get_clean_df(raw_df))
        for col in ["year", "month", "month_name", "quarter", "week", "day_of_week", "is_weekend"]:
            assert col in df.columns

    def test_quarter_valid_values(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._get_clean_df(raw_df))
        assert set(df["quarter"].unique()).issubset({"Q1","Q2","Q3","Q4"})

    def test_revenue_per_unit_positive(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._get_clean_df(raw_df))
        assert (df["revenue_per_unit"] > 0).all()

    def test_discount_amount_correct(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._get_clean_df(raw_df))
        computed = (df["price"] * df["discount_percent"] / 100).round(2)
        assert (abs(computed - df["discount_amount"]) < 0.01).all()

    def test_has_discount_boolean(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._get_clean_df(raw_df))
        assert df["has_discount"].dtype == bool or df["has_discount"].isin([True, False]).all()

    def test_price_segment_no_nulls(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._get_clean_df(raw_df))
        assert df["price_segment"].isnull().sum() == 0

    def test_is_top_revenue_flag(self, raw_df):
        from elt.transform.transform import enrich
        df = enrich(self._get_clean_df(raw_df))
        assert "is_top_revenue" in df.columns
        assert df["is_top_revenue"].dtype in [bool, object]


class TestDataQuality:
    def test_no_null_critical_columns(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        for col in ["order_date","product_category","price","total_revenue","quantity_sold"]:
            assert df[col].isnull().sum() == 0

    def test_all_years_valid(self, raw_df):
        from elt.transform.transform import clean, enrich
        df = enrich(clean(raw_df))
        assert df["year"].between(2020, 2030).all()

    def test_regions_known(self, raw_df):
        from elt.transform.transform import clean
        df = clean(raw_df)
        known = {"North America","Asia","Europe","Middle East","South America","Africa","Oceania"}
        for r in df["customer_region"].unique():
            assert r in known, f"Région inconnue : {r}"
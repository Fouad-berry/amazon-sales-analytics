"""
ELT — LOAD (DATA MARTS)
Construction des tables agrégées orientées Power BI.
Architecture en couches : staging → intermediate → marts.
"""

import pandas as pd
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LOAD] %(message)s")
log = logging.getLogger(__name__)

DB_PATH  = Path("data/amazon_analytics.db")
MART_DIR = Path("data/mart")


def load_processed() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM processed_orders", conn)
    conn.close()
    df["order_date"] = pd.to_datetime(df["order_date"])
    log.info(f"{len(df):,} lignes chargées depuis processed_orders")
    return df


def save(df: pd.DataFrame, name: str, conn: sqlite3.Connection) -> None:
    df.to_sql(name, conn, if_exists="replace", index=False)
    df.to_csv(MART_DIR / f"{name}.csv", index=False)
    log.info(f"  ✓ {name} : {len(df):,} lignes")


# ══════════════════════════════════════════════════════════════
# STAGING — tables proches du source, légèrement nettoyées
# ══════════════════════════════════════════════════════════════

def build_staging(df: pd.DataFrame, conn: sqlite3.Connection):
    log.info("--- STAGING ---")

    # stg_orders : table de base enrichie
    stg = df[[
        "order_id","order_date","year","month","month_name","quarter","week",
        "day_of_week","is_weekend","product_id","product_category",
        "price","discount_percent","discount_amount","has_discount",
        "discounted_price","effective_margin","quantity_sold",
        "total_revenue","revenue_per_unit",
        "customer_region","payment_method","rating","review_count",
        "price_segment","discount_segment","rating_segment","volume_segment",
        "is_top_revenue","is_high_rating",
    ]].copy()
    save(stg, "stg_orders", conn)


# ══════════════════════════════════════════════════════════════
# INTERMEDIATE — agrégations intermédiaires réutilisables
# ══════════════════════════════════════════════════════════════

def build_intermediate(df: pd.DataFrame, conn: sqlite3.Connection):
    log.info("--- INTERMEDIATE ---")

    # int_orders_by_product : revenue agrégé par produit
    int_prod = (
        df.groupby(["product_id", "product_category"])
        .agg(
            total_revenue   =("total_revenue", "sum"),
            total_units     =("quantity_sold", "sum"),
            nb_orders       =("order_id", "count"),
            avg_price       =("price", "mean"),
            avg_discount    =("discount_percent", "mean"),
            avg_rating      =("rating", "mean"),
            avg_review_count=("review_count", "mean"),
        )
        .round(2)
        .reset_index()
    )
    save(int_prod, "int_orders_by_product", conn)

    # int_daily_sales : agrégation journalière
    int_daily = (
        df.groupby("order_date")
        .agg(
            nb_orders     =("order_id", "count"),
            total_revenue =("total_revenue", "sum"),
            total_units   =("quantity_sold", "sum"),
            avg_price     =("price", "mean"),
            avg_discount  =("discount_percent", "mean"),
            avg_rating    =("rating", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("order_date")
    )
    int_daily["revenue_cumsum"] = int_daily["total_revenue"].cumsum().round(2)
    save(int_daily, "int_daily_sales", conn)


# ══════════════════════════════════════════════════════════════
# MARTS — tables finales prêtes pour Power BI
# ══════════════════════════════════════════════════════════════

def build_marts(df: pd.DataFrame, conn: sqlite3.Connection):
    log.info("--- MARTS ---")

    # ── mart_kpis : KPIs globaux ────────────────────────────────────────
    kpis = pd.DataFrame([{
        "total_revenue"         : round(df["total_revenue"].sum(), 2),
        "total_orders"          : len(df),
        "total_units_sold"      : int(df["quantity_sold"].sum()),
        "avg_order_value"       : round(df["total_revenue"].mean(), 2),
        "avg_price"             : round(df["price"].mean(), 2),
        "avg_discount_pct"      : round(df["discount_percent"].mean(), 2),
        "avg_rating"            : round(df["rating"].mean(), 2),
        "pct_orders_discounted" : round((df["has_discount"].sum() / len(df)) * 100, 2),
        "max_order_revenue"     : round(df["total_revenue"].max(), 2),
        "unique_products"       : df["product_id"].nunique(),
        "unique_categories"     : df["product_category"].nunique(),
    }])
    save(kpis, "mart_kpis", conn)

    # ── mart_category : par catégorie ───────────────────────────────────
    cat = (
        df.groupby("product_category")
        .agg(
            total_revenue   =("total_revenue", "sum"),
            total_units     =("quantity_sold", "sum"),
            nb_orders       =("order_id", "count"),
            avg_price       =("price", "mean"),
            avg_discount    =("discount_percent", "mean"),
            avg_rating      =("rating", "mean"),
            avg_review_count=("review_count", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    cat["revenue_share_pct"] = (cat["total_revenue"] / cat["total_revenue"].sum() * 100).round(2)
    save(cat, "mart_category", conn)

    # ── mart_region : par région ─────────────────────────────────────────
    region = (
        df.groupby("customer_region")
        .agg(
            total_revenue=("total_revenue", "sum"),
            total_units  =("quantity_sold", "sum"),
            nb_orders    =("order_id", "count"),
            avg_price    =("price", "mean"),
            avg_discount =("discount_percent", "mean"),
            avg_rating   =("rating", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    region["revenue_share_pct"] = (region["total_revenue"] / region["total_revenue"].sum() * 100).round(2)
    save(region, "mart_region", conn)

    # ── mart_payment : par méthode de paiement ───────────────────────────
    pay = (
        df.groupby("payment_method")
        .agg(
            total_revenue=("total_revenue", "sum"),
            nb_orders    =("order_id", "count"),
            total_units  =("quantity_sold", "sum"),
            avg_order_val=("total_revenue", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    pay["revenue_share_pct"] = (pay["total_revenue"] / pay["total_revenue"].sum() * 100).round(2)
    save(pay, "mart_payment", conn)

    # ── mart_monthly_trend : tendance mensuelle ───────────────────────────
    monthly = (
        df.groupby(["year", "month", "month_name", "quarter"])
        .agg(
            total_revenue=("total_revenue", "sum"),
            nb_orders    =("order_id", "count"),
            total_units  =("quantity_sold", "sum"),
            avg_price    =("price", "mean"),
            avg_discount =("discount_percent", "mean"),
            avg_rating   =("rating", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values(["year", "month"])
    )
    monthly["revenue_cumsum"] = monthly["total_revenue"].cumsum().round(2)
    monthly["mom_growth_pct"] = monthly["total_revenue"].pct_change().mul(100).round(2)
    save(monthly, "mart_monthly_trend", conn)

    # ── mart_quarterly : par trimestre ───────────────────────────────────
    quarterly = (
        df.groupby(["year", "quarter"])
        .agg(
            total_revenue=("total_revenue", "sum"),
            nb_orders    =("order_id", "count"),
            total_units  =("quantity_sold", "sum"),
            avg_rating   =("rating", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values(["year", "quarter"])
    )
    quarterly["qoq_growth_pct"] = quarterly["total_revenue"].pct_change().mul(100).round(2)
    save(quarterly, "mart_quarterly", conn)

    # ── mart_category_region : croisement catégorie × région ─────────────
    cat_region = (
        df.groupby(["product_category", "customer_region"])
        .agg(
            total_revenue=("total_revenue", "sum"),
            nb_orders    =("order_id", "count"),
            avg_rating   =("rating", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    save(cat_region, "mart_category_region", conn)

    # ── mart_discount_analysis : impact discount ─────────────────────────
    disc = (
        df.groupby("discount_segment")
        .agg(
            total_revenue=("total_revenue", "sum"),
            nb_orders    =("order_id", "count"),
            avg_rating   =("rating", "mean"),
            avg_quantity =("quantity_sold", "mean"),
            total_units  =("quantity_sold", "sum"),
        )
        .round(2)
        .reset_index()
    )
    save(disc, "mart_discount_analysis", conn)

    # ── mart_rating_analysis : analyse satisfaction ───────────────────────
    rating = (
        df.groupby("rating_segment")
        .agg(
            total_revenue   =("total_revenue", "sum"),
            nb_orders       =("order_id", "count"),
            avg_review_count=("review_count", "mean"),
            avg_price       =("price", "mean"),
            avg_discount    =("discount_percent", "mean"),
        )
        .round(2)
        .reset_index()
    )
    save(rating, "mart_rating_analysis", conn)

    # ── mart_price_segment : segmentation prix ────────────────────────────
    price_seg = (
        df.groupby("price_segment")
        .agg(
            total_revenue=("total_revenue", "sum"),
            nb_orders    =("order_id", "count"),
            avg_rating   =("rating", "mean"),
            avg_discount =("discount_percent", "mean"),
            total_units  =("quantity_sold", "sum"),
        )
        .round(2)
        .reset_index()
    )
    save(price_seg, "mart_price_segment", conn)

    # ── mart_category_monthly : tendance par catégorie ────────────────────
    cat_monthly = (
        df.groupby(["product_category", "year", "month", "month_name"])
        .agg(
            total_revenue=("total_revenue", "sum"),
            nb_orders    =("order_id", "count"),
        )
        .round(2)
        .reset_index()
        .sort_values(["product_category", "year", "month"])
    )
    save(cat_monthly, "mart_category_monthly", conn)

    # ── mart_top_products : top 100 produits ─────────────────────────────
    top_prod = (
        df.groupby(["product_id", "product_category"])
        .agg(
            total_revenue   =("total_revenue", "sum"),
            nb_orders       =("order_id", "count"),
            total_units     =("quantity_sold", "sum"),
            avg_price       =("price", "mean"),
            avg_rating      =("rating", "mean"),
            avg_review_count=("review_count", "mean"),
            avg_discount    =("discount_percent", "mean"),
        )
        .round(2)
        .reset_index()
        .sort_values("total_revenue", ascending=False)
        .head(100)
    )
    top_prod["rank"] = range(1, len(top_prod) + 1)
    save(top_prod, "mart_top_products", conn)


def run():
    log.info("=== LOAD START ===")
    conn = sqlite3.connect(DB_PATH)
    df = load_processed()
    build_staging(df, conn)
    build_intermediate(df, conn)
    build_marts(df, conn)
    conn.close()
    log.info("=== LOAD DONE ===")


if __name__ == "__main__":
    run()
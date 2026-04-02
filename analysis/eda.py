"""
analysis/eda.py — Analyse Exploratoire Complète (EDA)
Génère statistiques + 9 figures pour comprendre le dataset Amazon.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import sqlite3
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

DB_PATH = Path("data/amazon_analytics.db")
FIG_DIR = Path("analysis/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = ["#FF9900", "#232F3E", "#146EB4", "#FF6600", "#00A8E0",
           "#1A9C3E", "#E31837", "#8B4513"]
sns.set_theme(style="whitegrid", palette=PALETTE)
plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False,
                      "axes.spines.right": False, "font.size": 11})


def load() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM processed_orders", conn)
    conn.close()
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def sep(title): print(f"\n{'═'*60}\n  {title}\n{'═'*60}")


def overview(df):
    sep("VUE GÉNÉRALE")
    print(f"Lignes     : {len(df):,}")
    print(f"Période    : {df['order_date'].min().date()} → {df['order_date'].max().date()}")
    print(f"Catégories : {sorted(df['product_category'].unique())}")
    print(f"Régions    : {sorted(df['customer_region'].unique())}")
    print(f"\nNaN :\n{df.isnull().sum()[df.isnull().sum()>0]}")
    print(f"\nStats numériques :")
    print(df[["price","discount_percent","quantity_sold","total_revenue","rating"]].describe().round(2))


def plot_category(df):
    cat = df.groupby("product_category")["total_revenue"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(cat.index, cat.values, color=PALETTE[:len(cat)])
    ax.bar_label(bars, labels=[f"${v/1e6:.2f}M" for v in cat.values], padding=4, fontsize=9)
    ax.set_title("Revenue total par catégorie", fontsize=14, fontweight="bold")
    ax.set_ylabel("Revenue (USD)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1e6:.1f}M"))
    plt.tight_layout()
    plt.savefig(FIG_DIR / "01_revenue_by_category.png"); plt.close()
    print("✓ Fig 1 : Revenue par catégorie")


def plot_region(df):
    reg = df.groupby("customer_region")["total_revenue"].sum().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(reg.index, reg.values, color=PALETTE[:len(reg)])
    ax.bar_label(bars, labels=[f"${v/1e6:.2f}M" for v in reg.values], padding=4, fontsize=9)
    ax.set_title("Revenue par région client", fontsize=14, fontweight="bold")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1e6:.1f}M"))
    plt.tight_layout()
    plt.savefig(FIG_DIR / "02_revenue_by_region.png"); plt.close()
    print("✓ Fig 2 : Revenue par région")


def plot_monthly(df):
    m = df.groupby(["year","month"])["total_revenue"].sum().reset_index()
    m["period"] = m["year"].astype(str)+"-"+m["month"].astype(str).str.zfill(2)
    fig, ax = plt.subplots(figsize=(14, 5))
    for y, grp in m.groupby("year"):
        ax.plot(grp["period"], grp["total_revenue"], marker="o", label=str(y), linewidth=2)
    ax.set_title("Tendance mensuelle du Revenue par année", fontsize=14, fontweight="bold")
    ax.set_ylabel("Revenue (USD)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1e6:.1f}M"))
    ax.legend(title="Année")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "03_monthly_trend.png"); plt.close()
    print("✓ Fig 3 : Tendance mensuelle")


def plot_payment(df):
    pay = df.groupby("payment_method")["total_revenue"].sum().sort_values(ascending=False)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    ax1.pie(pay.values, labels=pay.index, autopct="%1.1f%%", colors=PALETTE, startangle=90)
    ax1.set_title("Part revenue par paiement", fontweight="bold")
    bars = ax2.bar(pay.index, pay.values, color=PALETTE[:len(pay)])
    ax2.bar_label(bars, labels=[f"${v/1e6:.2f}M" for v in pay.values], padding=3, fontsize=8)
    ax2.set_title("Revenue par méthode de paiement", fontweight="bold")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1e6:.1f}M"))
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "04_payment_method.png"); plt.close()
    print("✓ Fig 4 : Méthode de paiement")


def plot_discount_impact(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    disc_rev = df.groupby("discount_segment")["total_revenue"].mean()
    axes[0].bar(disc_rev.index.astype(str), disc_rev.values, color=PALETTE)
    axes[0].set_title("Revenue moyen par segment de remise", fontweight="bold")
    axes[0].set_ylabel("Revenue moyen (USD)")
    axes[0].tick_params(axis="x", rotation=15)
    disc_qty = df.groupby("discount_segment")["quantity_sold"].mean()
    axes[1].bar(disc_qty.index.astype(str), disc_qty.values, color=PALETTE)
    axes[1].set_title("Quantité moyenne par segment de remise", fontweight="bold")
    axes[1].set_ylabel("Quantité moyenne")
    axes[1].tick_params(axis="x", rotation=15)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "05_discount_impact.png"); plt.close()
    print("✓ Fig 5 : Impact remise")


def plot_heatmap(df):
    pivot = df.pivot_table(values="total_revenue", index="product_category",
                           columns="customer_region", aggfunc="sum", fill_value=0)
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(pivot/1e6, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax,
                linewidths=0.5, cbar_kws={"label": "Revenue (M$)"})
    ax.set_title("Heatmap Revenue (M$) : Catégorie × Région", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "06_heatmap_category_region.png"); plt.close()
    print("✓ Fig 6 : Heatmap catégorie × région")


def plot_rating_distribution(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(df["rating"], bins=20, color=PALETTE[0], edgecolor="white", alpha=0.85)
    axes[0].set_title("Distribution des notes (Rating)", fontweight="bold")
    axes[0].set_xlabel("Rating")
    rat_rev = df.groupby("rating_segment")["total_revenue"].sum()
    axes[1].bar(rat_rev.index.astype(str), rat_rev.values/1e6, color=PALETTE)
    axes[1].set_title("Revenue par segment de note", fontweight="bold")
    axes[1].set_ylabel("Revenue (M$)")
    axes[1].tick_params(axis="x", rotation=10)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "07_rating_analysis.png"); plt.close()
    print("✓ Fig 7 : Analyse rating")


def plot_price_distribution(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(df["price"], bins=30, color=PALETTE[2], edgecolor="white", alpha=0.85)
    axes[0].set_title("Distribution des prix", fontweight="bold")
    axes[0].set_xlabel("Price (USD)")
    ps = df.groupby("price_segment")["total_revenue"].sum()
    axes[1].bar(ps.index.astype(str), ps.values/1e6, color=PALETTE)
    axes[1].set_title("Revenue par segment de prix", fontweight="bold")
    axes[1].set_ylabel("Revenue (M$)")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "08_price_distribution.png"); plt.close()
    print("✓ Fig 8 : Distribution prix")


def plot_quarterly(df):
    q = df.groupby(["year","quarter"])["total_revenue"].sum().reset_index()
    q["label"] = q["year"].astype(str) + " " + q["quarter"]
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = [PALETTE[0] if y==2022 else PALETTE[2] for y in q["year"]]
    bars = ax.bar(q["label"], q["total_revenue"]/1e6, color=colors)
    ax.bar_label(bars, labels=[f"${v:.2f}M" for v in q["total_revenue"]/1e6], padding=3, fontsize=9)
    ax.set_title("Revenue trimestriel 2022 vs 2023", fontsize=14, fontweight="bold")
    ax.set_ylabel("Revenue (M$)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=PALETTE[0], label="2022"), Patch(color=PALETTE[2], label="2023")])
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "09_quarterly_comparison.png"); plt.close()
    print("✓ Fig 9 : Comparaison trimestrielle")


def print_insights(df):
    sep("TOP INSIGHTS")
    print(f"Revenue total        : ${df['total_revenue'].sum():,.2f}")
    print(f"Nb commandes         : {len(df):,}")
    print(f"Catégorie #1         : {df.groupby('product_category')['total_revenue'].sum().idxmax()}")
    print(f"Région #1            : {df.groupby('customer_region')['total_revenue'].sum().idxmax()}")
    print(f"Paiement #1          : {df.groupby('payment_method')['total_revenue'].sum().idxmax()}")
    print(f"Note moyenne         : {df['rating'].mean():.2f} / 5")
    print(f"Remise moyenne       : {df['discount_percent'].mean():.1f}%")
    print(f"% commandes remisées : {(df['has_discount'].sum()/len(df)*100):.1f}%")
    print(f"Revenu moyen/commande: ${df['total_revenue'].mean():.2f}")
    print(f"Produits uniques     : {df['product_id'].nunique():,}")


if __name__ == "__main__":
    df = load()
    overview(df)
    sep("GÉNÉRATION FIGURES")
    plot_category(df)
    plot_region(df)
    plot_monthly(df)
    plot_payment(df)
    plot_discount_impact(df)
    plot_heatmap(df)
    plot_rating_distribution(df)
    plot_price_distribution(df)
    plot_quarterly(df)
    print_insights(df)
    print(f"\nFigures dans : {FIG_DIR}/")
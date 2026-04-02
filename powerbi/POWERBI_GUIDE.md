# 📊 Guide Power BI — Amazon Sales Analytics Dashboard

## 1. Import des données

### Option A — Import CSV direct (recommandé)
`Accueil → Obtenir des données → Texte/CSV`

Importer ces fichiers depuis `data/mart/` :

| Fichier CSV | Nom table Power BI |
|---|---|
| `mart_kpis.csv` | KPIs |
| `mart_category.csv` | Category |
| `mart_region.csv` | Region |
| `mart_payment.csv` | Payment |
| `mart_monthly_trend.csv` | MonthlyTrend |
| `mart_quarterly.csv` | Quarterly |
| `mart_category_region.csv` | CategoryRegion |
| `mart_discount_analysis.csv` | DiscountAnalysis |
| `mart_rating_analysis.csv` | RatingAnalysis |
| `mart_price_segment.csv` | PriceSegment |
| `mart_top_products.csv` | TopProducts |
| `stg_orders.csv` | Orders (table de détail) |

### Option B — Connexion SQLite via ODBC
`Obtenir des données → ODBC → DSN : {chemin vers amazon_analytics.db}`

---

## 2. Modèle de données (Relations)

```
Orders ──────────────────────────────────────────────┐
  │ (order_id, product_category, customer_region)   │
  │                                                  │
  ├──[product_category]──► Category                 │
  ├──[customer_region]───► Region                   │
  ├──[payment_method]────► Payment                  │
  └──[year, month]────────► MonthlyTrend             │
                                                     │
CategoryRegion ◄─[product_category + customer_region]┘
```

---

## 3. Mesures DAX essentielles

Crée une table `_Measures` vide et ajoute ces mesures :

```dax
// ── KPIs de base ──────────────────────────────────────────

Total Revenue =
    SUM(Orders[total_revenue])

Total Orders =
    COUNTROWS(Orders)

Total Units Sold =
    SUM(Orders[quantity_sold])

Avg Order Value =
    AVERAGE(Orders[total_revenue])

Avg Rating =
    AVERAGE(Orders[rating])

Avg Discount % =
    AVERAGE(Orders[discount_percent])

// ── Croissance ────────────────────────────────────────────

Revenue YoY % =
VAR current_year = SELECTEDVALUE(MonthlyTrend[year])
VAR rev_current  = CALCULATE([Total Revenue], MonthlyTrend[year] = current_year)
VAR rev_prev     = CALCULATE([Total Revenue], MonthlyTrend[year] = current_year - 1)
RETURN
    DIVIDE(rev_current - rev_prev, rev_prev) * 100

Revenue MoM % =
VAR current_month = SELECTEDVALUE(MonthlyTrend[month])
VAR current_year  = SELECTEDVALUE(MonthlyTrend[year])
VAR rev_current   = CALCULATE([Total Revenue],
                    MonthlyTrend[year] = current_year,
                    MonthlyTrend[month] = current_month)
VAR rev_prev      = CALCULATE([Total Revenue],
                    MonthlyTrend[year] = current_year,
                    MonthlyTrend[month] = current_month - 1)
RETURN
    DIVIDE(rev_current - rev_prev, rev_prev) * 100

// ── Part de marché ────────────────────────────────────────

Revenue Share % =
    DIVIDE(
        SUM(Category[total_revenue]),
        CALCULATE(SUM(Category[total_revenue]), ALL(Category))
    ) * 100

// ── Analyse remise ────────────────────────────────────────

% Orders Discounted =
    DIVIDE(
        CALCULATE(COUNTROWS(Orders), Orders[has_discount] = TRUE()),
        COUNTROWS(Orders)
    ) * 100

Revenue Lost to Discount =
    SUMX(Orders, Orders[discount_amount] * Orders[quantity_sold])

// ── Satisfaction ──────────────────────────────────────────

High Rating Orders % =
    DIVIDE(
        CALCULATE(COUNTROWS(Orders), Orders[is_high_rating] = TRUE()),
        COUNTROWS(Orders)
    ) * 100

// ── Revenue cumulé ────────────────────────────────────────

Cumulative Revenue =
    CALCULATE(
        [Total Revenue],
        FILTER(
            ALL(MonthlyTrend),
            MonthlyTrend[year] <= MAX(MonthlyTrend[year]) &&
            MonthlyTrend[month] <= MAX(MonthlyTrend[month])
        )
    )
```

---

## 4. Architecture du Dashboard (5 pages)

### Page 1 — Executive Overview
```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ Total    │ Orders   │ Units    │ Avg Order│ Avg      │  ← Cards KPI
│ Revenue  │ Count    │ Sold     │ Value    │ Rating   │
│ $XXX.XM  │ 50,000   │ XXX,XXX  │ $XXX     │ X.X/5    │
└──────────┴──────────┴──────────┴──────────┴──────────┘
┌─────────────────────────┬──────────────────────────────┐
│  Line chart             │  Donut                        │
│  Revenue mensuel 2022vs │  Revenue par catégorie        │
│  2023 (MonthlyTrend)    │  (Category)                   │
└─────────────────────────┴──────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│  Bar chart horizontal : Revenue par région (Region)      │
└──────────────────────────────────────────────────────────┘
```

### Page 2 — Produits & Catégories
```
┌─────────────────────────┬──────────────────────────────┐
│  Clustered Bar          │  Decomposition Tree           │
│  Revenue + Orders par   │  Catégorie → Région → Produit │
│  catégorie (Category)   │  (CategoryRegion + Orders)    │
└─────────────────────────┴──────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│  Matrix : Catégorie × Région — Revenue (CategoryRegion)  │
└──────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│  Table : Top 100 Produits (TopProducts)                  │
│  Colonnes : Rank | Product ID | Category | Revenue |     │
│  Orders | Avg Rating | Avg Discount                      │
└──────────────────────────────────────────────────────────┘
```

### Page 3 — Tendances Temporelles
```
┌──────────────────────────────────────────────────────────┐
│  Area chart : Revenue cumulé mensuel (MonthlyTrend)      │
└──────────────────────────────────────────────────────────┘
┌─────────────────────────┬──────────────────────────────┐
│  Grouped Bar            │  Line Chart                   │
│  Revenue trimestriel    │  MoM Growth % par mois        │
│  2022 vs 2023           │  (MonthlyTrend.mom_growth_pct)│
│  (Quarterly)            │                               │
└─────────────────────────┴──────────────────────────────┘
```

### Page 4 — Remises & Pricing
```
┌─────────────────────────┬──────────────────────────────┐
│  Bar chart              │  Scatter Plot                 │
│  Revenue moyen par      │  Discount % vs Revenue        │
│  segment remise         │  (Orders : sample)            │
│  (DiscountAnalysis)     │                               │
└─────────────────────────┴──────────────────────────────┘
┌─────────────────────────┬──────────────────────────────┐
│  Bar chart              │  Card                         │
│  Revenue par segment    │  % commandes remisées         │
│  de prix (PriceSegment) │  Revenue perdu en remises     │
└─────────────────────────┴──────────────────────────────┘
```

### Page 5 — Satisfaction & Paiements
```
┌─────────────────────────┬──────────────────────────────┐
│  Bar + Line combo       │  Donut                        │
│  Revenue + Avg Rating   │  Revenue par méthode paiement │
│  par catégorie          │  (Payment)                    │
│  (RatingAnalysis)       │                               │
└─────────────────────────┴──────────────────────────────┘
┌──────────────────────────────────────────────────────────┐
│  Table détail avec filtres cross-page                    │
│  Filtres : Année | Région | Catégorie | Canal paiement   │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Slicers recommandés (filtres globaux)

Ajouter sur chaque page :
- **Année** — `MonthlyTrend[year]`
- **Trimestre** — `MonthlyTrend[quarter]`
- **Catégorie** — `Category[product_category]`
- **Région** — `Region[customer_region]`
- **Méthode paiement** — `Payment[payment_method]`

---

## 6. Palette de couleurs Amazon

| Couleur | Hex | Usage |
|---|---|---|
| Amazon Orange | `#FF9900` | Couleur principale, KPIs |
| Dark Blue | `#232F3E` | Titres, fond |
| Light Blue | `#146EB4` | Visuels secondaires |
| Green | `#1A9C3E` | Valeurs positives |
| Red | `#E31837` | Valeurs négatives, alertes |

---

## 7. Publication

1. `Fichier → Publier → Power BI Service`
2. Crée un **workspace** dédié : `Amazon Sales Analytics`
3. Configure l'**actualisation planifiée** si connecté à une BDD live
4. Partage via lien ou intégration dans SharePoint
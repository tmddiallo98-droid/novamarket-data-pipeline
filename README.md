# NovaMarket — Pipeline de données sur Google Cloud

Projet fil rouge de ma formation **Data Engineering sur Google Cloud Platform** (BigQuery, Cloud Storage, Cloud Composer / Airflow, BigQuery ML).

## 🎯 Objectif

NovaMarket est un site e-commerce **fictif** dont les données (commandes, clients, produits, événements web) arrivent chaque jour sous forme de fichiers CSV, JSON et Parquet.
Ce dépôt construit, étape par étape, un **pipeline ELT automatisé et contrôlé** qui transforme ces fichiers bruts en données fiables pour le reporting, puis en un modèle de **prédiction du réachat client**.

## 🏗️ Architecture

```
Sources (CSV / JSON / Parquet)
        ↓  Python : extraction, validation (pandas)
Cloud Storage  →  raw/   processed/   archive/          (data lake)
        ↓  chargement
BigQuery RAW        copie fidèle de la source, tout en STRING
        ↓  SQL
BigQuery STAGING    typé, nettoyé, dédoublonné, une table par source
        ↓  SQL (ELT)
BigQuery CURATED    modèle en étoile : faits + dimensions
        ↓
Data mart / vues    → notebook Python (reporting)
        ↓
BigQuery ML         prédiction du réachat client

Airflow / Cloud Composer orchestre toute la chaîne :
planification, relances, alertes, contrôles qualité, monitoring
```

## 🧰 Stack

| Domaine | Outils |
|---|---|
| Stockage | Google Cloud Storage |
| Entrepôt de données | BigQuery (SQL standard) |
| Transformation et qualité | SQL, Python, pandas |
| Orchestration | Apache Airflow / Cloud Composer |
| Machine learning | BigQuery ML |
| Outils | Cloud Shell, gcloud, bq, Git / GitHub |

## 📁 Structure du dépôt

```
novamarket-data-pipeline/
├── README.md
├── .gitignore        # aucun secret ni donnée réelle publiés
├── scripts/          # scripts bash et Python (contrôle d'environnement, extraction)
├── sql/              # requêtes raw / staging / curated, tests qualité
├── notebooks/        # notebooks pandas et reporting
├── dags/             # DAGs Airflow
└── data/sample/      # petits fichiers d'exemple fictifs
```

## 📈 Avancement

| Section | Contenu | Statut |
|---|---|---|
| 1 | Pipeline de données, couches RAW / STAGING / CURATED, qualité | ✅ |
| 2 | Types et schémas, SQL (jointures, CTE), pandas, modélisation, qualité des données | ✅ |
| 3 | Google Cloud : projet, facturation, Cloud Shell, IAM, comptes de service, coûts | ✅ |
| 4 | Extraction vers Cloud Storage (Git/GitHub, buckets, Python, Parquet) | 🟡 En cours |
| 5 | Chargement et structuration dans BigQuery | ⬜ |
| 6 | Transformations SQL (staging → curated) | ⬜ |
| 7 | Orchestration avec Airflow / Cloud Composer | ⬜ |
| 8 | Analyse et vues SQL (data mart) | ⬜ |
| 9 | Reporting avec des notebooks Python | ⬜ |
| 10 | Machine learning avec BigQuery ML | ⬜ |

## ▶️ Utilisation

Contrôle de l'environnement Google Cloud (projet actif, datasets, localisation, rôles du compte de service, requêtes les plus coûteuses), depuis Cloud Shell :

```bash
bash scripts/controle_env.sh
```

## 🔐 Sécurité

- Aucune clé de compte de service, aucun mot de passe ni fichier `.env` dans ce dépôt (voir `.gitignore`).
- Le pipeline s'authentifie avec un **compte de service dédié**, aux droits minimaux (principe du moindre privilège).
- Toutes les données de `data/sample/` sont **fictives**.

"""Extraction NovaMarket : contrôle d'un fichier local, dépôt dans raw/, puis copie Parquet dans processed/.

Usage :
    python scripts/extraction.py <source> <chemin_du_fichier>
Exemples :
    python scripts/extraction.py commandes data/sample/commandes.csv
    python scripts/extraction.py clients data/sample/clients.json

Pour exécuter en tant que compte de service (impersonation) :
    NOVAMARKET_SA=sa-pipeline-novamarket@novamarket-510908.iam.gserviceaccount.com \
        python scripts/extraction.py clients data/sample/clients.json
"""
import os
import sys
from datetime import date

import pandas as pd
from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage

PROJET = "novamarket-510908"
BUCKET = "novamarket-510908-datalake"

# Colonnes obligatoires par source (le « contrat » du fichier)
COLONNES_ATTENDUES = {
    "commandes": ["order_id", "client_id", "date_commande", "montant", "statut", "canal"],
    "produits": ["product_id", "nom", "categorie", "prix", "date_maj"],
    "clients": ["client_id", "nom", "email", "ville"],
}


def creer_client():
    """Client Cloud Storage : ton compte par défaut, ou le compte de service si NOVAMARKET_SA est défini."""
    sa = os.environ.get("NOVAMARKET_SA")
    if not sa:
        return storage.Client(project=PROJET)
    import google.auth
    from google.auth import impersonated_credentials

    identifiants_source, _ = google.auth.default()
    identifiants = impersonated_credentials.Credentials(
        source_credentials=identifiants_source,
        target_principal=sa,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    print(f"(exécution en tant que {sa})")
    return storage.Client(project=PROJET, credentials=identifiants)


def lire_fichier(chemin):
    """Lit un fichier CSV ou JSON en DataFrame, sans deviner les types. Lève ValueError sinon."""
    extension = os.path.splitext(chemin)[1].lower()
    if extension == ".csv":
        return pd.read_csv(chemin, sep=";", dtype=str)
    if extension == ".json":
        return pd.read_json(chemin, dtype=False)
    if extension == ".jsonl":
        return pd.read_json(chemin, dtype=False, lines=True)
    
    raise ValueError(f"extension non prise en charge : {extension}")


def controler_fichier(chemin, source):
    """Renvoie (liste des problèmes BLOQUANTS, nombre de lignes). Liste vide = fichier accepté."""
    problemes = []
    try:
        df = lire_fichier(chemin)
    except pd.errors.EmptyDataError:  # en PREMIER : c'est une sous-classe de ValueError
        return ["fichier totalement vide"], 0
    except ValueError as erreur:  # JSON mal formé, extension inconnue…
        return [f"fichier illisible : {erreur}"], 0

    if len(df) == 0:
        problemes.append("fichier vide : aucune ligne de données")

    col_manquantes = [c for c in COLONNES_ATTENDUES[source] if c not in df.columns]
    if col_manquantes:
        problemes.append(f"colonnes manquantes : {col_manquantes}")

    return problemes, len(df)


def ecrire_parquet(chemin, nom_parquet):
    """Relit le fichier source et l'écrit en Parquet dans /tmp. Renvoie le chemin du Parquet local."""
    df = lire_fichier(chemin)
    chemin_parquet = os.path.join("/tmp", nom_parquet)
    df.to_parquet(chemin_parquet, index=False)
    return chemin_parquet


def deposer(client, chemin_local, chemin_gcs, immuable):
    """Dépose un fichier. immuable=True : refuse d'écraser un objet existant."""
    blob = client.bucket(BUCKET).blob(chemin_gcs)
    if immuable:
        blob.upload_from_filename(chemin_local, if_generation_match=0)
    else:
        blob.upload_from_filename(chemin_local)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)

    source, chemin = sys.argv[1], sys.argv[2]
    if source not in COLONNES_ATTENDUES:
        print(f"❌ Source inconnue : {source}. Sources possibles : {list(COLONNES_ATTENDUES)}")
        sys.exit(2)

    jour = date.today().isoformat()
    nom_fichier = os.path.basename(chemin)
    client = creer_client()

    problemes, nb_lignes = controler_fichier(chemin, source)

    if problemes:
        cible = f"quarantine/{source}/date={jour}/{nom_fichier}"
        deposer(client, chemin, cible, immuable=False)
        print(f"❌ REJETÉ : {problemes}")
        print(f"   Fichier mis en quarantaine : gs://{BUCKET}/{cible}")
        sys.exit(1)

    # 1) raw/ : l'original, immuable
    cible = f"raw/{source}/date={jour}/{nom_fichier}"
    try:
        deposer(client, chemin, cible, immuable=True)
    except PreconditionFailed:
        print(f"❌ raw est immuable : gs://{BUCKET}/{cible} existe déjà, rien n'a été écrasé")
        sys.exit(1)
    print(f"✅ ACCEPTÉ : {nb_lignes} lignes déposées dans gs://{BUCKET}/{cible}")

    # 2) processed/ : la copie Parquet, régénérable
    nom_parquet = os.path.splitext(nom_fichier)[0] + ".parquet"
    local_parquet = ecrire_parquet(chemin, nom_parquet)
    cible_processed = f"processed/{source}/date={jour}/{nom_parquet}"

    # Partie C — Contrôle du Parquet avant le dépôt dans processed/
    source_df = lire_fichier(chemin)
    parquet_df = pd.read_parquet(local_parquet)
    if len(parquet_df) != len(source_df) or list(parquet_df.columns) != list(source_df.columns):
        print(f"❌ CONTRÔLE PARQUET ÉCHOUÉ : lignes {len(source_df)} → {len(parquet_df)} ; "
              f"colonnes {list(source_df.columns)} → {list(parquet_df.columns)}")
        sys.exit(1)
    
    deposer(client, local_parquet, cible_processed, immuable=False)
    print(f"✅ CONVERTI : gs://{BUCKET}/{cible_processed}")

if __name__ == "__main__":
    main()

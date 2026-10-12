"""Extraction NovaMarket : contrôle d'un fichier local, puis dépôt dans Cloud Storage.

Usage :
    python scripts/extraction.py <source> <chemin_du_fichier>
Exemple :
    python scripts/extraction.py commandes data/sample/commandes.csv

Pour exécuter en tant que compte de service (impersonation) :
    NOVAMARKET_SA=sa-pipeline-novamarket@novamarket-510908.iam.gserviceaccount.com \
        python scripts/extraction.py commandes data/sample/commandes.csv
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


def controler_fichier(chemin, source):
    """Renvoie (liste des problèmes BLOQUANTS, nombre de lignes). Liste vide = fichier accepté."""
    problemes = []
    try:
        df = pd.read_csv(chemin, sep=";", dtype=str)
    except pd.errors.EmptyDataError:
        return ["fichier totalement vide ou illisible"], 0

    if len(df) == 0:
        problemes.append("fichier vide : aucune ligne de données")

    col_manquants = [i for i in  COLONNES_ATTENDUES[source] if i not in df.columns ]

    if col_manquants:
        problemes.append(f"colonnes manquantes : {col_manquants}")

    return problemes, len(df)


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

    cible = f"raw/{source}/date={jour}/{nom_fichier}"

    try:
        deposer(client, chemin, cible, True)
    except PreconditionFailed:
        print("raw est immuable, rien n'a été écrasé »")
        sys.exit(1)

    print(f"✅ ACCEPTÉ : {nb_lignes} lignes déposées dans gs://{BUCKET}/{cible}")


if __name__ == "__main__":
    main()

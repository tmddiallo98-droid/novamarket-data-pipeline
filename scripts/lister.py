"""Liste les objets d'un préfixe du bucket NovaMarket.

Usage : python scripts/lister.py raw/
"""
import sys

from google.cloud import storage

PROJET = "novamarket-510908"
BUCKET = "novamarket-510908-datalake"

prefixe = sys.argv[1] if len(sys.argv) > 1 else ""
client = storage.Client(project=PROJET)

total = 0
nb = 0
for blob in client.list_blobs(BUCKET, prefix=prefixe):
    print(f"{blob.size:>8} octets  {blob.updated:%Y-%m-%d %H:%M}  gs://{BUCKET}/{blob.name}")
    total += blob.size
    nb += 1

print(f"TOTAL : {nb} objets, {total} octets")

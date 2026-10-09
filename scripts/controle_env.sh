#!/bin/bash

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
PIPELINE_SA="sa-pipeline-novamarket@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Étape 1 : Afficher le projet actif ==="
gcloud config get-value project 2>/dev/null


echo "=== Étape 2 : Lister les datasets ==="
bq ls --project_id="${PROJECT_ID}"


echo "=== Étape 3 : Afficher la localisation et les labels du dataset raw ==="
bq show --format=prettyjson "${PROJECT_ID}:raw" 2>/dev/null | \
jq '{
  location: .location,
  labels: .labels
}'


echo "=== Étape 4 : Afficher les rôles du compte de service du pipeline ==="
echo "Compte de service : ${PIPELINE_SA}"

gcloud projects get-iam-policy "${PROJECT_ID}" \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${PIPELINE_SA}" \
  --format="table(bindings.role)"


echo "=== Étape 5 : Afficher le top 5 des jobs de la région US sur 7 jours, par octets facturés, avec un plafond de 50 Mo ==="

bq query \
  --location=US \
  --use_legacy_sql=false \
  --maximum_bytes_billed=50000000 \
  "
  SELECT
    job_id,
    user_email,
    creation_time,
    total_bytes_billed,
    ROUND(total_bytes_billed / POW(1024, 3), 2) AS billed_gb,
    query
  FROM \`${PROJECT_ID}.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT\`
  WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND job_type = 'QUERY'
  ORDER BY total_bytes_billed DESC
  LIMIT 5
  "

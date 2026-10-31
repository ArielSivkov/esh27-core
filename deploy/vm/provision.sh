#!/usr/bin/env bash
# Creates the CrownBot VM in GCP (plan phase 2). Run from a machine with gcloud logged in as Ariel.
# Not run yet. Everything here costs money only once the VM exists (about e2-small + 20GB disk).
#
#   PROJECT=<project id> ./deploy/vm/provision.sh
#
# What it creates: a service account with three roles, an e2-small Ubuntu 24.04 VM in me-west1
# with Shielded VM and OS Login, firewall rules that let in nothing but IAP SSH, and daily snapshots
# kept 7 days. The VM keeps an ephemeral public IP only so cloudflared can dial out; no port is open.
set -euo pipefail

PROJECT=${PROJECT:?set PROJECT}
REGION=${REGION:-me-west1}
ZONE=${ZONE:-me-west1-a}
NAME=${NAME:-crown-vm}
SA_NAME=${SA_NAME:-crown-vm}
SA="$SA_NAME@$PROJECT.iam.gserviceaccount.com"
TAG=crown
g() { gcloud --project "$PROJECT" "$@"; }

g services enable compute.googleapis.com iap.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com

g iam service-accounts describe "$SA" >/dev/null 2>&1 ||
  g iam service-accounts create "$SA_NAME" --display-name "CrownBot VM"
for role in roles/secretmanager.secretAccessor roles/logging.logWriter roles/aiplatform.user; do
  g projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$SA" --role "$role" --condition None >/dev/null
done

# The default network allows SSH and RDP from anywhere; these two rules override that for this VM only.
g compute firewall-rules describe crown-allow-iap-ssh >/dev/null 2>&1 ||
  g compute firewall-rules create crown-allow-iap-ssh --network default --direction INGRESS --priority 800 \
    --action ALLOW --rules tcp:22 --source-ranges 35.235.240.0/20 --target-tags "$TAG"
g compute firewall-rules describe crown-deny-ingress >/dev/null 2>&1 ||
  g compute firewall-rules create crown-deny-ingress --network default --direction INGRESS --priority 900 \
    --action DENY --rules all --source-ranges 0.0.0.0/0 --target-tags "$TAG"

g compute instances describe "$NAME" --zone "$ZONE" >/dev/null 2>&1 ||
  g compute instances create "$NAME" --zone "$ZONE" --machine-type e2-small \
    --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud \
    --boot-disk-size 20GB --boot-disk-type pd-balanced \
    --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
    --service-account "$SA" --scopes cloud-platform \
    --metadata enable-oslogin=TRUE --tags "$TAG"

g compute resource-policies describe crown-daily --region "$REGION" >/dev/null 2>&1 ||
  g compute resource-policies create snapshot-schedule crown-daily --region "$REGION" \
    --max-retention-days 7 --daily-schedule --start-time 00:00
g compute disks add-resource-policies "$NAME" --zone "$ZONE" --resource-policies crown-daily || true

echo "Done. Next: gcloud compute ssh $NAME --zone $ZONE --tunnel-through-iap, then run deploy/vm/bootstrap.sh"

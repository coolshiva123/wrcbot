#!/bin/bash

# Get the token and CA from the wrcbot ServiceAccount
VAULT_SA_NAME=$(kubectl get sa wrcbot-sa -n wrcbot -o jsonpath="{.secrets[*]['name']}")
if [ -z "$VAULT_SA_NAME" ]; then
  echo "No secret found for wrcbot-sa, using direct approach..."
  SA_JWT_TOKEN=$(kubectl create token wrcbot-sa -n wrcbot --duration=24h)
  SA_CA_CRT=$(kubectl get secret -n wrcbot -o jsonpath="{.items[?(@.type==\"kubernetes.io/service-account-token\")].data.ca\.crt}" | base64 -d)
else
  SA_JWT_TOKEN=$(kubectl get secret $VAULT_SA_NAME -n wrcbot -o jsonpath="{.data.token}" | base64 -d)
  SA_CA_CRT=$(kubectl get secret $VAULT_SA_NAME -n wrcbot -o jsonpath="{.data.ca\.crt}" | base64 -d)
fi

# Configure Vault
vault write auth/kubernetes/config \
    token_reviewer_jwt="$SA_JWT_TOKEN" \
    kubernetes_host="https://kubernetes.default.svc.cluster.local" \
    kubernetes_ca_cert="$SA_CA_CRT" \
    disable_iss_validation=true

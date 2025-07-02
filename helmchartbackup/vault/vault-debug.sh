#!/bin/bash
# Script to debug and fix Vault Kubernetes auth
# Run this from the Vault pod

# Set environment variables for Vault CLI
export VAULT_ADDR=http://127.0.0.1:8200
# You'll need to set this to your root token when running the script
export VAULT_TOKEN="root"

echo "======== Current Kubernetes Auth Configuration ========"
vault read auth/kubernetes/config

echo "======== Current wrcbot-role Configuration ========"
vault read auth/kubernetes/role/wrcbot-role

echo "======== Service Account Token for Vault ========"
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
echo "Token exists: $(if [[ -n $TOKEN ]]; then echo YES; else echo NO; fi)"
echo "Token length: $(echo $TOKEN | wc -c)"

echo "======== Kubernetes API Access Test ========"
curl -s -o /dev/null -w "Status code: %{http_code}\n" \
  --cacert /var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  -H "Authorization: Bearer $TOKEN" \
  https://kubernetes.default.svc/api/v1/namespaces

echo "======== Reconfiguring Vault Kubernetes Auth ========"
# Get Kubernetes CA certificate
KUBE_CA_CERT=$(cat /var/run/secrets/kubernetes.io/serviceaccount/ca.crt)

# Reconfigure Vault with proper parameters
vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc.cluster.local:443" \
    kubernetes_ca_cert="$KUBE_CA_CERT" \
    token_reviewer_jwt="$TOKEN" \
    disable_local_ca_jwt=false

echo "======== Updated Kubernetes Auth Configuration ========"
vault read auth/kubernetes/config

echo "======== Verifying wrcbot-role ========"
vault read auth/kubernetes/role/wrcbot-role

echo "======== Checking wrcbot-policy ========"
vault policy read wrcbot-policy

echo "Done! Now try authenticating from the wrcbot pod again."

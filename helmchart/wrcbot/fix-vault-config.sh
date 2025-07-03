#!/bin/bash

# Write the policy
cat > policy.hcl << EOF
path "secret/data/wrcbot-config" {
  capabilities = ["read"]
}
path "secret/metadata/wrcbot-config" {
  capabilities = ["read", "list"]
}
EOF
kubectl cp policy.hcl wrcbot/vault-0:/tmp/policy.hcl
kubectl exec -n wrcbot vault-0 -- vault policy write wrcbot-policy /tmp/policy.hcl
rm policy.hcl

# Update the Kubernetes auth role
echo "Updating Kubernetes auth role..."
kubectl exec -n wrcbot vault-0 -- vault write auth/kubernetes/role/wrcbot-role \
    bound_service_account_names=wrcbot-sa \
    bound_service_account_namespaces=wrcbot \
    policies=wrcbot-policy \
    ttl=24h

# Verify the secret exists at the correct path and has the right format
kubectl exec -n wrcbot vault-0 -- vault kv get -mount=secret wrcbot-config

# View the policy
echo "Current policy:"
kubectl exec -n wrcbot vault-0 -- vault policy read wrcbot-policy

# View the role configuration
echo "Role configuration:"
kubectl exec -n wrcbot vault-0 -- vault read auth/kubernetes/role/wrcbot-role

# Check if the secret is accessible using the role token
echo "Testing secret access with service account token..."
WRCBOT_POD=$(kubectl get pod -n default -l app=wrcbot -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)

if [ -n "$WRCBOT_POD" ]; then
    TOKEN=$(kubectl exec -it -n default $WRCBOT_POD -c vault-agent-init -- cat /var/run/secrets/kubernetes.io/serviceaccount/token)
    kubectl exec -n wrcbot vault-0 -- /bin/sh -c "VAULT_TOKEN=\$(vault write -field=token auth/kubernetes/login role=wrcbot-role jwt=$TOKEN) && vault kv get -mount=secret wrcbot-config"
else
    echo "No wrcbot pod found in default namespace"
fi

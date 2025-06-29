# Quick Vault Unsealing Guide

## When Vault Pod Restarts

After any Vault pod restart, you need to manually unseal Vault:

### Option 1: Using the Unsealing Script (Recommended)
```bash
cd /home/ec2-user/wrcbot
./unseal-vault.sh
```

### Option 2: Manual Command
```bash
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d)
kubectl exec deployment/vault -n wrcbot -- vault operator unseal $UNSEAL_KEY
```

### Option 3: Interactive
```bash
kubectl exec -it deployment/vault -n wrcbot -- vault operator unseal
# Enter key: eEU8yX1GSCvW/tCvEwBWoTYX+4ur1hrprcKiX/+W758=
```

## Check Status
```bash
# Check if unsealing is needed
kubectl exec deployment/vault -n wrcbot -- vault status

# Look for:
# Sealed: true  -> Needs unsealing
# Sealed: false -> Ready to use
```

## Verify Secrets
```bash
# After unsealing, verify secrets are accessible
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)

# Start port forward
kubectl port-forward svc/vault 8200:8200 -n wrcbot &

# Check secrets
vault kv get secret/wrcbot/config
```

---
**Note**: This manual process is more secure than auto-unsealing as it ensures human oversight when Vault comes online.

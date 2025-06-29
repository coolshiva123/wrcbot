# Vault Secrets Management

This guide explains how to manage secrets in your WRCBot deployment using HashiCorp Vault.

## Overview

Your Vault deployment now runs in production mode with persistent storage, ensuring secrets survive pod restarts. The system:

1. Maintains persistent storage for all secrets and configuration
2. Requires manual unsealing after pod restarts (for enhanced security)
3. Refreshes bot secrets from Vault periodically
4. Provides enterprise-grade secret management

## Manual Unsealing Process

After a Vault pod restart, you'll need to manually unseal Vault. This is a security feature that ensures only authorized personnel can bring Vault online.

### Quick Unseal Commands

```bash
# Method 1: Using the unsealing script (recommended)
./helmchart/vault/unseal-vault.sh

# Method 2: Manual unsealing
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d)
kubectl exec deployment/vault -n wrcbot -- vault operator unseal $UNSEAL_KEY

# Method 3: Interactive unsealing
kubectl exec -it deployment/vault -n wrcbot -- vault operator unseal
# Then enter the unseal key when prompted
```

### When to Unseal

You need to unseal Vault in these situations:
- After any Vault pod restart
- After cluster maintenance or node restarts  
- After Helm upgrades that restart the Vault pod
- If Vault is manually sealed for security reasons

### Checking Vault Status

```bash
# Check if Vault needs unsealing
kubectl exec deployment/vault -n wrcbot -- vault status

# Look for these indicators:
# Sealed: true  -> Needs unsealing
# Sealed: false -> Ready to use
```

## Initial Setup

### 1. Deploy Vault

```bash
# Deploy Vault using ArgoCD
kubectl apply -f argoapp/vaultapp.yaml
```

### 2. Get Vault Access Credentials

After deployment, retrieve the root token and unseal key:

```bash
# Get the root token
kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d

# Get the unseal key (for manual unsealing if needed)
kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d
```

### 3. Access Vault UI

```bash
# Port forward to access Vault UI
kubectl port-forward svc/vault 8200:8200 -n wrcbot

# Open http://localhost:8200 in your browser
# Login with the root token from step 2
```

## Managing Bot Secrets

### Setting Bot Secrets in Vault

1. **Via Vault UI:**
   - Navigate to `secret/` in the UI
   - Go to `wrcbot/config`
   - Add/update the following secrets:
     - `bot_token`: Your bot's token
     - `admin_users`: Comma-separated list of admin users
     - `bot_signing_secret`: Bot signing secret
     - `bot_app_token`: Bot application token

2. **Via Vault CLI:**

```bash
# Set environment variables
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="your-root-token-here"

# Create/update secrets
vault kv put secret/wrcbot/config \
  bot_token="xoxb-your-bot-token" \
  admin_users="user1,user2,user3" \
  bot_signing_secret="your-signing-secret" \
  bot_app_token="xapp-your-app-token"
```

3. **Via kubectl exec:**

```bash
# Exec into vault pod
kubectl exec -it deployment/vault -n wrcbot -- /bin/sh

# Inside the container
export VAULT_TOKEN="your-root-token"
vault kv put secret/wrcbot/config \
  bot_token="xoxb-your-bot-token" \
  admin_users="user1,user2,user3" \
  bot_signing_secret="your-signing-secret" \
  bot_app_token="xapp-your-app-token"
```

### Verifying Secrets

```bash
# Check if secrets are set correctly
vault kv get secret/wrcbot/config

# Or view in JSON format
vault kv get -format=json secret/wrcbot/config
```

## Secret Refresh Process

Secrets are automatically refreshed in several ways:

1. **Init Container**: Every time a bot pod starts, an init container fetches the latest secrets from Vault
2. **CronJob**: Every 30 minutes, a CronJob updates the Kubernetes secrets with the latest values from Vault
3. **Manual Refresh**: You can manually trigger a secret refresh

### Manual Secret Refresh

```bash
# Create a one-time job to refresh secrets
kubectl create job --from=cronjob/wrcbot-secret-refresh manual-refresh-$(date +%s) -n wrcbot
```

### Restart Bot to Pick Up New Secrets

```bash
# Restart the bot deployment to pick up refreshed secrets
kubectl rollout restart deployment/wrcbot -n wrcbot
```

## Troubleshooting

### Vault is Sealed

After a pod restart, Vault will be sealed and you need to unseal it manually:

```bash
# Check if Vault is sealed
kubectl exec deployment/vault -n wrcbot -- vault status

# If sealed, unseal it using the unsealing script
./helmchart/vault/unseal-vault.sh

# Or manually unseal with the stored key
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d)
kubectl exec deployment/vault -n wrcbot -- vault operator unseal $UNSEAL_KEY
```

### Secret Refresh Failing

Check the logs of the secret refresh job:

```bash
# Check recent jobs
kubectl get jobs -n wrcbot | grep secret-refresh

# Check job logs
kubectl logs job/wrcbot-secret-refresh-<timestamp> -n wrcbot
```

### Bot Can't Access Secrets

1. Check if secrets exist in Vault:
```bash
kubectl exec deployment/vault -n wrcbot -- vault kv get secret/wrcbot/config
```

2. Check if Kubernetes secret is updated:
```bash
kubectl get secret wrcbot-vault-secrets -n wrcbot -o yaml
```

3. Check bot logs:
```bash
kubectl logs deployment/wrcbot -n wrcbot
```

## Security Best Practices

1. **Change the Root Token**: The default root token should be changed in production
2. **Enable Authentication**: Set up proper authentication methods (AppRole, Kubernetes auth, etc.)
3. **Use Policies**: Create specific policies for different services instead of using the root token
4. **Regular Backups**: Backup your Vault data regularly
5. **Monitor Access**: Enable audit logging to monitor secret access

## Backup and Recovery

### Backup Vault Data

```bash
# The persistent volume contains all Vault data
# Back up the PV or the host path: /home/ec2-user/vaultdata
```

### Recovery

If you need to restore Vault:

1. Restore the persistent volume data
2. Redeploy Vault
3. The system should automatically unseal and be ready

## Advanced Configuration

### Custom Secret Paths

To use different secret paths, update the `vault.secretPath` in your `wrcbot/values.yaml`:

```yaml
vault:
  enabled: true
  secretPath: "secret/mybot/config"  # Custom path
```

### Different Refresh Intervals

Modify the CronJob schedule in `secret-refresh-cronjob.yaml`:

```yaml
spec:
  schedule: "*/15 * * * *"  # Every 15 minutes instead of 30
```

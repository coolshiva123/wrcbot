# WRCBot - Slack Bot with Persistent Vault Secrets

This is a WRC bot experiment for Slack with enterprise-grade secret management using HashiCorp Vault.

## Features

- **Persistent Secret Storage**: Secrets are stored in HashiCorp Vault with persistent volumes
- **Automatic Secret Refresh**: Secrets are automatically refreshed on pod restarts and periodically
- **ArgoCD Deployment**: GitOps-based deployment using ArgoCD
- **Helm Charts**: Production-ready Helm charts for all components
- **High Availability**: Designed for production use with proper persistence

## Components

- **WRCBot**: The main Slack bot application
- **HashiCorp Vault**: Secret management with persistent storage
- **Redis**: Caching layer
- **RabbitMQ**: Message queuing
- **ArgoCD**: GitOps deployment

## Quick Start

### 1. Deploy Infrastructure

```bash
# Deploy Vault (secrets management)
kubectl apply -f argoapp/vaultapp.yaml

# Deploy Redis
kubectl apply -f argoapp/redisapp.yaml

# Deploy RabbitMQ
kubectl apply -f argoapp/rabbitmqapp.yaml
```

### 2. Configure Vault Secrets

**First, ensure Vault is unsealed:**
```bash
./unseal-vault.sh
```

**Then set secrets via port forwarding:**
```bash
# Start port forwarding
kubectl port-forward svc/vault 8200:8200 -n wrcbot &

# Set environment variables
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)

# Set secrets using vault CLI
vault kv put secret/wrcbot/config \
  bot_token="xoxb-your-token" \
  admin_users="@awsterraform30" \
  bot_signing_secret="your-secret" \
  bot_app_token="xapp-your-token"

# Or visit http://localhost:8200 to use Vault UI
```

### 3. Deploy the Bot

```bash
# Deploy WRCBot
kubectl apply -f argoapp/wrc-app.yaml
```

## Secret Management

### Vault Secrets Persistence

The Vault deployment now runs in production mode with:

- **Persistent Volumes**: Secrets survive pod restarts and cluster maintenance
- **Automatic Unsealing**: Vault automatically unseals after restarts
- **Secret Refresh**: Bot secrets are refreshed automatically every 30 minutes
- **Init Containers**: Fresh secrets are fetched on every bot pod start

### Managing Secrets

**Check Vault status:**
```bash
kubectl exec deployment/vault -n wrcbot -- vault status
```

**Unseal Vault if needed:**
```bash
./unseal-vault.sh
```

**Set bot secrets:**
```bash
# Port forward to Vault
kubectl port-forward svc/vault 8200:8200 -n wrcbot &

# Set environment variables
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)

# Set secrets
vault kv put secret/wrcbot/config \
  bot_token="xoxb-your-token" \
  admin_users="@awsterraform30" \
  bot_signing_secret="your-secret" \
  bot_app_token="xapp-your-token"
```

**View current secrets:**
```bash
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)
vault kv get secret/wrcbot/config
```

**Restart bot to pick up new secrets:**
```bash
kubectl rollout restart deployment/wrcbot -n wrcbot
```

### Required Secrets

The bot requires the following secrets in Vault at path `secret/wrcbot/config`:

- `bot_token`: Your Slack bot token (xoxb-...)
- `admin_users`: Comma-separated list of admin users
- `bot_signing_secret`: Slack app signing secret
- `bot_app_token`: Slack app token (xapp-...)

## Troubleshooting

### Secrets Not Persisting

Your vault secrets now persist across pod restarts! The issue is completely resolved.

**After any Vault pod restart, simply unseal Vault:**

```bash
# Quick unseal command
**Manual Vault Unsealing:**
```bash
./unseal-vault.sh
```

# Check status
kubectl exec deployment/vault -n wrcbot -- vault status
```

**The vault secrets persistence architecture ensures:**
- ✅ **Data Survives Restarts**: All secrets stored in persistent volumes
- ✅ **Configuration Preserved**: Vault initializes with existing data  
- ✅ **Zero Data Loss**: Complete persistence across cluster maintenance
- ✅ **Security First**: Manual unsealing ensures authorized access

See [VAULT_QUICK_UNSEAL.md](VAULT_QUICK_UNSEAL.md) for quick reference.

### Manual Secret Recovery

If you need to restart the bot to pick up secret changes:

```bash
# Restart the bot deployment
kubectl rollout restart deployment/wrcbot -n wrcbot

# Check deployment status
kubectl rollout status deployment/wrcbot -n wrcbot
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     WRCBot      │    │   HashiCorp     │    │   Persistent    │
│   (Slack Bot)   │◄──►│     Vault       │◄──►│    Storage      │
│                 │    │  (Production)   │    │   (4GB PVC)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │   Secret Sync   │
│   (Caching)     │    │   (CronJob)     │
└─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│    RabbitMQ     │
│  (Messaging)    │
└─────────────────┘
```

## Development

### Local Development

See `setuperrbot_local.md` for local development setup.

### Docker Experiments

Various Docker configurations are available in the `Docker Expts/` directory for testing different setups.

## Production Deployment

### Security Considerations

1. **Change Default Tokens**: Update the default Vault root token
2. **Enable Authentication**: Configure proper Vault authentication methods
3. **Network Policies**: Implement Kubernetes network policies
4. **RBAC**: Use minimal required permissions
5. **Regular Backups**: Backup Vault data and Kubernetes configurations

### Monitoring

Monitor the following components:

- Vault seal status and secret access
- Bot application logs and health endpoints
- Secret refresh job success/failure
- Persistent volume usage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the provided Docker experiments
5. Submit a pull request

## Documentation

- [Vault Secrets Guide](helmchart/vault/VAULT_SECRETS_GUIDE.md) - Comprehensive secret management guide
- [Local Setup](setuperrbot_local.md) - Local development setup
- Individual component README files in their respective directories
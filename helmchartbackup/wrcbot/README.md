# WRC Bot Helm Chart

This Helm chart deploys the WRC Bot application on a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster
- Helm 3.x installed
- Vault service for secrets management
- Bot tokens and secrets stored in Vault

## Installation

### Quick Start

1. **Install dependencies first:**
```bash
# Install Vault
helm install vault ../vault -n wrcbot --create-namespace
```

2. **Store bot secrets in Vault:**
```bash
# Set up port forwarding for Vault
kubectl port-forward -n wrcbot svc/vault 8200:8200

# Store bot configuration (replace with actual values)
echo '{
  "bot_token": "xoxb-your-bot-token",
  "admin_users": "@your-admin-user",
  "bot_signing_secret": "your-signing-secret",
  "bot_app_token": "xapp-your-app-token"
}' | VAULT_ADDR='http://localhost:8200' VAULT_TOKEN='root' vault kv put secret/wrcbot/config -
```

3. **Install the WRC Bot:**
```bash
helm install wrcbot . -n wrcbot
```

### Custom Installation

You can customize the installation by creating a custom values file:

```bash
# Create custom-values.yaml
cp values.yaml custom-values.yaml

# Edit custom-values.yaml with your preferences

# Install with custom values
helm install wrcbot . -n wrcbot -f custom-values.yaml
```

## Configuration

### Main Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of bot replicas | `1` |
| `image.repository` | Bot container image repository | `wrcbot` |
| `image.tag` | Bot container image tag | `latest` |
| `vault.enabled` | Enable Vault integration | `true` |
| `vault.secretPath` | Path to secrets in Vault | `secret/wrcbot/config` |
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.size` | Size of persistent volume | `1Gi` |

### Environment Variables

The bot deployment will include these environment variables:

- `VAULT_ADDR`: Vault server address

### Secrets from Vault

The following secrets are automatically loaded from Vault:

- `BOT_TOKEN`: Slack bot token
- `ADMIN_USERS`: Bot admin users
- `BOT_SIGNING_SECRET`: Slack signing secret
- `BOT_APP_TOKEN`: Slack app token

## Usage

### Check Status

```bash
# Check pod status
kubectl get pods -n wrcbot

# Check logs
kubectl logs -n wrcbot deployment/wrcbot

# Port forward to access bot (if needed)
kubectl port-forward -n wrcbot svc/wrcbot 8080:80
```

### Scaling

```bash
# Scale replicas
helm upgrade wrcbot . -n wrcbot --set replicaCount=3

# Enable autoscaling
helm upgrade wrcbot . -n wrcbot \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=1 \
  --set autoscaling.maxReplicas=5
```

## Troubleshooting

### Common Issues

1. **Vault Connection Issues:**
   - Ensure Vault is running and unsealed
   - Check if port forwarding is active
   - Verify secrets are stored in the correct path

2. **Bot Authentication Issues:**
   - Verify bot tokens in Vault are correct
   - Check if admin users are properly configured
   - Ensure bot has necessary Slack permissions

### Debug Commands

```bash
# Check vault secrets
kubectl exec -n wrcbot deploy/vault -- vault kv get secret/wrcbot/config

# Check bot environment
kubectl exec -n wrcbot deploy/wrcbot -- env | grep -E "(BOT|VAULT)"

# Check connectivity
kubectl exec -n wrcbot deploy/wrcbot -- nc -zv vault 8200
```

## Uninstallation

```bash
# Uninstall bot
helm uninstall wrcbot -n wrcbot

# Uninstall dependencies (if needed)
helm uninstall vault -n wrcbot

# Delete namespace (optional)
kubectl delete namespace wrcbot
```

## Security Considerations

- Bot tokens are stored securely in Vault
- Use RBAC to limit access to Vault secrets
- Consider using Vault Agent for secret injection
- Enable network policies for pod-to-pod communication
- Use non-root containers when possible

## Contributing

To contribute to this chart:

1. Make changes to templates or values
2. Test the chart: `helm template . --debug`
3. Validate syntax: `helm lint .`
4. Test installation in development cluster

## License

This chart is licensed under the MIT License.

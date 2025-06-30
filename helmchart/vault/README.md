# Vault Helm Chart

This Helm chart deploys HashiCorp Vault on a Kubernetes cluster with data persistence support.

## ⚠️ Data Persistence Important Information

**Current Limitation**: Due to minikube running in Docker mode, true filesystem persistence between minikube restarts is not supported. However, this setup provides:

✅ **Data persistence as long as minikube is running** (stop/start OK)  
✅ **Backup/restore mechanism** for minikube delete/recreate scenarios  
✅ **Easy data migration** between minikube clusters  

## Quick Start

```bash
# Setup Vault with persistence support
./helmchart/vault/setup-vault-persistence.sh

# Unseal Vault
./helmchart/vault/unseal-vault.sh

# Set up secrets
./helmchart/vault/set-vault-secrets.sh
```

## Data Persistence Workflow

### Before Minikube Restart
```bash
# Always backup your data first!
./helmchart/vault/backup-vault-data.sh
```

### After Minikube Restart
```bash
# Deploy Vault
kubectl apply -f /home/ec2-user/wrcbot/argoproj/wrcbot.yaml

# Restore your data
./helmchart/vault/restore-vault-data.sh

# Unseal Vault
./helmchart/vault/unseal-vault.sh
```

## Prerequisites

- Kubernetes cluster (minikube)
- kubectl configured
- ArgoCD deployed (for GitOps deployment)

## Available Scripts

| Script | Purpose |
|--------|---------|
| `setup-vault-persistence.sh` | Complete setup with persistence support |
| `backup-vault-data.sh` | Backup Vault data before minikube restart |
| `restore-vault-data.sh` | Restore Vault data after minikube restart |
| `unseal-vault.sh` | Unseal Vault (required after each restart) |
| `get-vault-credentials.sh` | Get root token and unseal key |
| `set-vault-secrets.sh` | Interactive secret management |
| `view-vault-secrets.sh` | View stored secrets (safely) |

## Manual Installation (if not using setup script)

### Deploy using ArgoCD
```bash
kubectl apply -f /home/ec2-user/wrcbot/argoproj/wrcbot.yaml
```

### Wait for deployment
```bash
kubectl wait --for=condition=ready pod -l app=vault -n wrcbot --timeout=300s
```

## Unsealing Vault

Vault starts in a sealed state and must be unsealed before use.

**Method 1: Using the unseal script (recommended)**
```bash
./helmchart/vault/unseal-vault.sh
```

**Method 2: One-liner**
```bash
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d) && kubectl exec deployment/vault -n wrcbot -- vault operator unseal $UNSEAL_KEY
```

**Method 3: Interactive**
```bash
kubectl exec -it deployment/vault -n wrcbot -- vault operator unseal
# Then paste the unseal key when prompted
```

## Getting Vault Credentials

**Option 1: Using the credentials script**
```bash
./helmchart/vault/get-vault-credentials.sh
```

**Option 2: Manual commands**
```bash
# Get root token
kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d

# Get unseal key  
kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d
```

## Accessing Vault UI

1. **Start port forwarding:**
```bash
kubectl port-forward svc/vault 8200:8200 -n wrcbot
```

2. **Open browser:** http://localhost:8200

3. **Login with root token:** Use the token from `get-vault-credentials.sh`

## Setting Up Secrets

**Interactive method (recommended):**
```bash
./helmchart/vault/set-vault-secrets.sh
```

**Manual method:**
```bash
# Login to Vault
kubectl exec -it deployment/vault -n wrcbot -- vault auth -method=token token=<root-token>

# Create secrets
kubectl exec -it deployment/vault -n wrcbot -- vault kv put secret/wrcbot/config \
    RABBITMQ_HOST=rabbitmq.wrcbot.svc.cluster.local \
    RABBITMQ_PORT=5672 \
    RABBITMQ_USERNAME=user \
    RABBITMQ_PASSWORD=your-password
```

## Viewing Secrets

**Safe viewing (values masked):**
```bash
./helmchart/vault/view-vault-secrets.sh
```

**Show actual values:**
```bash
./helmchart/vault/view-vault-secrets.sh --show-values
```

## Troubleshooting

### Vault Pod Not Starting
```bash
kubectl describe pod -l app=vault -n wrcbot
kubectl logs -l app=vault -n wrcbot
```

### Vault Sealed
```bash
./helmchart/vault/unseal-vault.sh
```

### Check Vault Status
```bash
kubectl exec deployment/vault -n wrcbot -- vault status
```

### Backup/Restore Issues
```bash
# List available backups
ls -la /home/ec2-user/vault-persistent-data/

# Check if Vault pod is running
kubectl get pods -n wrcbot -l app=vault

# Manual backup
kubectl exec -n wrcbot deployment/vault -- tar czf - /vault/file > manual-backup.tar.gz
```

## Data Backup Location

Backups are stored in: `/home/ec2-user/vault-persistent-data/`

## Security Notes

- The root token is stored in Kubernetes secrets
- All secrets are base64 encoded (not encrypted at rest by default)
- Consider using external secret management for production
- Vault data is stored in `/tmp/vault-data` inside the minikube container

## Configuration

The Vault configuration can be customized by editing `values.yaml`:

```yaml
storage:
  enabled: true
  accessModes:
    - ReadWriteOnce
  size: 4Gi
  path: /tmp/vault-data  # Path inside minikube container

vault:
  rootToken: "root"      # Change for production
  mode: "production"     # production or dev
```

## Persistent Volume Behavior

- **Path**: `/tmp/vault-data` (inside minikube container)
- **Persistence**: Data survives pod restarts but NOT minikube restarts
- **Backup**: Use `backup-vault-data.sh` before minikube operations
- **Restore**: Use `restore-vault-data.sh` after minikube restart

## Production Considerations

For production environments, consider:

1. **External Storage**: Use cloud storage or network-attached storage
2. **Auto-unseal**: Configure auto-unseal with cloud key management
3. **High Availability**: Deploy multiple Vault instances
4. **Backup Automation**: Automated backup scheduling
5. **Secret Rotation**: Implement secret rotation policies

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault on Kubernetes](https://www.vaultproject.io/docs/platform/k8s)
- [Vault Helm Chart](https://github.com/hashicorp/vault-helm)
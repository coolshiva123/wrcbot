# HashiCorp Vault Helm Chart

This Helm chart deploys HashiCorp Vault on Kubernetes with configurable storage backends and security settings.

## Prerequisites

- Kubernetes cluster (v1.16+)
- Helm 3.0+
- Persistent Volume provisioner support in the underlying infrastructure (if persistence is enabled)

## Installation

### 1. Install the Chart

```bash
# Install with default values
helm install vault ./vault

# Install with custom values
helm install vault ./vault -f custom-values.yaml

# Install in a specific namespace
helm install vault ./vault -n vault --create-namespace
```

### 2. Verify Installation

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=vault

# Check service
kubectl get svc -l app.kubernetes.io/name=vault

# Check logs
kubectl logs -l app.kubernetes.io/name=vault
```

## Configuration

### Basic Configuration

Key configuration options in `values.yaml`:

```yaml
# Number of replicas
replicaCount: 1

# Docker image
image:
  repository: vault
  tag: "1.15.2"

# Service configuration
service:
  type: ClusterIP
  port: 8200

# Persistence (recommended for production)
persistence:
  enabled: true
  size: 10Gi
```

### Vault Configuration

```yaml
vault:
  # Storage backend
  storage:
    type: "file"  # Options: file, consul, etcd, raft
    config:
      path: "/vault/data"
  
  # Listener configuration
  listener:
    tcp:
      address: "0.0.0.0:8200"
      tls_disable: true  # Set to false for production
  
  # Enable UI
  ui: true
  
  # Development mode (NOT for production)
  dev: false
```

## Post-Installation Setup

### 1. Initialize Vault

After installation, you need to initialize Vault:

```bash
# Port forward to access Vault
kubectl port-forward svc/vault 8200:8200

# Initialize Vault (run this once)
vault operator init

# Save the unseal keys and root token securely!
```

### 2. Unseal Vault

Vault starts sealed and needs to be unsealed:

```bash
# Unseal with 3 different keys (by default)
vault operator unseal <unseal-key-1>
vault operator unseal <unseal-key-2>
vault operator unseal <unseal-key-3>

# Check status
vault status
```

### 3. Login and Configure

```bash
# Login with root token
vault auth <root-token>

# Enable auth methods
vault auth enable userpass

# Create policies
vault policy write my-policy - <<EOF
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

# Create users
vault write auth/userpass/users/myuser password=mypassword policies=my-policy
```

## Production Considerations

### 1. High Availability

For production, consider using:
- Multiple replicas with shared storage (Consul, etcd)
- Raft storage for built-in clustering
- Load balancer for service exposure

```yaml
replicaCount: 3
vault:
  storage:
    type: "raft"
    config:
      path: "/vault/data"
```

### 2. Security

- Enable TLS/SSL
- Use proper RBAC
- Regular backups
- Monitor unseal keys

```yaml
vault:
  listener:
    tcp:
      tls_disable: false
      tls_cert_file: "/path/to/cert"
      tls_key_file: "/path/to/key"
```

### 3. Ingress Setup

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: vault.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: vault-tls
      hosts:
        - vault.example.com
```

## Uninstallation

```bash
# Uninstall the release
helm uninstall vault

# Clean up PVCs (if needed)
kubectl delete pvc -l app.kubernetes.io/name=vault
```

## Troubleshooting

### Common Issues

1. **Vault not starting**: Check logs for configuration errors
2. **Sealed vault**: Vault needs to be unsealed after each restart
3. **Permission denied**: Check security contexts and file permissions
4. **Storage issues**: Verify PVC creation and storage class

### Debug Commands

```bash
# Check pod logs
kubectl logs -l app.kubernetes.io/name=vault

# Describe pod for events
kubectl describe pod -l app.kubernetes.io/name=vault

# Check configuration
kubectl get configmap vault-config -o yaml

# Test connectivity
kubectl exec -it deployment/vault -- vault status
```

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Vault image repository | `vault` |
| `image.tag` | Vault image tag | `1.15.2` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8200` |
| `persistence.enabled` | Enable persistence | `true` |
| `persistence.size` | PVC size | `10Gi` |
| `vault.ui` | Enable Vault UI | `true` |
| `vault.dev` | Enable dev mode | `false` |
| `ingress.enabled` | Enable ingress | `false` |

## Security Notes

- **Never use dev mode in production**
- **Store unseal keys securely**
- **Use proper TLS certificates**
- **Implement proper backup strategies**
- **Monitor Vault logs for security events**

## Support

For issues related to this chart, please check:
1. Vault official documentation
2. Kubernetes documentation
3. Helm documentation

# Vault Helm Chart

This Helm chart deploys HashiCorp Vault on a Kubernetes cluster. It includes the necessary configurations for persistent storage and deployment.

## Prerequisites

- Kubernetes cluster
- Helm 3.x installed
- Access to the EC2 instance where the PersistentVolume will be created

## Installation

To install the chart, use the following command:

```bash
helm install my-vault ./vault-helm-chart
```

Replace `my-vault` with your desired release name.

## Configuration

You can customize the deployment by modifying the `values.yaml` file. This file contains default configuration values that can be overridden.

## Persistent Storage

This chart creates a PersistentVolume and PersistentVolumeClaim to store Vault data. The data will be stored at the path `/home/ec2-user/vaultdata` on the EC2 instance.

## Uninstallation

To uninstall the chart, use the following command:

```bash
helm uninstall my-vault
```

Replace `my-vault` with your release name.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

Do this

sudo mkdir -p /home/ec2-user/vaultdata && sudo chown $(whoami):$(whoami) /home/ec2-user/vaultdata


## Vault Seal/Unseal Operations

**Unseal Key**: `xxxxx`  
**Root Token**: `root`

### Access Vault
```bash
# Set up port forwarding
kubectl port-forward -n wrcbot svc/vault 8200:8200

# Check status
export VAULT_ADDR='http://localhost:8200'
vault status
```

### Install Vault CLI
```bash
sudo yum install -y yum-utils && sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo && sudo yum -y install vault
```

### Seal Vault
```bash
# Seal the vault (requires root token)
VAULT_ADDR='http://localhost:8200' VAULT_TOKEN='root' vault operator seal
```

### Unseal Vault
```bash
# Unseal the vault (requires unseal key)
VAULT_ADDR='http://localhost:8200' vault operator unseal lmiZUCyKqanlY1oW8JxnHaimyl5K4L0qfI6cdN+i5c4=
```

### Basic Operations
```bash
# Set environment variables
export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root'

# Check status
vault status

# List secrets engines
vault secrets list

# Store a secret
vault kv put secret/myapp/config username=admin password=supersecret

# Retrieve a secret
vault kv get secret/myapp/config

#API seal status
curl -s http://localhost:8200/v1/sys/seal-status | jq '.'
```
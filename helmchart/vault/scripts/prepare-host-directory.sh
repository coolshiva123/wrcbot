#!/bin/bash

# Script to prepare the host directory for Vault data and get node information
# Run this on your EC2 instance before deploying Vault

VAULT_DATA_DIR="/home/ec2-user/vaultdata"

echo "=== Preparing Vault Host Directory ==="

# Create the directory if it doesn't exist
echo "Creating Vault data directory: $VAULT_DATA_DIR"
sudo mkdir -p "$VAULT_DATA_DIR"

# Set proper ownership (1000:1000 is the vault user in the container)
sudo chown -R 1000:1000 "$VAULT_DATA_DIR"

# Set proper permissions
sudo chmod -R 755 "$VAULT_DATA_DIR"

echo "Directory created and configured successfully!"
echo "Path: $VAULT_DATA_DIR"
echo "Owner: $(ls -ld $VAULT_DATA_DIR | awk '{print $3":"$4}')"
echo "Permissions: $(ls -ld $VAULT_DATA_DIR | awk '{print $1}')"

echo ""
echo "=== Getting Kubernetes Node Information ==="

# Get the current node name for Kubernetes
if command -v kubectl &> /dev/null; then
    echo "Available Kubernetes nodes:"
    kubectl get nodes --no-headers -o custom-columns=":metadata.name"
    echo ""
    echo "Please update your values.yaml with one of the node names above in:"
    echo "persistence.hostPath.allowedNodes"
else
    echo "kubectl not found. Please install kubectl or get the node name manually."
    echo "You can get the node name by running: kubectl get nodes"
fi

echo ""
echo "=== Next Steps ==="
echo "1. Update values.yaml with the correct node name"
echo "2. Commit and push your changes"
echo "3. Sync the Vault application in ArgoCD"

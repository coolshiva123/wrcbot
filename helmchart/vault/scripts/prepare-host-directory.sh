#!/bin/bash

# Script to prepare the host directory for Vault data in Minikube
# Run this to create the directory inside Minikube VM

VAULT_DATA_DIR="/data/vaultdata"

echo "=== Preparing Vault Directory in Minikube ==="

# Check if running in Minikube environment
if command -v minikube &> /dev/null; then
    echo "Creating directory inside Minikube VM..."
    
    # Create directory inside Minikube VM
    minikube ssh "sudo mkdir -p $VAULT_DATA_DIR"
    minikube ssh "sudo chown -R 1000:1000 $VAULT_DATA_DIR"
    minikube ssh "sudo chmod -R 755 $VAULT_DATA_DIR"
    
    echo "Directory created successfully in Minikube VM!"
    echo "Path: $VAULT_DATA_DIR (inside Minikube VM)"
    
    # Verify the directory
    echo "Verifying directory:"
    minikube ssh "ls -la $VAULT_DATA_DIR"
    
else
    echo "Minikube not found. Creating directory locally..."
    echo "Note: This may not work if Minikube doesn't have access to this path"
    
    # Fallback - create locally
    sudo mkdir -p "$VAULT_DATA_DIR"
    sudo chown -R 1000:1000 "$VAULT_DATA_DIR"
    sudo chmod -R 755 "$VAULT_DATA_DIR"
fi

echo ""
echo "=== Minikube Node Information ==="
kubectl get nodes --no-headers -o custom-columns=":metadata.name"

echo ""
echo "=== Next Steps ==="
echo "1. The directory has been created inside Minikube VM"
echo "2. Commit and push your changes"
echo "3. Sync the Vault application in ArgoCD"

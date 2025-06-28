#!/bin/bash

# Vault Minikube Deployment Script
set -e

echo "🚀 Deploying Vault on Minikube"

# Check if Minikube is running
if ! minikube status &>/dev/null; then
    echo "❌ Minikube is not running. Please start it with: minikube start"
    exit 1
fi

echo "✅ Minikube is running"

# Create the data directory in Minikube
echo "📁 Creating Vault data directory in Minikube..."
minikube ssh "sudo mkdir -p /data/vaultdata && sudo chown -R 1000:1000 /data/vaultdata && sudo chmod -R 755 /data/vaultdata"

echo "✅ Directory created: /data/vaultdata"

# Create namespace if it doesn't exist
echo "🔧 Creating wrcbot namespace..."
kubectl create namespace wrcbot --dry-run=client -o yaml | kubectl apply -f -

# Deploy Vault using Helm
echo "🎯 Deploying Vault..."
helm upgrade --install vault ./vault -n wrcbot

# Wait for deployment
echo "⏳ Waiting for Vault pod to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=vault -n wrcbot --timeout=300s

# Get pod status
echo "📊 Vault deployment status:"
kubectl get pods -n wrcbot -l app.kubernetes.io/name=vault

# Get service info
echo "🌐 Vault service info:"
kubectl get svc -n wrcbot vault

# Port forward for access
echo "🔗 Setting up port forwarding..."
echo "Run this command to access Vault UI:"
echo "kubectl port-forward -n wrcbot svc/vault 8200:8200"
echo ""
echo "Then access Vault at: http://localhost:8200"
echo "Root token: myroot"

echo "✅ Vault deployment completed successfully!"

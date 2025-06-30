# ArgoCD Deployment Setup for WRCBot

## Overview
This document describes the ArgoCD application setup for deploying the WRCBot via Helm charts on Kubernetes/minikube.

## Application Structure

### Parent Application: `wrc-app.yaml`
- **Name**: `wrcbot-apps`
- **Purpose**: Parent ArgoCD Application that manages all component applications
- **Includes**: redis, rabbitmq, vault, and wrcbot applications
- **Path**: `argoapp/`
- **Pattern**: `{redisapp.yaml,rabbitmqapp.yaml,vaultapp.yaml,wrcbotapp.yaml}`

### WRCBot Application: `wrcbotapp.yaml`
- **Name**: `wrcbot`
- **Purpose**: Deploys the wrcbot application using the simplified Helm chart
- **Path**: `helmchart/wrcbot`
- **Target Namespace**: `wrcbot`
- **Image**: `wrcbot:1.0` (local image in minikube)

## Deployment Configuration

### Image Setup
- **Image**: `wrcbot:1.0`
- **Pull Policy**: `IfNotPresent` (uses local image in minikube)
- **Location**: Available in minikube Docker daemon

### Helm Chart Simplifications
The wrcbot Helm chart has been simplified for the first iteration:

**Removed Components:**
- HPA (Horizontal Pod Autoscaler)
- Ingress
- Secret refresh cronjob
- Vault RBAC
- Vault secrets
- Persistent Volumes/Claims
- Service Accounts

**Current Features:**
- Basic Deployment with keep-alive command for debugging
- ConfigMap with transient data storage (`/tmp/data`)
- ClusterIP Service
- Override command for debugging: `while true; do echo 'Pod is running...'; sleep 30; done`
- Health checks disabled via `disableHealthChecks: true`
- Environment variables configured

## Deployment Steps

### 1. Ensure Local Image is Available
```bash
# Switch to minikube Docker environment
eval $(minikube docker-env)

# Verify image exists
docker images | grep wrcbot
# Should show: wrcbot 1.0 961f5741c654 29 hours ago 120MB
```

### 2. Deploy via ArgoCD
```bash
# Apply the parent application (this will deploy all components)
kubectl apply -f argoapp/wrc-app.yaml

# Or deploy wrcbot individually
kubectl apply -f argoapp/wrcbotapp.yaml
```

### 3. Monitor Deployment
```bash
# Check ArgoCD applications
kubectl get applications -n argocd

# Check wrcbot pod status
kubectl get pods -n wrcbot -l app.kubernetes.io/name=wrcbot

# Check pod logs
kubectl logs -n wrcbot -l app.kubernetes.io/name=wrcbot
```

## Validation

### Manifest Validation
Both ArgoCD application manifests have been validated:
```bash
kubectl --dry-run=client -f argoapp/wrcbotapp.yaml apply  # ✓ Valid
kubectl --dry-run=client -f argoapp/wrc-app.yaml apply    # ✓ Valid
```

### Helm Chart Validation
```bash
cd helmchart/wrcbot
helm lint .          # ✓ No issues
helm template . --values values.yaml  # ✓ Renders correctly
```

## File Locations

```
/home/ec2-user/wrcbot/
├── argoapp/
│   ├── wrc-app.yaml         # Parent ArgoCD Application
│   ├── wrcbotapp.yaml       # WRCBot ArgoCD Application
│   ├── vaultapp.yaml        # Vault ArgoCD Application
│   ├── redisapp.yaml        # Redis ArgoCD Application
│   └── rabbitmqapp.yaml     # RabbitMQ ArgoCD Application
└── helmchart/
    └── wrcbot/
        ├── Chart.yaml
        ├── values.yaml      # Simplified configuration
        └── templates/
            ├── deployment.yaml    # Simplified deployment
            ├── service.yaml
            ├── configmap.yaml     # Transient storage config
            ├── _helpers.tpl       # Cleaned up helpers
            └── tests/
                └── test-connection.yaml
```

## Next Steps

1. **Test ArgoCD Deployment**: Deploy the application via ArgoCD and verify the pod starts successfully
2. **Bot Configuration**: Once the pod is running, configure the bot with actual secrets and settings
3. **Add Back Features**: Gradually add back features like persistence, health checks, and ingress as needed
4. **Production Readiness**: Configure proper resource limits, monitoring, and backup procedures

## Troubleshooting

### Common Issues
1. **Image Pull Errors**: Ensure `eval $(minikube docker-env)` was run and image exists locally
2. **Pod CrashLoop**: Check logs with `kubectl logs -n wrcbot -l app.kubernetes.io/name=wrcbot`
3. **ArgoCD Sync Issues**: Check ArgoCD UI or use `kubectl describe application wrcbot -n argocd`

### Debug Commands
```bash
# Check if image is available in minikube
eval $(minikube docker-env) && docker images | grep wrcbot

# Validate Helm chart
cd helmchart/wrcbot && helm lint . && helm template . --values values.yaml

# Check ArgoCD application status
kubectl get application wrcbot -n argocd -o yaml

# Get pod details
kubectl describe pod -n wrcbot -l app.kubernetes.io/name=wrcbot
```

## ArgoCD Access and Password Management

### Current Admin Credentials
- **Username**: `admin`
- **Password**: `admin123` (reset on 2025-06-30)

### Accessing ArgoCD UI
```bash
# Port forward to access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Then access: https://localhost:8080
# Accept the self-signed certificate warning
```

### Password Reset Process
If you forget the ArgoCD admin password, you can reset it:

1. **Method 1: Using Initial Admin Secret (if available)**
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

2. **Method 2: Reset via ArgoCD Secret**
   ```bash
   # Set password to 'admin123'
   kubectl patch secret argocd-secret -n argocd --type merge -p '{"data":{"admin.password":"JDJhJDEwJE8yOGN4WDhGZ0JZbDNWQ0VYd2owUy5uWVFCTXNEQTdELk1vcFRjYTg3SkRCMXNjRTdqSG0y"}}'
   
   # Restart ArgoCD server
   kubectl rollout restart deployment argocd-server -n argocd
   ```

3. **Method 3: Generate New Random Password**
   ```bash
   # Delete and recreate initial admin secret
   kubectl delete secret argocd-initial-admin-secret -n argocd
   kubectl create secret generic argocd-initial-admin-secret -n argocd --from-literal=password=$(openssl rand -base64 16)
   
   # Get the new password
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
   ```

## Deployment Steps

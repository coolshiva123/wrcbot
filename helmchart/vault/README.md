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
# SRE Task Platform

A containerized task-management application deployed on a single-node
k3s Kubernetes cluster running on AWS EC2.

The project demonstrates Kubernetes deployment, Helm, CI/CD,
observability, alerting, failure simulation, and incident response.

## Architecture

```text
                         Internet
                            |
                            | HTTP :80
                            v
                     +-------------+
                     |   Traefik   |
                     |   Ingress   |
                     +------+------+
                            |
                 +----------+----------+
                 |                     |
                 v                     v
          +-------------+       +-------------+
          |  Frontend   |       |   Task API  |
          |    nginx    | ----> |    Flask    |
          +-------------+       +-------------+
                 \                     /
                  \                   /
                   +-----------------+
                   |  k3s Cluster    |
                   |   (single node) |
                   +-----------------+

              Observability namespace
              +----------------------+
              | Prometheus           |
              | Grafana              |
              | Loki                 |
              | Promtail             |
              | Alertmanager         |
              +----------------------+

              CI/CD
              GitHub
                 |
                 v
          GitHub Actions
                 |
          Build & Push images
                 |
               GHCR
                 |
                 v
             EC2 / k3s
```

## Deployment

### Prerequisites

- AWS EC2 Ubuntu 22.04
- Docker
- k3s
- kubectl
- Helm
- Git
- GitHub account with GHCR access

### Kubernetes Deployment

The application is deployed using the Helm chart located at:

`helm/task-app/`

The chart manages:

- API and frontend Deployments
- Kubernetes Services
- Ingress
- ConfigMap
- Secret
- Resource requests and limits
- Liveness and readiness probes
- Prometheus alerting rules

Deploy or upgrade the application with:

```bash
sudo -E helm upgrade --install task-app ./helm/task-app
```

## CI/CD

GitHub Actions automates the build and deployment process whenever changes are pushed to the `main` branch.

Pipeline flow:

`Git Push → GitHub Actions → Build Images → Push to GHCR → SSH to EC2 → Helm Upgrade → Rollout Verification`

The workflow:

1. Checks out the repository.
2. Logs in to GitHub Container Registry (GHCR).
3. Builds the backend and frontend Docker images.
4. Pushes both images to GHCR.
5. Connects to the EC2 instance using SSH.
6. Runs the Helm deployment.
7. Waits for the Kubernetes deployments to successfully roll out.

### Container Registry

Images are stored in GitHub Container Registry:

- `ghcr.io/galacticgit007/task-api`
- `ghcr.io/galacticgit007/task-frontend`

### GitHub Actions Secrets

The workflow uses GitHub repository secrets for:

- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`
- `GHCR_TOKEN`

## Observability

The cluster uses the following monitoring stack:

- Prometheus — metrics collection and alerting
- Grafana — metrics visualization and dashboards
- Loki — centralized log storage
- Promtail — log collection from Kubernetes nodes/pods

The monitoring components are deployed in the `monitoring` namespace.

### Access

Grafana and Prometheus are kept private and are accessed through SSH port forwarding rather than exposing their ports publicly through the EC2 security group.

Grafana:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```
## Failure Scenarios and Incident Analysis

Two controlled failure scenarios were simulated to validate application and cluster recovery.

### Incident 1 — Application Pod CrashLoopBackOff

#### Scenario

The `task-api` Deployment was intentionally modified so that its container exited immediately after startup.

This simulated an application/container startup failure.

#### Detection

Kubernetes reported the pod transitioning through:

`Running → Error → Restarting → CrashLoopBackOff`

The restart count increased and the pod remained unready.

#### Recovery

The Deployment command override was removed, restoring the original container startup configuration.

The pod was then recreated successfully.

#### Final State

- `task-api`: `1/1 Running`
- `task-frontend`: `1/1 Running`
- Restart count: `0`

#### 5 Whys

1. **Why was the API unavailable?**  
   The API container repeatedly exited.

2. **Why did the container exit?**  
   Its startup command was intentionally configured to return exit code `1`.

3. **Why did Kubernetes restart it?**  
   Kubernetes detected the failed container and applied its restart policy.

4. **Why did the pod enter CrashLoopBackOff?**  
   Repeated container failures caused Kubernetes to apply increasing restart backoff.

5. **What is the corrective action?**  
   Restore the correct container startup command and investigate application startup failures through container logs.

---

### Incident 2 — k3s/Node Service Failure

#### Scenario

The k3s service running on the single Kubernetes node was intentionally stopped:

```bash
sudo systemctl stop k3s
```

#### Observed Behavior

Before the failure, the cluster was healthy:

```text
Node: Ready
task-api: 1/1 Running
task-frontend: 1/1 Running
```
#### After Failure / Recovery

The k3s service was restarted:

```bash
sudo systemctl start k3s
```

#### 5 Whys

1. **Why was Kubernetes temporarily unavailable?**  
   The k3s service on the node was stopped.

2. **Why did stopping k3s affect the cluster?**  
   The k3s service provides the Kubernetes control-plane components and API server on this node.

3. **Why did this affect the entire cluster?**  
   The environment uses a single-node Kubernetes cluster, so there was no second node to provide availability.

4. **Why was there no failover?**  
   No additional control-plane or worker nodes were configured in this evaluation environment.

5. **What is the corrective action?**  
   Use a multi-node Kubernetes cluster with redundant control-plane and worker capacity in a production environment to avoid a single point of failure.

## Runbook

This runbook provides basic troubleshooting and recovery procedures for the Kubernetes application, k3s cluster, Helm deployment, and monitoring stack.

### 1. Check Overall Cluster Health

Check the Kubernetes node:
``` bash
sudo kubectl get nodes
```
Check all workloads:
``` bash
sudo kubectl get pods -A
```
The node should be Ready and application pods should be Running.

### 2. Check Application Health

Check application pods:
``` bash
sudo kubectl get pods -n default
```
Check services:
``` bash
sudo kubectl get services -n default
```
Check ingress:
``` bash
sudo kubectl get ingress -n default
```
### 3. Troubleshoot a Failed Pod

Identify the affected pod:
``` bash
sudo kubectl get pods -n default
```
Inspect the pod:
``` bash
sudo kubectl describe pod <pod-name> -n default
```
Check application logs:
``` bash
sudo kubectl logs <pod-name> -n default
```
If the container has restarted, check the previous container logs:
``` bash
sudo kubectl logs <pod-name> -n default --previous
```
### 4. Troubleshoot CrashLoopBackOff

If a pod enters CrashLoopBackOff:

1. Identify the affected pod.
2. Inspect its status and events.
3. Check current and previous container logs.
4. Check the Deployment configuration.
5. Correct the underlying configuration or application issue.
6. Verify that the pod returns to Running.

Commands:
``` bash
sudo kubectl get pods -n default
sudo kubectl describe pod <pod-name> -n default
sudo kubectl logs <pod-name> -n default
sudo kubectl logs <pod-name> -n default --previous
```
Check the Deployment:
``` bash
sudo kubectl get deployment <deployment-name> -n default -o yaml
```
Verify recovery:
``` bash
sudo kubectl get pods -n default
```
### 5. Troubleshoot k3s

Check the k3s service:
``` bash
sudo systemctl status k3s
```
Check recent k3s logs:
``` bash
sudo journalctl -u k3s -n 100 --no-pager
```
Restart k3s if required:
``` bash
sudo systemctl restart k3s
```
Verify recovery:
``` bash
sudo kubectl get nodes
sudo kubectl get pods -A
```
The node should return to Ready state.

### 6. Helm Deployment Recovery

Check Helm releases:
``` bash
sudo -E helm list -A
```
Validate the chart before deployment:
``` bash
helm template task-app ./helm/task-app -n default
```
Deploy or reconcile the application:
``` bash
sudo -E helm upgrade --install task-app ./helm/task-app
```
Verify:
``` bash
sudo kubectl get pods -n default
sudo kubectl get ingress -n default
```
### 7. Check Monitoring Stack

Check monitoring components:
``` bash
sudo kubectl get pods -n monitoring
```
Check Prometheus rules:
``` bash
sudo kubectl get prometheusrule -n monitoring
```
Check the application alert rules:
``` bash
sudo kubectl get prometheusrule task-app-alerts -n monitoring -o yaml
```
The application has the following Prometheus alerts:

- PodRestartDetected
- PodNotReady
- HighNodeCPU
- PodCrashLooping

### 8. Access Grafana and Prometheus

Monitoring interfaces are not exposed publicly.

Grafana:
``` bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```
Prometheus:
``` bash
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
```
SSH port forwarding is used to access these services from the administrator's local machine.

### 9. Recovery Verification

After performing a recovery action, verify:
``` bash
sudo kubectl get nodes
sudo kubectl get pods -A
```
For the application, confirm:

- Node is Ready
- task-api is 1/1 Running
- task-frontend is 1/1 Running
- No unexpected pod restarts are occurring
- Ingress is available
- Prometheus and Grafana are operational

## Security Considerations

### Network Security

- Only HTTP port 80 is exposed for application traffic.
- Grafana and Prometheus are not publicly exposed.
- Monitoring interfaces are accessed through SSH port forwarding.
- SSH access to the EC2 instance is controlled through the AWS Security Group.

### Kubernetes Security

- Kubernetes RBAC is enabled through the default k3s configuration.
- Application workloads run in the `default` namespace.
- No privileged containers are intentionally configured for the application.
- Resource requests and limits are configured for application and monitoring workloads.

### Secrets

- No real credentials, private keys, or access tokens are committed to the repository.
- GitHub Actions credentials are stored as GitHub repository secrets.
- Kubernetes secrets are managed separately from source-code credentials.
- The current application Secret contains a non-sensitive placeholder value for evaluation purposes.

### Container Images

Application images are stored in GitHub Container Registry (GHCR).


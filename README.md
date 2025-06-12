# SpaceX Data Platform

This repository contains a prototype for a scalable data platform using SpaceX launch data. It demonstrates a theoretical AWS architecture (data lake + Redshift) and a local Kubernetes-based PoC (Docker Desktop) with Apache Airflow, PostgreSQL (mock warehouse), ETL scripts, and monitoring via Prometheus and Grafana.

## AWS Architecture:
```text
+----------------------+        +------------------------+        +-----------------------+
|   Ingestion Layer    |        |    Storage Layer       |        |   Processing Layer    |
|                      |        |                        |        |                       |
|  +----------------+  |        |  +------------------+  |        |  +-----------------+  |
|    SpaceX API        |  --->  |  S3 Raw Zone           |  --->  |  AWS Glue/EMR         |  
|   (Lambda/AppFlow)   |        |  (raw JSON files)      |        |  jobs to clean/       |
|  +----------------+  |        |  +------------------+  |        |  transform data       |
|                      |        |          |             |        |  +---------------+    |
|                      |        |          v             |        |  | Redshift           |  
|                      |        |  +------------------+  |        |  | COPY or Spectrum   | 
|                      |        |   S3 Curated Zone      |        |  +---------------+    |
|                      |        |  (cleaned/parquet)     |        |                       | 
|                      |        |  +------------------+  |        |                       |
+----------------------+        +------------------------+        +-----------------------+
                                                                          |
                                                                          v
                                               +-------------------------------------------+
                                               |   Data Warehouse / Query Layer            |
                                               |                                           |
                                               |  +------------------+      +-------------+|
                                               |     Amazon Redshift   <-->    Redshift    |
                                               |    (leader + compute)         Spectrum    |
                                               |  +------------------+      +-------------+|
                                               |  +------------------+                     |
                                               |  | Amazon Athena    |                     |
                                               |  +------------------+                     |
                                               +-------------------------------------------+
                                                                          |
                                                                          v
                                               +-------------------------------------------+
                                               |   Consumption Layer                       |
                                               |                                           |
                                               |  +------------------+   +---------------+ |
                                               |  | QuickSight /     |   | Other BI      | |
                                               |  | Looker / etc.    |   | Tools         | |
                                               |  +------------------+   +---------------+ |
                                               +-------------------------------------------+

Security / Network Considerations:
- Entire architecture runs in a private VPC:
   - S3 buckets (Raw and Curated) with IAM policies granting only specific roles access.
   - Redshift in private subnets; use subnet group and security groups to restrict access.
- IAM Roles with least-privilege:
   * Lambda/AppFlow role: write to S3 Raw zone only.
   * Glue/EMR roles: read from S3 Raw, write to S3 Curated or load into Redshift.
   * Redshift IAM role: permission to read from S3 (for COPY or Spectrum).
- Encryption:
   * S3: Server-Side Encryption with AWS KMS (SSE-KMS).
   * Redshift: Encryption at rest via KMS.
   * Data in transit: TLS for all service endpoints (API calls, JDBC/ODBC to Redshift).
- Monitoring & Auditing:
   * CloudWatch Logs/Metrics for Lambda, Glue jobs, Redshift queries.
   * CloudTrail for auditing API calls across services.
   * (Optional) VPC Flow Logs for network-level visibility.
- VPC Routing:
   * Redshift Enhanced VPC Routing enabled for secure data traffic.
   * NAT Gateways for any outbound internet access needed (e.g., for Lambda or EMR bootstrap).
- Networking components (in a real deployment):
   * Subnet groups for Redshift in private subnets.
   * Security groups: restrict inbound to only allowed sources (e.g., analytics bastion or specific client IPs).
   * Endpoint configurations: VPC endpoints for S3 to keep traffic within AWS network.

Terraform Snippet for Redshift (example):
- File: `aws/terraform/redshift_cluster.tf`
- Defines an `aws_redshift_cluster` resource with:
   * `cluster_identifier`, `database_name`, `master_username`/`master_password` (store in Secrets Manager in production)
   * `node_type = "ra3.xlplus"`, `cluster_type = "multi-node"`, `number_of_nodes`
   * `publicly_accessible = false`, `encrypted = true`
   * In a full deployment, also add:
     - `aws_redshift_subnet_group`, `aws_security_group`
     - `aws_iam_role` for S3 access
     - `aws_secretsmanager_secret` for credentials
     - Possibly Parameter Group settings, Enhanced VPC Routing, maintenance windows, logging settings, etc.

Data Flow Summary:
1. **SpaceX API** → (via AWS Lambda or AppFlow) → **S3 Raw Zone**
2. **S3 Raw Zone** → (via AWS Glue or EMR jobs) → **S3 Curated Zone** (e.g., Parquet files), or directly → **Redshift** via `COPY`.
3. **S3 Curated Zone** → Redshift via `COPY`, or queried via **Redshift Spectrum** (external tables).
4. **Analytics/Consumption** → Query data with **Amazon Redshift** or **Amazon Athena** over S3; visualize in **QuickSight**, Looker, or other BI tools.
```

## Repository Structure
spacex-data-platform/
├── aws/
│   └── terraform/
│       └── redshift_cluster.tf       # Terraform snippet for Redshift cluster
├── k8s/
│   ├── postgres/
│   │   └── postgres-deployment.yaml   # Kubernetes manifest for Postgres
│   ├── airflow/
│   │   └── values.yaml               # Helm values for Airflow deployment
│   ├── monitoring/
│   │   ├── statsd-exporter.yaml      # StatsD exporter Deployment & Service
│   │   ├── statsd-servicemonitor.yaml# ServiceMonitor for StatsD exporter
│   │   ├── postgres-exporter.yaml    # Postgres exporter Deployment & Service
│   │   └── postgres-servicemonitor.yaml # ServiceMonitor for Postgres exporter
│   └── README_K8s.md                 # Overview of applying k8s manifests
├── etl/
│   ├── Dockerfile                    # Dockerfile for ETL image
│   ├── extract_spacex.py             # ETL script to fetch and load SpaceX data
│   └── requirements.txt              # Python dependencies
├── dags/
│   └── core_usage_dag.py             # Airflow DAG for ETL orchestration
├── sql/
│   └── queries.sql                   # Example SQL queries for core reuse analysis
├── .gitignore                        # Ignore patterns
└── README.md                         # This file


## Part 2: Kubernetes Orchestration & Container Management

This section explains how to deploy a local Kubernetes environment (Docker Desktop on Mac) with:
- Apache Airflow as orchestrator
- PostgreSQL as metadata DB and mock data warehouse
- ETL containers for ingestion
- Monitoring stack (Prometheus, Grafana, exporters)

### 1. Prerequisites
- Docker Desktop with Kubernetes enabled.
- CLI tools: `kubectl`, `helm`, `docker`.
- Ensure `kubectl config current-context` is `docker-desktop`.

### 2. Namespaces
Create isolated namespaces:
```bash
kubectl create namespace data-platform
kubectl create namespace airflow
kubectl create namespace monitoring
```

### 3. Deploy PostgreSQL (Mock Warehouse & Airflow Metadata DB)
Apply the manifest:
```bash
    kubectl apply -f k8s/postgres/postgres-deployment.yaml
```

- This creates a Secret (pg-secret), PVC (postgres-pvc), Deployment, and Service for Postgres in data-platform namespace.
- Postgres listens on postgres.data-platform.svc.cluster.local:5432
- To connect locally for testing:
```bash
    kubectl -n data-platform port-forward svc/postgres 5432:5432
    psql postgresql://admin:postgres_pass@localhost:5432/spacexdb
```

### 4. Build ETL Docker Image
From project root:
```bash
cd etl/
docker build -t spacex-etl:latest .
```
- This image contains extract_spacex.py, which fetches launch data from SpaceX API, transforms it, and loads into Postgres using environment variables:
    PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD.

### 5. Deploy Monitoring Exporters
#### 5.1 StatsD Exporter (for Airflow metrics)
    ```bash
        kubectl apply -f k8s/monitoring/statsd-exporter.yaml
        kubectl apply -f k8s/monitoring/statsd-servicemonitor.yaml
    ```
    - Deploys StatsD exporter in monitoring namespace, listening on UDP port 9125.
    - Prometheus (via ServiceMonitor) scrapes its HTTP metrics endpoint.

#### 5.2 Postgres Exporter.
```bash
kubectl apply -f k8s/monitoring/postgres-exporter.yaml
kubectl apply -f k8s/monitoring/postgres-servicemonitor.yaml
- Runs in data-platform namespace; exposes metrics on port 9187 for Postgres.
```

### 6. Install Prometheus & Grafana.
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install kube-prom-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword="admin"
```

- Prometheus scrapes Kubernetes metrics, StatsD exporter, and Postgres exporter.
- Grafana is available for dashboards.
- Port-forward:
```bash
    kubectl -n monitoring port-forward svc/kube-prom-stack-prometheus 9090:9090
    kubectl -n monitoring port-forward svc/kube-prom-stack-grafana 3000:80
```

### 7. Deploy Apache Airflow via Helm
```bash
helm repo add apache-airflow https://airflow.apache.org
helm repo update
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  -f k8s/airflow/values.yaml
```

- Uses LocalExecutor, external Postgres at postgres.data-platform.svc.cluster.local:5432.
- Enables StatsD metrics to statsd-exporter.monitoring.svc.cluster.local:9125.
- DAGs will be provided via ConfigMap or Git-Sync.
- Port-forward Airflow UI:
```bash
    kubectl -n airflow port-forward svc/airflow-webserver 8080:8080
```

### 8. Deploy ETL DAG to Airflow
#### 8.1. Create ConfigMap for DAG:
```bash
    kubectl -n airflow create configmap airflow-dags --from-file=dags/core_usage_dag.py
```

#### 8.2. Patch Airflow deployments (webserver, scheduler) to mount the ConfigMap under /opt/airflow/dags. For example:
```bash
    kubectl -n airflow patch deployment airflow-webserver \
    --patch '{"spec":{"template":{"spec":{"volumes":[{"name":"dags","configMap":{"name":"airflow-dags"}}],"containers":[{"name":"webserver","volumeMounts":[{"name":"dags","mountPath":"/opt/airflow/dags"}]}]}}}}'
```

#### 8.3. In Airflow UI, unpause and trigger the core_usage_dag.
    - The DAG uses KubernetesPodOperator to run the spacex-etl:latest image, passing environment variables for DB connection.

### 9. Networking and Access
- By default, pods in airflow namespace can reach services in data-platform namespace (DNS: postgres.data-platform.svc.cluster.local).
- If using NetworkPolicies, ensure rules allow:
    * Airflow → Postgres on port 5432
    * Airflow → StatsD exporter UDP 9125
    * Prometheus → exporters in their namespaces
- No special ingress is needed for internal service-to-service access.

### 10. Monitoring & Logging
- Prometheus UI: http://localhost:9090; verify targets: kubelets, StatsD exporter, Postgres exporter.
- Grafana UI: http://localhost:3000 (admin/admin); import dashboards for:
    * Kubernetes cluster metrics
    * Airflow StatsD metrics (DAG durations, task successes/failures)
    * Postgres performance metrics (if exporter deployed)
- Airflow Logs: In Airflow Web UI, under each task instance.
- Pod Logs: kubectl -n airflow logs <pod-name> for scheduler/webserver/worker or ETL pods.
- Centralized Logging (optional): Deploy Loki/Promtail to collect logs, view via Grafana Explore.

### 11. Commands Summary
# Pre-check: Kubernetes enabled
```bash
kubectl config current-context
kubectl get nodes
```

# Namespaces
```bash
kubectl create namespace data-platform
kubectl create namespace airflow
kubectl create namespace monitoring
```

# Deploy Postgres
```bash
kubectl apply -f k8s/postgres/postgres-deployment.yaml
```

# Build ETL image
```bash
cd etl/
docker build -t spacex-etl:latest .
cd ..
```

# Deploy exporters
```bash
kubectl apply -f k8s/monitoring/statsd-exporter.yaml
kubectl apply -f k8s/monitoring/statsd-servicemonitor.yaml
kubectl apply -f k8s/monitoring/postgres-exporter.yaml
kubectl apply -f k8s/monitoring/postgres-servicemonitor.yaml
```

# Install Prometheus & Grafana
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install kube-prom-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword="admin"
```

# Install Airflow
```bash
helm repo add apache-airflow https://airflow.apache.org
helm repo update
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  -f k8s/airflow/values.yaml
```

# Deploy DAG
```bash
kubectl -n airflow create configmap airflow-dags --from-file=dags/core_usage_dag.py
# Patch deployments to mount DAGs
# (See instructions above)
```

# Port-forward UIs
```bash
kubectl -n airflow port-forward svc/airflow-webserver 8080:8080
kubectl -n monitoring port-forward svc/kube-prom-stack-prometheus 9090:9090
kubectl -n monitoring port-forward svc/kube-prom-stack-grafana 3000:80
```

    
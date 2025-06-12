# Kubernetes Manifests and Helm Values

This folder contains Kubernetes manifests and Helm values files for deploying:
- PostgreSQL (namespace: data-platform)
- Apache Airflow (namespace: airflow)
- Monitoring stack components (namespace: monitoring)

## Namespaces
We use:
- `data-platform` for Postgres and related database exporters
- `airflow` for Airflow components (webserver, scheduler, etc.)
- `monitoring` for Prometheus, Grafana, exporters

## Applying Manifests
1. Ensure Docker Desktop Kubernetes is enabled and `kubectl` context is `docker-desktop`. (All the following commands should be running in a bash terminal)
2. Create namespaces:
```bash
   kubectl create namespace data-platform
   kubectl create namespace airflow
   kubectl create namespace monitoring
```

3. Deploy Postgres:
```bash
    kubectl apply -f k8s/postgres/postgres-deployment.yaml
```

4. Build ETL Docker image locally: 
```bash
    cd etl/
    docker build -t spacex-etl:latest .
```

5. Deploying monitoring exportes:
```bash
    kubectl apply -f k8s/monitoring/statsd-exporter.yaml
    kubectl apply -f k8s/monitoring/statsd-servicemonitor.yaml
    kubectl apply -f k8s/monitoring/postgres-exporter.yaml
    kubectl apply -f k8s/monitoring/postgres-servicemonitor.yaml
```

6. Install Prometheus & Grafana:
```bash
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    helm install kube-prom-stack prometheus-community/kube-prometheus-stack \
    --namespace monitoring --create-namespace \
    --set grafana.adminPassword="admin"
```

7. Install Airflow via Helm:
```bash
    helm repo add apache-airflow https://airflow.apache.org
    helm repo update
    helm install airflow apache-airflow/airflow \
    --namespace airflow \
    -f k8s/airflow/values.yaml
```

8. Deploy DAGs to Airflow (ConfigMap or Git-Sync). Example ConfigMap:
```bash
    kubectl -n airflow create configmap airflow-dags --from-file=../dags/core_usage_dag.py
    # Then patch Airflow deployments to mount the ConfigMap at /opt/airflow/dags
```

9. Port-forward UIs:
```bash 
    kubectl -n airflow port-forward svc/airflow-webserver 8080:8080
    kubectl -n monitoring port-forward svc/kube-prom-stack-prometheus 9090:9090
    kubectl -n monitoring port-forward svc/kube-prom-stack-grafana 3000:80
```
     
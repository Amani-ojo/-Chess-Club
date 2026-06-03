# ChessMate AI Pipeline — AWS Production Deployment Guide

**Branch:** `feature/ai-pipeline`  
**Date:** 4 April 2026  
**Target:** AWS — Production environment ready for main project integration

---

## 1. Architecture Overview

```
                        ┌─────────────────────────────────────────────────┐
                        │                    AWS VPC                       │
                        │                                                  │
  Users / Main Project  │  ┌──────────┐     ┌─────────────────────────┐  │
  ──────────────────────┼─▶│   ALB    │────▶│   ECS Cluster (Fargate) │  │
                        │  │(port 443)│     │                         │  │
                        │  └──────────┘     │  ┌───────────────────┐  │  │
                        │                   │  │  Django Web Task  │  │  │
                        │  ┌────────────┐   │  │  (2+ replicas)    │  │  │
                        │  │ Route 53   │   │  └─────────┬─────────┘  │  │
                        │  │ (DNS)      │   │            │            │  │
                        │  └────────────┘   │  ┌─────────▼─────────┐  │  │
                        │                   │  │  Celery Worker    │  │  │
                        │  ┌────────────┐   │  │  Task  (2+        │  │  │
                        │  │    ACM     │   │  │  replicas)        │  │  │
                        │  │ (TLS cert) │   │  │  + Stockfish EXE  │  │  │
                        │  └────────────┘   │  └─────────┬─────────┘  │  │
                        │                   └────────────┼────────────┘  │
                        │                                │               │
                        │  ┌─────────────────────────────▼─────────────┐ │
                        │  │              Private Subnet                │ │
                        │  │                                            │ │
                        │  │  ┌──────────────┐  ┌──────────────────┐  │ │
                        │  │  │  RDS          │  │  ElastiCache     │  │ │
                        │  │  │  PostgreSQL   │  │  Redis           │  │ │
                        │  │  │  (Multi-AZ)   │  │  (Celery Broker) │  │ │
                        │  │  └──────────────┘  └──────────────────┘  │ │
                        │  └────────────────────────────────────────────┘ │
                        │                                                  │
                        │  ┌─────────────────────────────────────────────┐│
                        │  │  S3 Bucket (static files + media)           ││
                        │  └─────────────────────────────────────────────┘│
                        └─────────────────────────────────────────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │  Secrets    │
                                    │  Manager    │
                                    │ (API tokens)│
                                    └─────────────┘
```

---

## 2. Required AWS Services

### 2.1 Compute — Amazon ECS (Fargate)

**Two task definitions** inside one ECS cluster:

| Task | CPU | Memory | Replicas | Notes |
|---|---|---|---|---|
| `chessmate-web` | 512 | 1024 MB | 2 min | Django + Gunicorn |
| `chessmate-celery-worker` | 1024 | 2048 MB | 2 min | Celery + Stockfish binary |

Fargate is recommended over EC2 for this project because:
- No servers to patch or manage
- Workers scale independently of the web layer
- Pay only for task runtime (Stockfish workers can scale to zero)

**Why Celery workers need more memory:**  
Stockfish loads the opening book and hash tables into RAM. At `STOCKFISH_HASH_MB=256` and depth 20, each worker process uses ~400–600 MB. Set `STOCKFISH_HASH_MB=128` per worker if memory is constrained.

---

### 2.2 Container Registry — Amazon ECR

Two repositories:

```
chessmate/web-app        ← Django + Gunicorn image
chessmate/celery-worker  ← same base image + Stockfish Linux binary
```

The Stockfish Linux binary (`stockfish-ubuntu-x86-64-avx2`) must be baked into the **celery-worker image** at build time:

```dockerfile
# Dockerfile.worker
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stockfish binary
COPY bin/stockfish_linux/stockfish /usr/local/bin/stockfish
RUN chmod +x /usr/local/bin/stockfish

COPY . .

CMD ["celery", "-A", "chess_club", "worker", "--loglevel=info", "--concurrency=2"]
```

> **Important:** The Windows `.exe` binary used in development will not run on Linux containers. Download the Linux AVX2 build from [stockfishchess.org/download](https://stockfishchess.org/download) and add it to the worker image.

---

### 2.3 Database — Amazon RDS (PostgreSQL)

| Setting | Value |
|---|---|
| Engine | PostgreSQL 16 |
| Instance | `db.t3.medium` (start here, scale up if needed) |
| Multi-AZ | Yes — automatic failover |
| Storage | 20 GB GP3, auto-scaling enabled |
| Backups | 7-day automated snapshots |
| Subnet | Private — no public endpoint |

Update `settings.py` to use `dj-database-url` with the RDS connection string pulled from Secrets Manager.

---

### 2.4 Cache + Celery Broker — Amazon ElastiCache (Redis)

| Setting | Value |
|---|---|
| Engine | Redis 7.x |
| Node type | `cache.t3.micro` (development) / `cache.t3.small` (production) |
| Cluster mode | Disabled (single node is sufficient for this workload) |
| Subnet | Private |

```python
# settings.py — production
CELERY_BROKER_URL     = os.environ['REDIS_URL']   # injected from Secrets Manager
CELERY_RESULT_BACKEND = os.environ['REDIS_URL']
```

---

### 2.5 Secrets — AWS Secrets Manager

Store all credentials here. Never hard-code in `settings.py` or commit to git.

| Secret name | Value |
|---|---|
| `chessmate/lichess-api-token` | Lichess OAuth token |
| `chessmate/django-secret-key` | Django `SECRET_KEY` |
| `chessmate/db-password` | RDS PostgreSQL password |
| `chessmate/redis-url` | `redis://<elasticache-endpoint>:6379/0` |

ECS tasks retrieve secrets at startup via **ECS Secrets injection** (no SDK calls needed in code):

```json
// ECS Task Definition — environment section
{
  "secrets": [
    {
      "name": "LICHESS_API_TOKEN",
      "valueFrom": "arn:aws:secretsmanager:eu-west-1:123456789:secret:chessmate/lichess-api-token"
    },
    {
      "name": "SECRET_KEY",
      "valueFrom": "arn:aws:secretsmanager:eu-west-1:123456789:secret:chessmate/django-secret-key"
    }
  ]
}
```

---

### 2.6 Load Balancer — Application Load Balancer (ALB)

- HTTPS on port 443, HTTP redirects to HTTPS
- TLS certificate from **ACM (AWS Certificate Manager)** — free, auto-renews
- Target group → `chessmate-web` ECS tasks on port 8000
- Health check: `GET /health/` (add a simple view that returns 200)

---

### 2.7 Static Files — Amazon S3 + CloudFront

```python
# settings.py — production (using django-storages)
DEFAULT_FILE_STORAGE  = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE   = 'storages.backends.s3boto3.S3StaticStorage'
AWS_STORAGE_BUCKET_NAME = 'chessmate-static'
AWS_S3_REGION_NAME    = 'eu-west-1'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
```

Run once after deploy:

```bash
python manage.py collectstatic --no-input
```

---

### 2.8 Networking — VPC

| Subnet type | Contains |
|---|---|
| Public subnets (2 AZs) | ALB, NAT Gateway |
| Private subnets (2 AZs) | ECS tasks, RDS, ElastiCache |

**Security group rules (minimum):**

| Resource | Inbound | Outbound |
|---|---|---|
| ALB | 443 from `0.0.0.0/0` | 8000 to ECS web SG |
| ECS web tasks | 8000 from ALB SG | 5432 to RDS SG, 6379 to Redis SG, 443 to internet |
| ECS celery workers | None | 5432 to RDS SG, 6379 to Redis SG, 443 to Lichess API |
| RDS | 5432 from ECS SGs only | — |
| ElastiCache | 6379 from ECS SGs only | — |

---

### 2.9 Monitoring — CloudWatch

| What to monitor | Metric / Log group |
|---|---|
| Task failures | `/ecs/chessmate-celery-worker` — filter for `ERROR` |
| Analysis queue depth | Celery task count via CloudWatch custom metric |
| RDS CPU / connections | Built-in RDS metrics |
| Memory per worker | ECS `MemoryUtilization` |
| ALB 5xx errors | `HTTPCode_Target_5XX_Count` — alarm at > 5 in 5 min |

---

## 3. Production `settings.py` Changes

```python
import os
import dj_database_url

DEBUG = False
ALLOWED_HOSTS = [os.environ['DOMAIN_NAME']]

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ['DATABASE_URL'],
        conn_max_age=600,
        ssl_require=True,
    )
}

# Celery / Redis
CELERY_BROKER_URL     = os.environ['REDIS_URL']
CELERY_RESULT_BACKEND = os.environ['REDIS_URL']

# Lichess
LICHESS_API_TOKEN    = os.environ['LICHESS_API_TOKEN']
LICHESS_API_BASE_URL = 'https://lichess.org/api'

# Stockfish — Linux binary path inside the container
STOCKFISH_PATH    = '/usr/local/bin/stockfish'
STOCKFISH_DEPTH   = 20
STOCKFISH_THREADS = 2
STOCKFISH_HASH_MB = 128

# Static files (S3)
DEFAULT_FILE_STORAGE  = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE   = 'storages.backends.s3boto3.S3StaticStorage'
AWS_STORAGE_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
```

---

## 4. CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS ECS

on:
  push:
    branches: [develop, main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: python -m pytest -v   # must pass before any deploy

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id:     ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-1

      - name: Build and push Docker images to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
          docker build -f Dockerfile.web    -t $ECR_REGISTRY/chessmate/web-app:$GITHUB_SHA .
          docker build -f Dockerfile.worker -t $ECR_REGISTRY/chessmate/celery-worker:$GITHUB_SHA .
          docker push $ECR_REGISTRY/chessmate/web-app:$GITHUB_SHA
          docker push $ECR_REGISTRY/chessmate/celery-worker:$GITHUB_SHA

      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster chessmate --service chessmate-web    --force-new-deployment
          aws ecs update-service --cluster chessmate --service chessmate-worker --force-new-deployment
```

**Deploy flow:**
1. `git push origin develop` → GitHub Actions runs all 27 tests
2. Tests pass → Docker images built and pushed to ECR
3. ECS performs a rolling deployment (zero downtime) — old tasks stay up until new ones are healthy

---

## 5. Estimated Monthly Cost (AWS eu-west-1)

| Service | Spec | Est. cost / month |
|---|---|---|
| ECS Fargate — web (2 tasks) | 0.5 vCPU, 1 GB, 730 hrs | ~$15 |
| ECS Fargate — workers (2 tasks) | 1 vCPU, 2 GB, 730 hrs | ~$55 |
| RDS PostgreSQL | db.t3.medium, Multi-AZ | ~$70 |
| ElastiCache Redis | cache.t3.micro | ~$15 |
| ALB | 1 LCU avg | ~$18 |
| S3 + CloudFront | 5 GB storage, 10 GB transfer | ~$5 |
| Secrets Manager | 4 secrets | ~$2 |
| CloudWatch | Logs + metrics | ~$5 |
| **Total estimate** | | **~$185 / month** |

> Costs drop significantly using Reserved Instances (1-year term saves ~30%) or if workers are scaled to zero when no analysis jobs are queued.

---

## 6. Pre-Launch Checklist

- [ ] Linux Stockfish binary added to `Dockerfile.worker`
- [ ] All secrets stored in AWS Secrets Manager (no values in git)
- [ ] `DEBUG = False` in production settings
- [ ] `ALLOWED_HOSTS` set to the actual domain
- [ ] RDS is in a private subnet — no public endpoint
- [ ] ElastiCache is in a private subnet
- [ ] ALB HTTPS certificate issued via ACM
- [ ] `python manage.py migrate` run as part of ECS startup or deploy step
- [ ] `python manage.py collectstatic` run and S3 bucket accessible
- [ ] CloudWatch alarm on ALB 5xx errors
- [ ] CloudWatch alarm on Celery worker task failures
- [ ] GitHub Actions pipeline: tests must pass before deploy
- [ ] At least 2 Celery worker replicas (one per AZ) for availability

---

## 7. Integration Point for the Main Project

Once deployed, the main `chess_club` project connects to the pipeline by:

1. Pointing `CELERY_BROKER_URL` at the same ElastiCache Redis endpoint
2. Importing and calling the tasks:

```python
from ai_pipeline.tasks import fetch_lichess_games_task, generate_insights_task

# Trigger game import for a member (e.g. from an admin action or webhook)
fetch_lichess_games_task.delay(member.lichess_username, member.pk)

# Trigger insight regeneration after a batch of analyses
generate_insights_task.delay(member.pk)
```

3. Linking to the analysis views from existing member profile pages:

```python
# In any existing template:
<a href="{% url 'ai_pipeline:player_insights' member.pk %}">View Coaching Insights</a>
<a href="{% url 'ai_pipeline:game_analysis' game.pk %}">View Game Analysis</a>
```

The `ai_pipeline` app never modifies any `club` app models — integration is additive and non-breaking.

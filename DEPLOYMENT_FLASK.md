# Smart Buddy - Production Deployment Guide (v2.0)

Complete guide for deploying Smart Buddy to production environments with Flask backend.

## 🚀 Quick Start Options

### 1. Local Development (Fastest)
```bash
python server_flask.py
```
✅ Access: http://127.0.0.1:8000  
✅ Metrics: http://127.0.0.1:8000/metrics

### 2. Production WSGI (Recommended for Local)
```bash
# Windows (Waitress)
waitress-serve --port=8000 --threads=4 wsgi:app

# Linux/Mac (Gunicorn)
gunicorn wsgi:app --workers 4 --bind 0.0.0.0:8000 --timeout 120
```

### 3. Docker (Best for Cloud)
```bash
docker build -f Dockerfile.production -t smart-buddy .
docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key smart-buddy
```

## 📦 Installation

```bash
# Clone and setup
cd "Smart Buddy"
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set API key
$env:GOOGLE_API_KEY = "your_google_api_key"  # PowerShell
# export GOOGLE_API_KEY="your_google_api_key"  # Bash
```

## 🐳 Docker Deployment

### Local Testing
```bash
# Build
docker build -f Dockerfile.production -t smart-buddy:latest .

# Run
docker run -d \
  --name smart-buddy \
  -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key \
  smart-buddy:latest

# Check logs
docker logs smart-buddy

# Test
curl http://localhost:8000/health
```

### Docker Compose (with Nginx)
```bash
# Standard deployment
docker-compose up -d

# With Nginx reverse proxy
docker-compose --profile production up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## ☁️ Cloud Deployment

### Google Cloud Run (Recommended - Serverless)

**Step 1: Setup**
```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

**Step 2: Deploy**
```bash
# Deploy from source (auto-builds)
gcloud run deploy smart-buddy \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=your_api_key \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 10

# Get URL
gcloud run services describe smart-buddy \
  --region us-central1 \
  --format 'value(status.url)'
```

**Step 3: Test**
```bash
SERVICE_URL=$(gcloud run services describe smart-buddy --region us-central1 --format 'value(status.url)')

curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"Hello Smart Buddy!","mode":"general"}'
```

### Azure Container Apps

**Step 1: Setup**
```bash
# Install Azure CLI
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

# Login
az login

# Create resource group
az group create --name smart-buddy-rg --location eastus

# Create container registry
az acr create \
  --resource-group smart-buddy-rg \
  --name smartbuddyacr \
  --sku Basic \
  --admin-enabled true
```

**Step 2: Build & Push**
```bash
# Build in Azure (recommended)
az acr build \
  --registry smartbuddyacr \
  --image smart-buddy:latest \
  --file Dockerfile.production .

# Or build locally and push
docker build -f Dockerfile.production -t smart-buddy:latest .
az acr login --name smartbuddyacr
docker tag smart-buddy:latest smartbuddyacr.azurecr.io/smart-buddy:latest
docker push smartbuddyacr.azurecr.io/smart-buddy:latest
```

**Step 3: Deploy**
```bash
# Create container app environment
az containerapp env create \
  --name smart-buddy-env \
  --resource-group smart-buddy-rg \
  --location eastus

# Deploy app
az containerapp create \
  --name smart-buddy \
  --resource-group smart-buddy-rg \
  --environment smart-buddy-env \
  --image smartbuddyacr.azurecr.io/smart-buddy:latest \
  --registry-server smartbuddyacr.azurecr.io \
  --target-port 8000 \
  --ingress external \
  --secrets google-api-key=your_google_api_key \
  --env-vars GOOGLE_API_KEY=secretref:google-api-key \
  --cpu 1.0 \
  --memory 2Gi \
  --min-replicas 1 \
  --max-replicas 10

# Get URL
az containerapp show \
  --name smart-buddy \
  --resource-group smart-buddy-rg \
  --query properties.configuration.ingress.fqdn \
  --output tsv
```

### AWS ECS Fargate

**Step 1: Setup**
```bash
# Install AWS CLI
# https://aws.amazon.com/cli/

# Configure
aws configure

# Create ECR repository
aws ecr create-repository \
  --repository-name smart-buddy \
  --region us-east-1
```

**Step 2: Build & Push**
```bash
# Get ECR login
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -f Dockerfile.production -t smart-buddy:latest .
docker tag smart-buddy:latest \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-buddy:latest
docker push \
  YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smart-buddy:latest
```

**Step 3: Deploy (via Console or IaC)**
- Create ECS Cluster (Fargate)
- Create Task Definition with your ECR image
- Set environment variable: GOOGLE_API_KEY
- Configure service with load balancer
- Set min/max tasks for auto-scaling

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | ✅ Yes | - | Google Gemini API key |
| `PORT` | No | 8000 | Server port |
| `LOG_LEVEL` | No | INFO | DEBUG, INFO, WARNING, ERROR |
| `ENVIRONMENT` | No | development | production, development |

### Production Settings

**Gunicorn Configuration** (Linux/Mac)
```bash
gunicorn wsgi:app \
  --workers 4 \
  --threads 2 \
  --worker-class sync \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile -
```

**Waitress Configuration** (Windows)
```bash
waitress-serve \
  --port=8000 \
  --threads=4 \
  --channel-timeout=120 \
  --connection-limit=100 \
  wsgi:app
```

## 📊 API Endpoints

### Health Check
```bash
GET /health

Response: {"status": "ok", "service": "Smart Buddy"}
```

### Chat
```bash
POST /chat
Content-Type: application/json

{
  "user_id": "user123",
  "session_id": "session456",
  "message": "What is machine learning?",
  "mode": "general"  // Optional: general, mentor, bestfriend, or auto-routing
}

Response: {
  "reply": "Machine learning is...",
  "trace_id": "api_1234567890",
  "mode": "general",
  "latency_ms": 245.67
}
```

### Metrics Dashboard
```bash
GET /metrics

Response: HTML dashboard with performance metrics
- Request latency (p50, p95, p99, p999)
- Token usage by mode
- Error rates
- Intent distribution
```

### User Data
```bash
GET /tasks/<user_id>      # User's tasks
GET /events/<user_id>     # User's events
GET /mentor/<user_id>     # Mentor content
```

## 🧪 Testing

### Local Testing
```powershell
# PowerShell
$body = @{
    user_id = 'test_user'
    message = 'Explain quantum computing'
    mode = 'mentor'
} | ConvertTo-Json

Invoke-WebRequest `
  -Uri http://localhost:8000/chat `
  -Method POST `
  -Body $body `
  -ContentType 'application/json'
```

```bash
# Bash/Linux
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "Explain quantum computing",
    "mode": "mentor"
  }'
```

### Load Testing
```bash
# Install Apache Bench
# Windows: Download from Apache website
# Linux: apt-get install apache2-utils

# Test 1000 requests, 10 concurrent
ab -n 1000 -c 10 -p chat_payload.json \
  -T application/json \
  http://localhost:8000/chat
```

## 🔒 Security Checklist

- [ ] **API Keys**: Use secrets manager (Cloud Secret Manager, Azure Key Vault, AWS Secrets Manager)
- [ ] **HTTPS**: Enable SSL/TLS with valid certificates
- [ ] **Rate Limiting**: Configure in nginx.conf or cloud provider
- [ ] **Authentication**: Add auth for /metrics endpoint
- [ ] **CORS**: Configure if needed for web frontend
- [ ] **Firewall**: Restrict ingress to necessary ports
- [ ] **Logging**: Enable audit logs and monitoring
- [ ] **Updates**: Keep dependencies updated (dependabot)
- [ ] **Backups**: Backup SQLite memory database regularly
- [ ] **DDoS Protection**: Use cloud provider WAF/DDoS protection

## 📈 Monitoring & Observability

### Built-in Metrics
Access `/metrics` endpoint for:
- Request latency percentiles
- Token usage per mode
- Error rates and types
- Intent distribution
- Memory operations

### Cloud Monitoring

**Google Cloud**
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=smart-buddy" --limit 50

# Monitor metrics
gcloud monitoring dashboards create --config-from-file=dashboard.json
```

**Azure**
```bash
# View logs
az monitor log-analytics query \
  --workspace YOUR_WORKSPACE_ID \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerName_s == 'smart-buddy'"

# Set up alerts
az monitor metrics alert create --name high-latency ...
```

### Third-Party Tools
- **Sentry**: Error tracking
- **Datadog**: APM and monitoring
- **New Relic**: Full-stack observability
- **Prometheus + Grafana**: Self-hosted metrics

## ⚡ Performance Tuning

### Worker Configuration
- **Light load (<100 req/min)**: 2-4 workers
- **Medium load (100-1000 req/min)**: 4-8 workers
- **Heavy load (>1000 req/min)**: 8-16 workers + horizontal scaling

### Container Resources
| Traffic | CPU | Memory | Workers |
|---------|-----|--------|---------|
| Development | 0.5 | 512Mi | 2 |
| Light | 1 | 1Gi | 4 |
| Medium | 2 | 2Gi | 8 |
| Heavy | 4 | 4Gi | 16 |

### Scaling Strategy
1. **Vertical**: Increase CPU/memory per container
2. **Horizontal**: Increase container count
3. **Auto-scaling**: Based on CPU (>70%) or requests (>50/container)

## 🐛 Troubleshooting

### Server won't start
```bash
# Check Python version
python --version  # Need 3.11+

# Verify dependencies
pip install -r requirements.txt

# Test imports
python -c "from smart_buddy.memory import MemoryBank; print('OK')"

# Check port
netstat -an | findstr 8000  # Windows
lsof -i :8000  # Linux/Mac
```

### API errors
```bash
# Check logs
docker logs smart-buddy  # Docker
gcloud run logs read --service smart-buddy  # Cloud Run
az containerapp logs show --name smart-buddy --resource-group smart-buddy-rg  # Azure

# Test Gemini API
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('OK')"

# View metrics
curl http://localhost:8000/metrics
```

### High latency
1. Check `/metrics` for bottlenecks
2. Increase workers/threads
3. Scale container resources
4. Enable response caching
5. Optimize database queries

### Memory leaks
1. Monitor `/metrics` over time
2. Set `--max-requests 1000` for Gunicorn
3. Enable periodic worker restarts
4. Profile with memory_profiler

## 📝 Deployment Files

| File | Purpose |
|------|---------|
| `server_flask.py` | Flask application with metrics |
| `wsgi.py` | WSGI entry point |
| `Dockerfile.production` | Optimized Docker build |
| `docker-compose.yml` | Multi-container setup |
| `nginx.conf` | Reverse proxy config |
| `cloud-run.yaml` | GCP deployment config |
| `azure-containerapp.yaml` | Azure deployment config |
| `requirements.txt` | Python dependencies |

## 🎯 Production Readiness Score

Smart Buddy includes:
- ✅ Production WSGI server (Gunicorn/Waitress)
- ✅ Docker containerization
- ✅ Cloud deployment configs (GCP, Azure, AWS)
- ✅ Health checks & metrics dashboard
- ✅ Structured logging
- ✅ Error handling & recovery
- ✅ Horizontal scaling support
- ✅ Security headers (nginx)
- ✅ Rate limiting (nginx)
- ✅ Multi-stage Docker builds
- ✅ Environment-based configuration
- ✅ API documentation

## 🆘 Support

For deployment issues:
1. Check this guide's troubleshooting section
2. Review `/metrics` endpoint for diagnostic info
3. Check cloud provider logs
4. Verify environment variables
5. Test with minimal configuration first

## 📚 Additional Resources

- [Flask Deployment Options](https://flask.palletsprojects.com/en/latest/deploying/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/settings.html)
- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [Azure Container Apps Docs](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

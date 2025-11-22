# 🚀 Smart Buddy Deployment Guide

Complete guide for deploying Smart Buddy locally and to production environments.

---

## 📋 Table of Contents

- [Localhost Deployment (Development)](#localhost-deployment-development)
- [Prerequisites](#prerequisites)
- [Quick Deploy (Google Cloud Run)](#quick-deploy-google-cloud-run)
- [Docker Deployment](#docker-deployment)
- [Azure Container Apps](#azure-container-apps)
- [AWS Elastic Container Service](#aws-elastic-container-service)
- [Environment Variables](#environment-variables)
- [Health Checks & Monitoring](#health-checks--monitoring)
- [Troubleshooting](#troubleshooting)

---

## 🏠 Localhost Deployment (Development)

### Quick Start (2 minutes)

Run Smart Buddy on your local machine for development and testing:

```powershell
# Windows - Automated startup
.\scripts\run_localhost.ps1

# Or manual start
python server_flask.py
```

**Access your deployment:**
- **Health Check:** http://127.0.0.1:8000/health
- **Metrics Dashboard:** http://127.0.0.1:8000/metrics
- **Audit Console:** http://127.0.0.1:8000/audit
- **Chat API:** POST http://127.0.0.1:8000/chat

### Detailed Localhost Setup

#### 1. Install Dependencies

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac

# Install packages
pip install -e .
```

#### 2. Set API Key

```powershell
# Windows PowerShell
$env:GOOGLE_API_KEY = "your-gemini-api-key"

# Linux/Mac
export GOOGLE_API_KEY="your-gemini-api-key"
```

Get your free API key: https://aistudio.google.com/app/apikey

#### 3. Start Server

```powershell
# Development mode (auto-reload)
python server_flask.py

# Production mode with Waitress (Windows)
pip install waitress
waitress-serve --port=8000 wsgi:app

# Production mode with Gunicorn (Linux/Mac)
pip install gunicorn
gunicorn wsgi:app --workers 4 --bind 0.0.0.0:8000
```

#### 4. Test Your Deployment

```powershell
# Test health endpoint
Invoke-RestMethod http://127.0.0.1:8000/health

# Test chat endpoint
$body = @{
    user_id = "test-user"
    session_id = "test-session"
    message = "Hello!"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:8000/chat `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

#### 5. Explore Dashboards

Open in your browser:
- **📊 Metrics:** http://127.0.0.1:8000/metrics
  - Real-time latency stats (p50, p95, p99)
  - Token usage by mode
  - Error rates and request counts
  
- **🛡️ Audit Console:** http://127.0.0.1:8000/audit
  - Complete audit trail
  - Safety moderation logs
  - Tool invocation history

### Localhost Troubleshooting

**Port already in use:**
```powershell
# Find and stop process on port 8000
netstat -ano | findstr :8000
Stop-Process -Id <PID> -Force
```

**Missing dependencies:**
```powershell
pip install -e . --force-reinstall
```

**API key not working:**
```powershell
# Verify it's set
echo $env:GOOGLE_API_KEY

# Test directly
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('OK')"
```

---

## Prerequisites

### Required
- Python 3.10+
- Google Gemini API key ([Get free key](https://aistudio.google.com))
- Docker (for container deployments)

### Cloud Provider CLIs (choose one)
- **Google Cloud**: [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- **Azure**: [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- **AWS**: [AWS CLI](https://aws.amazon.com/cli/)

---

## Quick Deploy (Google Cloud Run)

### Automated Deployment Scripts

**Using PowerShell (Windows):**
```powershell
# Set your project ID and API key
$env:GCP_PROJECT_ID = "your-project-id"
$env:GOOGLE_API_KEY = "your-gemini-api-key"

# Run deployment script
.\scripts\deploy_cloud_run.ps1
```

**Using Bash (Linux/Mac):**
```bash
# Set your project ID and API key
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_API_KEY="your-gemini-api-key"

# Run deployment script
bash scripts/deploy_cloud_run.sh
```

### Expected Output
```
✅ Deployment complete!

📊 Service URL: https://smart-buddy-xyz.run.app
📖 Metrics: https://smart-buddy-xyz.run.app/metrics
🔍 Health: https://smart-buddy-xyz.run.app/health
🛡️  Audit Console: https://smart-buddy-xyz.run.app/audit
```

### Testing Your Deployment
```bash
# Health check
curl https://smart-buddy-xyz.run.app/health

# Test chat endpoint
curl -X POST https://smart-buddy-xyz.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo",
    "session_id": "test_001",
    "message": "Hello Smart Buddy!"
  }'

# View metrics dashboard
open https://smart-buddy-xyz.run.app/metrics
```

## 🐳 Docker Deployment

### Building the Docker Image

The project includes a `Dockerfile` for containerization:

```bash
# Build the Docker image
docker build -t smart-buddy:latest .

# Run locally to test
docker run -p 8000:8000 --env-file .env smart-buddy:latest
```

### Docker Compose (Recommended)

For easier local testing with Docker:

```yaml
# docker-compose.yml
version: '3.8'

services:
  smart-buddy:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./smart_buddy_memory.db:/app/smart_buddy_memory.db
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

---

## ☁️ Google Cloud Run Deployment

### Prerequisites
- Google Cloud SDK installed
- Google Cloud project created
- Billing enabled on your project

### Deployment Steps

1. **Install Google Cloud CLI**
   ```bash
   # Download from https://cloud.google.com/sdk/docs/install
   gcloud init
   ```

2. **Set Project**
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Build and Push to Container Registry**
   ```bash
   # Enable required APIs
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   
   # Build and push
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/smart-buddy
   ```

4. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy smart-buddy \
     --image gcr.io/YOUR_PROJECT_ID/smart-buddy \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars GOOGLE_API_KEY=your_api_key_here \
     --memory 512Mi \
     --cpu 1
   ```

5. **Access Your Deployed Service**
   ```bash
   # Get the service URL
   gcloud run services describe smart-buddy --region us-central1 --format 'value(status.url)'
   ```

### Environment Variables in Cloud Run

**Important**: Never hardcode API keys in your Dockerfile or code!

Use Cloud Run's environment variables:
```bash
gcloud run services update smart-buddy \
  --set-env-vars GOOGLE_API_KEY=your_key_here \
  --region us-central1
```

Or use Google Secret Manager (recommended):
```bash
# Create secret
echo "your_api_key" | gcloud secrets create google-api-key --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# Deploy with secret
gcloud run deploy smart-buddy \
  --set-secrets=GOOGLE_API_KEY=google-api-key:latest
```

---

## 🔵 Azure Container Apps Deployment

### Prerequisites
- Azure CLI installed
- Azure subscription

### Deployment Steps

1. **Install Azure CLI**
   ```bash
   # Download from https://aka.ms/InstallAzureCli
   az login
   ```

2. **Create Resource Group**
   ```bash
   az group create \
     --name smart-buddy-rg \
     --location eastus
   ```

3. **Create Container Registry**
   ```bash
   az acr create \
     --resource-group smart-buddy-rg \
     --name smartbuddyregistry \
     --sku Basic
   
   # Login to ACR
   az acr login --name smartbuddyregistry
   ```

4. **Build and Push Image**
   ```bash
   # Tag image
   docker tag smart-buddy:latest smartbuddyregistry.azurecr.io/smart-buddy:latest
   
   # Push to ACR
   docker push smartbuddyregistry.azurecr.io/smart-buddy:latest
   ```

5. **Create Container App**
   ```bash
   # Install extension
   az extension add --name containerapp
   
   # Create environment
   az containerapp env create \
     --name smart-buddy-env \
     --resource-group smart-buddy-rg \
     --location eastus
   
   # Deploy container app
   az containerapp create \
     --name smart-buddy \
     --resource-group smart-buddy-rg \
     --environment smart-buddy-env \
     --image smartbuddyregistry.azurecr.io/smart-buddy:latest \
     --target-port 8000 \
     --ingress external \
     --env-vars GOOGLE_API_KEY=your_key_here \
     --cpu 0.5 \
     --memory 1.0Gi
   ```

6. **Access Your Service**
   ```bash
   az containerapp show \
     --name smart-buddy \
     --resource-group smart-buddy-rg \
     --query properties.configuration.ingress.fqdn
   ```

---

## 🔐 Security Best Practices

### Protecting API Keys

1. **Use Environment Variables**
   ```python
   # ✅ GOOD - Load from environment
   api_key = os.getenv("GOOGLE_API_KEY")
   
   # ❌ BAD - Hardcoded key
   api_key = "AIzaSy..."
   ```

2. **Use Secret Management Services**
   - **Google Cloud**: Secret Manager
   - **Azure**: Key Vault
   - **AWS**: Secrets Manager

3. **Never Commit Keys**
   ```bash
   # .gitignore should include:
   .env
   *.env
   secrets/
   config/secrets.json
   ```

### Docker Security

1. **Use Non-Root User**
   ```dockerfile
   # In Dockerfile
   RUN adduser -D appuser
   USER appuser
   ```

2. **Scan Images**
   ```bash
   # Scan for vulnerabilities
   docker scan smart-buddy:latest
   ```

---

## 📊 Monitoring & Logging

### Cloud Run Logging

View logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=smart-buddy" --limit 50
```

### Azure Container Apps Logging

View logs:
```bash
az containerapp logs show \
  --name smart-buddy \
  --resource-group smart-buddy-rg \
  --follow
```

### Application Insights (Azure)

Add to your code:
```python
from applicationinsights import TelemetryClient
tc = TelemetryClient(os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY"))
tc.track_event("user_interaction", {"mode": mode})
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Smart Buddy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Google Cloud
        uses: google-github-actions/setup-gcloud@v0
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ secrets.GCP_PROJECT_ID }}
      
      - name: Build and Push
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/smart-buddy
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy smart-buddy \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/smart-buddy \
            --platform managed \
            --region us-central1 \
            --set-env-vars GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }}
```

---

## 💰 Cost Considerations

### Google Cloud Run
- **Free Tier**: 2 million requests/month, 360,000 GB-seconds
- **Pricing**: Pay-per-use, scales to zero
- **Estimated Cost**: $0-5/month for personal use

### Azure Container Apps
- **Free Tier**: Limited compute hours
- **Pricing**: Pay-per-use
- **Estimated Cost**: $0-10/month for personal use

### Optimization Tips
1. Set appropriate memory limits
2. Use autoscaling policies
3. Enable scale-to-zero for non-production
4. Monitor usage regularly

---

## 🧪 Testing Deployment

### Health Check Endpoint

Add to your application:
```python
@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": time.time()}
```

### Load Testing

```bash
# Using Apache Bench
ab -n 100 -c 10 https://your-service-url/

# Using wrk
wrk -t12 -c400 -d30s https://your-service-url/
```

---

## 📝 Deployment Checklist

Before deploying to production:

- [ ] API keys moved to environment variables/secrets
- [ ] `.env` file added to `.gitignore`
- [ ] Docker image tested locally
- [ ] Health check endpoint added
- [ ] Logging configured
- [ ] Resource limits set appropriately
- [ ] Auto-scaling policies configured
- [ ] Monitoring/alerting set up
- [ ] Backup strategy for SQLite database
- [ ] CORS configured if using web frontend
- [ ] Rate limiting implemented
- [ ] Documentation updated

---

## 🆘 Troubleshooting

### Common Issues

**Issue**: "Failed to bind to port"
```bash
# Solution: Check if port is already in use
docker run -p 8080:8000 smart-buddy:latest
```

**Issue**: "Authentication failed"
```bash
# Solution: Check API key is correctly set
gcloud run services describe smart-buddy --format='value(spec.template.spec.containers[0].env)'
```

**Issue**: "Out of memory"
```bash
# Solution: Increase memory allocation
gcloud run services update smart-buddy --memory 1Gi
```

---

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Azure Container Apps Documentation](https://docs.microsoft.com/azure/container-apps)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Gemini API Documentation](https://ai.google.dev/docs)

---

**Note**: This is an educational project. For production deployment, implement additional security measures, error handling, and monitoring as needed.

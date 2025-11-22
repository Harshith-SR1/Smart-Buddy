#!/bin/bash
# Deploy Smart Buddy to Google Cloud Run
# Prerequisites: gcloud CLI installed and authenticated

set -e

PROJECT_ID="${GCP_PROJECT_ID:-smart-buddy-prod}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="smart-buddy"

echo "🚀 Deploying Smart Buddy to Google Cloud Run"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Install from https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check authentication
echo "🔐 Checking authentication..."
gcloud auth list

# Set project
echo "📦 Setting project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create secret for API key (if not exists)
echo "🔑 Setting up API key secret..."
if ! gcloud secrets describe google-api-key &> /dev/null; then
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "⚠️  GOOGLE_API_KEY not set. Skipping secret creation."
        echo "   Create manually: echo -n 'YOUR_API_KEY' | gcloud secrets create google-api-key --data-file=-"
    else
        echo -n "$GOOGLE_API_KEY" | gcloud secrets create google-api-key --data-file=-
        echo "✅ Secret created"
    fi
else
    echo "✅ Secret already exists"
fi

# Build and deploy using Cloud Build
echo "🏗️  Building and deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --min-instances 1 \
    --max-instances 10 \
    --port 8000 \
    --set-env-vars "ENVIRONMENT=production,LOG_LEVEL=INFO" \
    --update-secrets "GOOGLE_API_KEY=google-api-key:latest" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Service URL: $SERVICE_URL"
echo "📖 Metrics: $SERVICE_URL/metrics"
echo "🔍 Health: $SERVICE_URL/health"
echo "🛡️  Audit Console: $SERVICE_URL/audit"
echo ""
echo "🧪 Test with:"
echo "curl $SERVICE_URL/health"
echo ""

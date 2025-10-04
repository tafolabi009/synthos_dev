#!/bin/bash

# GCP Setup script for Synthos Go Backend

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}

if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo "❌ Please provide your GCP Project ID as the first argument"
    echo "Usage: ./setup-gcp.sh YOUR_PROJECT_ID [REGION]"
    exit 1
fi

echo "🚀 Setting up GCP resources for Synthos Go Backend"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create Cloud SQL instance
echo "🗄️ Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create synthos-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --retained-backups-count=7 \
    --retained-transaction-log-days=7 \
    --deletion-protection

# Create database
echo "📊 Creating database..."
gcloud sql databases create synthos --instance=synthos-db

# Create user
echo "👤 Creating database user..."
DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create synthos_user \
    --instance=synthos-db \
    --password=$DB_PASSWORD

# Create GCS bucket
echo "🪣 Creating Cloud Storage bucket..."
BUCKET_NAME="synthos-storage-$PROJECT_ID"
gsutil mb gs://$BUCKET_NAME
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME

# Create secrets
echo "🔐 Creating secrets..."
echo -n "$DB_PASSWORD" | gcloud secrets create db-password --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create jwt-secret --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets create encryption-key --data-file=-

# Grant IAM permissions
echo "🔑 Setting up IAM permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_ID-compute@developer.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_ID-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_ID-compute@developer.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$PROJECT_ID-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Create environment file
echo "📝 Creating environment configuration..."
cat > .env.production << EOF
# Server Configuration
PORT=8080
ENVIRONMENT=production

# Database Configuration
DB_HOST=/cloudsql/$PROJECT_ID:$REGION:synthos-db
DB_PORT=5432
DB_NAME=synthos
DB_USER=synthos_user
DB_PASSWORD=$DB_PASSWORD
DB_SSL_MODE=require

# GCP Configuration
GCP_PROJECT_ID=$PROJECT_ID
GCP_LOCATION=$REGION
GCS_BUCKET_NAME=$BUCKET_NAME

# Vertex AI Configuration
VERTEX_PROJECT_ID=$PROJECT_ID
VERTEX_LOCATION=$REGION
VERTEX_DEFAULT_MODEL=claude-4-opus

# Security Configuration (use secrets in production)
JWT_SECRET=your-jwt-secret-32-chars
ENCRYPTION_KEY=your-encryption-key-32-chars

# Redis Configuration (if using Cloud Memorystore)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Payment Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
PADDLE_VENDOR_ID=your_paddle_vendor_id
PADDLE_VENDOR_AUTH_CODE=your_paddle_auth_code

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Security Configuration
CORS_ORIGINS=https://your-frontend-domain.com
EOF

echo "✅ GCP setup completed successfully!"
echo ""
echo "📋 Summary:"
echo "  - Cloud SQL instance: synthos-db"
echo "  - Database: synthos"
echo "  - User: synthos_user"
echo "  - Password: $DB_PASSWORD"
echo "  - Storage bucket: $BUCKET_NAME"
echo "  - Environment file: .env.production"
echo ""
echo "🚀 Next steps:"
echo "  1. Update .env.production with your actual API keys"
echo "  2. Run: ./deploy.sh"
echo "  3. Test your deployment"
echo ""
echo "⚠️  Important: Keep your database password secure!"
echo "   Password: $DB_PASSWORD"

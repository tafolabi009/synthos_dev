# Cloud Run Deployment Guide

## Prerequisites ✅

Based on your setup, you already have:
- ✅ GCP Project: `genovo-technologies001`
- ✅ Cloud SQL Instance: `genovo-technologies001:europe-north2:synthos`
- ✅ GCS Bucket: `synthos`
- ✅ Redis/Valkey instance
- ✅ VPC Connector: `connector-eu-n2`
- ✅ Secret Manager secret: `Synthos_backend`
- ✅ gcloud CLI installed and configured

## Quick Deploy

### Option 1: Using PowerShell Script (Recommended for Windows)
```powershell
cd d:\Downloads\synthos_dev\backend-go
.\deploy.ps1
```

### Option 2: Using Bash Script
```bash
cd /d/Downloads/synthos_dev/backend-go
chmod +x deploy.sh
./deploy.sh
```

### Option 3: Manual gcloud Command
```powershell
# Set your project
gcloud config set project genovo-technologies001

# Build and push image
docker build -t gcr.io/genovo-technologies001/synthos-backend-go:latest .
docker push gcr.io/genovo-technologies001/synthos-backend-go:latest

# Deploy to Cloud Run
gcloud run deploy synthos-backend-go `
  --image=gcr.io/genovo-technologies001/synthos-backend-go:latest `
  --region=europe-north2 `
  --platform=managed `
  --allow-unauthenticated `
  --port=8080 `
  --memory=2Gi `
  --cpu=2 `
  --min-instances=0 `
  --max-instances=10 `
  --timeout=300 `
  --set-secrets="Synthos_backend=/etc/secrets/Synthos_backend:latest" `
  --vpc-connector=connector-eu-n2 `
  --vpc-egress=all-traffic
```

## Environment Configuration

Your service will automatically load environment variables from Secret Manager secret: `Synthos_backend`

### Verify Secret Manager Secret

Check if the secret has all required variables:
```powershell
gcloud secrets versions access latest --secret=Synthos_backend
```

Should contain (based on your env.example):
```env
ENVIRONMENT=production
JWT_SECRET_KEY=your-jwt-secret
USE_CLOUD_SQL_CONNECTOR=true
CLOUDSQL_INSTANCE=genovo-technologies001:europe-north2:synthos
DB_USER=synthos
DB_PASSWORD=Genovo-2025
DB_NAME=synthos
REDIS_URL=your-redis-url
STORAGE_PROVIDER=gcs
GCP_PROJECT_ID=genovo-technologies001
GCS_BUCKET=synthos
VERTEX_PROJECT_ID=genovo-technologies001
VERTEX_LOCATION=us-central1
VERTEX_DEFAULT_MODEL=claude-opus-4
VERTEX_API_KEY=your-api-key
# ... other variables from env.example
```

### Update Secret (if needed)
```powershell
# Create a temporary file with your env vars
$envContent = Get-Content env.example
$envContent | Set-Content temp-secret.txt

# Update the secret
gcloud secrets versions add Synthos_backend --data-file=temp-secret.txt

# Clean up
Remove-Item temp-secret.txt
```

## Service Account Permissions

Ensure your service account has these roles:
```powershell
# If service account doesn't exist, create it
gcloud iam service-accounts create synthos-backend --display-name="Synthos Backend Service Account"

# Grant necessary permissions
$SA_EMAIL = "synthos-backend@genovo-technologies001.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding genovo-technologies001 `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding genovo-technologies001 `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding genovo-technologies001 `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding genovo-technologies001 `
  --member="serviceAccount:$SA_EMAIL" `
  --role="roles/secretmanager.secretAccessor"
```

## Deployment with Cloud Build (Alternative)

If you prefer using Cloud Build:
```powershell
cd d:\Downloads\synthos_dev\backend-go
gcloud builds submit --config=cloudbuild.yaml ..
```

## Post-Deployment Verification

### 1. Check Service Status
```powershell
gcloud run services describe synthos-backend-go --region=europe-north2
```

### 2. Get Service URL
```powershell
$SERVICE_URL = gcloud run services describe synthos-backend-go --region=europe-north2 --format='value(status.url)'
Write-Host "Service URL: $SERVICE_URL"
```

### 3. Test Health Endpoint
```powershell
Invoke-WebRequest -Uri "$SERVICE_URL/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

### 4. Test API Docs
```powershell
Start-Process "$SERVICE_URL/api/v1/docs/ui"
```

### 5. View Logs
```powershell
gcloud run services logs read synthos-backend-go --region=europe-north2 --limit=50
```

## Troubleshooting

### Issue: Build fails with "cannot find package"
**Solution**: Make sure you're in the `backend-go` directory
```powershell
cd d:\Downloads\synthos_dev\backend-go
```

### Issue: Database connection fails
**Solutions**:
1. Check VPC connector is active:
   ```powershell
   gcloud compute networks vpc-access connectors describe connector-eu-n2 --region=europe-north2
   ```

2. Verify Cloud SQL instance is running:
   ```powershell
   gcloud sql instances describe synthos
   ```

3. Check service account has Cloud SQL Client role

### Issue: Secret not found
**Solution**: Verify secret exists and has latest version:
```powershell
gcloud secrets describe Synthos_backend
gcloud secrets versions list Synthos_backend
```

### Issue: Container crashes on startup
**Solution**: Check logs for errors:
```powershell
gcloud run services logs read synthos-backend-go --region=europe-north2 --limit=100
```

Common issues:
- Missing JWT_SECRET_KEY (must be 32+ characters)
- Missing VERTEX_PROJECT_ID or VERTEX_API_KEY
- Database connection string incorrect

## Update Existing Deployment

### Quick Update (same image tag)
```powershell
# Rebuild and push
docker build -t gcr.io/genovo-technologies001/synthos-backend-go:latest .
docker push gcr.io/genovo-technologies001/synthos-backend-go:latest

# Trigger new deployment
gcloud run services update synthos-backend-go --region=europe-north2
```

### Update Environment Variables
```powershell
# Add/update environment variable
gcloud run services update synthos-backend-go `
  --region=europe-north2 `
  --update-env-vars="NEW_VAR=value"

# Update secret
gcloud run services update synthos-backend-go `
  --region=europe-north2 `
  --update-secrets="Synthos_backend=/etc/secrets/Synthos_backend:latest"
```

## Rollback

If something goes wrong, rollback to previous revision:
```powershell
# List revisions
gcloud run revisions list --service=synthos-backend-go --region=europe-north2

# Rollback to specific revision
gcloud run services update-traffic synthos-backend-go `
  --region=europe-north2 `
  --to-revisions=synthos-backend-go-00002-xyz=100
```

## Monitoring

### Cloud Console Links
- Service: https://console.cloud.google.com/run/detail/europe-north2/synthos-backend-go
- Logs: https://console.cloud.google.com/logs
- Metrics: https://console.cloud.google.com/monitoring

### Set Up Alerts (Recommended)
```powershell
# Alert on high error rate
gcloud alpha monitoring policies create `
  --notification-channels=YOUR_CHANNEL_ID `
  --display-name="Synthos Backend High Error Rate" `
  --condition-display-name="Error rate > 5%" `
  --condition-threshold-value=0.05 `
  --condition-threshold-duration=300s
```

## Cost Optimization

Your current configuration:
- Min instances: 0 (scales to zero when idle ✅)
- Max instances: 10
- Memory: 2Gi
- CPU: 2

Expected costs:
- **Idle**: ~$0 (scales to zero)
- **Active**: ~$0.10/hour per instance
- **Storage**: ~$0.026/GB/month (GCS)
- **Cloud SQL**: Based on your instance size

To reduce costs:
```powershell
# Reduce memory/CPU for lower traffic
gcloud run services update synthos-backend-go `
  --region=europe-north2 `
  --memory=1Gi `
  --cpu=1
```

## CI/CD Setup (Optional)

To automate deployments on git push:

1. Connect repository to Cloud Build:
   ```powershell
   gcloud builds triggers create github `
     --repo-name=synthos_dev `
     --repo-owner=your-github-username `
     --branch-pattern="^main$" `
     --build-config=backend-go/cloudbuild.yaml
   ```

2. Push to trigger deployment:
   ```bash
   git push origin main
   ```

## Quick Reference Commands

```powershell
# Deploy
.\deploy.ps1

# View logs
gcloud run services logs read synthos-backend-go --region=europe-north2 --tail

# Get URL
gcloud run services describe synthos-backend-go --region=europe-north2 --format='value(status.url)'

# Shell into running container (for debugging)
gcloud run services proxy synthos-backend-go --region=europe-north2

# Delete service (if needed)
gcloud run services delete synthos-backend-go --region=europe-north2
```

## Need Help?

- Cloud Run docs: https://cloud.google.com/run/docs
- Logs: `gcloud run services logs read synthos-backend-go --region=europe-north2`
- Support: https://cloud.google.com/support

---

**Ready to deploy?** Run: `.\deploy.ps1` 🚀

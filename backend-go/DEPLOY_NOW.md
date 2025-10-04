# 🚀 Deploy Now - Quick Start

## Fastest Way to Deploy

Open PowerShell in the `backend-go` directory and run:

```powershell
cd d:\Downloads\synthos_dev\backend-go
.\deploy.ps1
```

That's it! The script will:
1. ✅ Build the Docker image
2. ✅ Push to Container Registry
3. ✅ Deploy to Cloud Run
4. ✅ Test the health endpoint
5. ✅ Display the service URL

---

## Alternative: One Command Deploy

If you prefer a single gcloud command:

```powershell
gcloud run deploy synthos-backend-go --source . --region=europe-north2 --allow-unauthenticated --set-secrets="Synthos_backend=/etc/secrets/Synthos_backend:latest" --vpc-connector=connector-eu-n2 --vpc-egress=all-traffic --memory=2Gi --cpu=2
```

---

## What Happens Next?

After deployment completes, you'll see:
```
Service URL: https://synthos-backend-go-xxxxx-ew.a.run.app
```

Test it immediately:
```powershell
# Health check
curl https://YOUR-SERVICE-URL/health

# API docs
Start-Process https://YOUR-SERVICE-URL/api/v1/docs/ui
```

---

## Troubleshooting Quick Fixes

### ❌ "Secret not found"
```powershell
# Check secret exists
gcloud secrets describe Synthos_backend

# If missing, create from env.example
Get-Content env.example | gcloud secrets create Synthos_backend --data-file=-
```

### ❌ "Permission denied"
```powershell
# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com sqladmin.googleapis.com
```

### ❌ "Cannot connect to database"
```powershell
# Verify VPC connector
gcloud compute networks vpc-access connectors describe connector-eu-n2 --region=europe-north2

# Check Cloud SQL is running
gcloud sql instances describe synthos
```

---

## View Logs in Real-Time

```powershell
gcloud run services logs tail synthos-backend-go --region=europe-north2
```

---

**Ready?** Just run: `.\deploy.ps1` 🎉

# Locked PDF Decrypt Service (Render)

FastAPI microservice for decrypting and merging encrypted PDF files. Deployed on **Render's free tier** (no billing required).

## Features

- ✅ Free tier support (512 MB RAM, 0.1 CPU)
- ✅ Auto-deploys from Git
- ✅ FastAPI + uvicorn
- ✅ pypdf encryption support
- ✅ Optional bearer token authentication
- ✅ HTTP GET health check & POST merge endpoint

## API Endpoints

### GET /healthz
Health check endpoint.

**Response:**
```json
{
  "ok": true
}
```

### POST /merge-locked
Fetch, decrypt, and merge encrypted PDFs.

**Request:**
```json
{
  "urls": ["https://example.com/locked1.pdf", "https://example.com/locked2.pdf"],
  "passwords": {
    "locked1.pdf": "password123",
    "locked2.pdf": "password456"
  }
}
```

**Success Response:**
```json
{
  "ok": true,
  "pagesAdded": 15,
  "pdfBase64": "JVBERi...",
  "failures": []
}
```

**Error Response:**
```json
{
  "ok": false,
  "error": "No pages could be decrypted and merged",
  "failures": [
    "https://example.com/locked1.pdf: invalid password"
  ]
}
```

## Authentication

If `DECRYPT_SERVICE_TOKEN` is set in environment, requests require:

```
Authorization: Bearer YOUR_TOKEN_HERE
```

## Deployment on Render (Free Tier)

### Prerequisites
- Render account (free at https://render.com)
- Git repository (GitHub, GitLab, or Bitbucket)
- This service pushed to your repository

### Step 1: Push to Git
```bash
git add cloud-run/locked-pdf-decrypt/
git commit -m "Add locked PDF decrypt service"
git push origin main
```

### Step 2: Create Render Account & Service
1. Go to https://render.com/register
2. Sign up with email or GitHub
3. Create a new **Web Service** from your repository
4. Use these settings:
   - **Repository:** Select your repo
   - **Root Directory:** `cloud-run/locked-pdf-decrypt`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (included with hobby workspace)

### Step 3: Set Environment Variables
In the Render dashboard (Web Service → Environment):
```
DECRYPT_SERVICE_TOKEN=YOUR_SECRET_TOKEN_HERE
```

**Generate a strong token:**
```bash
# On macOS/Linux:
openssl rand -hex 32

# On Windows (PowerShell):
[System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes(32) | ForEach-Object { $_.ToString("x2") } -join ""
```

### Step 4: Deploy
- Click **Deploy** in the Render dashboard
- Wait for build completion (~2 min)
- Service URL will appear: `https://locked-pdf-decrypt-xxxx.onrender.com`

### Verify Deployment

```bash
curl https://locked-pdf-decrypt-xxxx.onrender.com/healthz
# Should return: {"ok":true}
```

## Integration with Next.js

In your Vercel deployment, set:

```
LOCKED_PDF_DECRYPT_URL=https://locked-pdf-decrypt-xxxx.onrender.com
LOCKED_PDF_DECRYPT_TOKEN=YOUR_SECRET_TOKEN_HERE
```

Then redeploy your Vercel app.

## Render Free Tier Limits

| Resource | Limit |
|----------|-------|
| Memory | 512 MB |
| CPU | 0.1 vCPU |
| Outbound bandwidth | ~60 GB/month (ample for decryption) |
| Build minutes | 500/month |
| Auto-scale | No spinning down |

**Note:** Free instances are kept alive and never spin down, making them ideal for low-traffic APIs.

## Troubleshooting

### Build fails with "pip not found"
- Ensure `requirements.txt` is in `cloud-run/locked-pdf-decrypt/`
- Render will auto-detect Python and install deps

### "No pages could be decrypted"
- Check password correctness in request
- Verify PDF is actually encrypted (not protected)

### 401/403 Authentication Error
- Ensure `Authorization: Bearer TOKEN` header is included
- Verify token matches `DECRYPT_SERVICE_TOKEN` env var

### Service not responding
- Check logs in Render dashboard (Web Service → Logs)
- Redeploy if idle for extended period

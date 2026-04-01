# Render Deployment Guide for Locked PDF Decrypt Service

Complete step-by-step guide to deploy the locked PDF decrypt microservice on **Render's free tier** (no billing account required).

## Why Render Over Cloud Run?

| Feature | Render (Free) | Cloud Run (Free) |
|---------|---|---|
| Billing Account Required | **No** ✅ | **Yes** ❌ |
| Startup Time | ~30s (always-on) | <1s (faster) |
| Architecture | Traditional VPS | Serverless |
| Cost | $0/month | $0/month (if within free tier) |
| Python Support | Native runtime | Docker required |
| Git Auto-Deploy | ✅ Yes | Manual/GCP Build |

**Render wins for your case:** No billing required for hobby plan, native Python support, easier Git integration.

---

## Prerequisites

1. **Git Repository** (with code pushed to GitHub/GitLab/Bitbucket)
   - Service code in: `cloud-run/locked-pdf-decrypt/`
   - Files: `main.py`, `requirements.txt`, `render.yaml`

2. **Internet Connection** (to sign up and deploy)

3. **Command Line** (optional, for generating auth token)

---

## Part 1: Prepare Your Service Locally

### 1.1 Verify Service Files

Ensure these files exist in `cloud-run/locked-pdf-decrypt/`:

```
cloud-run/locked-pdf-decrypt/
├── main.py               # FastAPI app
├── requirements.txt      # Dependencies (fastapi, uvicorn, pypdf)
├── render.yaml          # Render deployment config
├── README.md            # Documentation
└── Dockerfile           # (optional, not used by Render)
```

### 1.2 Generate a Strong Token

You'll need a randomized token for `DECRYPT_SERVICE_TOKEN`. Choose one:

**On macOS/Linux:**
```bash
openssl rand -hex 32
# Output: a3f5b8c2e9d1f4a7b6e2c5d8f1a4b7e9c2d5f8a1b4e7c2d9f6a3b8e1c4f7
```

**On Windows (PowerShell):**
```powershell
-join ([System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes(32) | ForEach-Object { $_.ToString("x2") })
# Output: 2f1e8d9c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1
```

**Save this token somewhere safe** — you'll need it for both Render and Vercel env vars.

---

## Part 2: Push to Git

### 2.1 Commit and Push

```bash
cd path/to/your/repo
git add cloud-run/locked-pdf-decrypt/
git commit -m "Add locked PDF decrypt service for Render"
git push origin main
```

> Make sure your code is accessible on GitHub/GitLab/Bitbucket.

---

## Part 3: Create Render Account

### 3.1 Sign Up (Free)

1. Go to: https://render.com/register
2. Click **Sign up with GitHub** (or email)
3. Follow OAuth flow to authorize Render
4. You'll be placed in a **Hobby workspace** (free, no billing needed)

### 3.2 Verify Your Git Connection

In the Render dashboard:
- Dashboard → Integrations
- Render should have **GitHub/GitLab/Bitbucket access**
- If needed, click "Authorize" to grant access

---

## Part 4: Create and Deploy Web Service

### 4.1 New Web Service

1. Go to **Render Dashboard** → https://dashboard.render.com
2. Click **+ New** → **Web Service**
3. Select your repository (containing `cloud-run/locked-pdf-decrypt/`)
4. Click **Connect**

### 4.2 Configure Service

Fill in the settings:

| Field | Value |
|-------|-------|
| **Name** | `locked-pdf-decrypt` |
| **Runtime** | `Python 3` |
| **Root Directory** | `cloud-run/locked-pdf-decrypt` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` |

### 4.3 Add Environment Variables

In the config under **Environment**:

Click **Add Environment Variable**:

| Name | Value |
|------|-------|
| `DECRYPT_SERVICE_TOKEN` | (paste your generated token from Part 1.2) |

### 4.4 Deploy

1. Click **Create Web Service**
2. Render displays: **Deploying...** (wait 1-2 minutes)
3. Once live, you'll see:
   - ✅ Green status light
   - URL: `https://locked-pdf-decrypt-xxxx.onrender.com`
   - Deploy logs (scroll to verify "Uvicorn running on...")

---

## Part 5: Verify Deployment

### 5.1 Health Check

```bash
curl https://locked-pdf-decrypt-xxxx.onrender.com/healthz
# Expected: {"ok":true}
```

### 5.2 Test Auth (Optional)

```bash
# Without token (should fail):
curl -X POST https://locked-pdf-decrypt-xxxx.onrender.com/merge-locked \
  -H "Content-Type: application/json" \
  -d '{"urls":[]}'
# Expected: 401 Unauthorized

# With token (should work):
curl -X POST https://locked-pdf-decrypt-xxxx.onrender.com/merge-locked \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"urls":[]}'
# Expected: 400 Bad Request (urls are required) — auth passed!
```

---

## Part 6: Update Next.js Environment

### 6.1 Get Your Render Service URL

From Render dashboard, copy the URL:
```
https://locked-pdf-decrypt-xxxx.onrender.com
```

### 6.2 Update Vercel Environment Variables

In **Vercel Dashboard** → Your Project → Settings → Environment Variables:

Add or update:

| Name | Value |
|------|-------|
| `LOCKED_PDF_DECRYPT_URL` | `https://locked-pdf-decrypt-xxxx.onrender.com` |
| `LOCKED_PDF_DECRYPT_TOKEN` | (paste your token) |

### 6.3 Redeploy Vercel

```bash
# In your Next.js project root:
vercel deploy --prod
```

Or via Vercel dashboard:
- Dashboard → Your Project → Deployments → **Redeploy** latest commit

---

## Part 7: Test End-to-End

### 7.1 Test Locked PDF Download

In your Next.js app:
1. Navigate to locked PDF (e.g., `type=pdfl`)
2. Should download without blank pages
3. Check logs:
   - **Render:** Dashboard → Web Service → Logs
   - **Vercel:** Dashboard → Deployments → Logs

### 7.2 Verify Success

- ✅ PDF downloads successfully
- ✅ No "422 Unprocessable Entity" error
- ✅ PDF has all pages merged from source

---

## Troubleshooting

### Build Fails: "pip: command not found"

**Solution:** Ensure `requirements.txt` exists and has:
```
fastapi==0.116.1
uvicorn[standard]==0.35.0
pypdf==5.9.0
```

### Service Returns 500 Error

**Check Render Logs:**
1. Dashboard → Web Service → Logs
2. Look for Python errors (import, syntax, etc.)
3. Redeploy if logs look stale

### 401/403 Unauthorized from Next.js

**Verify:**
1. Token in Render env var: `DECRYPT_SERVICE_TOKEN`
2. Token in Vercel env var: `LOCKED_PDF_DECRYPT_TOKEN`
3. Tokens match exactly (case-sensitive)
4. `LOCKED_PDF_DECRYPT_URL` is set in Vercel

### PDF Still Blank After Merge

**Debug:**
1. Check password correctness
2. Verify PDF is actually encrypted (not just protected)
3. Test merge locally:
   ```bash
   python -c "from pypdf import PdfReader; PdfReader('file.pdf', password='pwd')"
   ```

### Free Tier Limitations?

**Render's free tier Web Services:**
- Never spin down (always-on, unlike Cloud Run)
- 512 MB RAM (ample for PDF merging)
- 0.1 CPU (quick for small merges)
- Outbound bandwidth: ~60 GB/month
- Build minutes: 500/month

Your use case is well within limits.

---

## Maintenance & Monitoring

### Auto-Redeploy on Git Push

By default, Render auto-redeploys when you push to `main`. To test:

```bash
git add .
git commit -m "Update decrypt service"
git push origin main
# Render automatically detects and redeploys
```

### Check Service Metrics

In Render dashboard:
- **Metrics** tab: CPU, RAM, request count
- **Logs** tab: Live logs (uvicorn, errors)
- **Events** tab: Deploy history, health checks

### Restart Service

If service becomes unresponsive:
1. Dashboard → Web Service → Settings
2. Click **Restart**

---

## Next Steps

1. ✅ Render deployment complete
2. ✅ Vercel environment updated
3. ✅ Test locked PDF download
4. ❓ Monitor first 24 hours for errors
5. ❓ Consider custom domain (Render → Settings → Custom Domain)

---

## File Reference

**Render Configuration Files:**
- `cloud-run/locked-pdf-decrypt/render.yaml` — Blueprint for one-click deploy
- `cloud-run/locked-pdf-decrypt/requirements.txt` — Python dependencies
- `cloud-run/locked-pdf-decrypt/main.py` — FastAPI source code

**Integration Points:**
- [src/lib/env.ts](src/lib/env.ts#L1) — Next.js env schema
- [src/app/api/pdf/route.ts](src/app/api/pdf/route.ts#L1) — Route that calls Render

---

## Support

- **Render Docs:** https://render.com/docs/deploy-fastapi
- **Render Support:** support@render.com or https://community.render.com
- **FastAPI Docs:** https://fastapi.tiangolo.com

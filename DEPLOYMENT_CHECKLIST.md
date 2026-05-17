# Deployment Checklist — MIP-008 Public Backend

## ✅ Files Created for Deployment

- `render.yaml` — Render blueprint for automated deployment
- `Procfile` — Process file for Render/Heroku-style deployment
- `DEPLOYMENT.md` — Complete deployment guide
- Updated `requirements.txt` — Removed macOS-only dependencies

## 📋 Deployment Steps

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "feat: add MIP-008 backend with Render deployment config"
git remote add origin <your-github-repo>
git push -u origin main
```

### 2. Create Render Account
- Go to [render.com](https://render.com)
- Sign up (GitHub login recommended)
- Verify email

### 3. Deploy PostgreSQL
- Dashboard → New → PostgreSQL
- Name: `membra-db`
- Database: `membra`
- User: `membra_user`
- Region: Choose nearest
- Plan: Free (or paid)
- Copy the **Internal Database URL**

### 4. Deploy Web Service
- Dashboard → New → Web Service
- Connect GitHub repository
- Name: `membra-kernel`
- Runtime: Python 3
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Environment Variables:
  - `DATABASE_URL`: (paste from step 3)
  - `AUTO_CREATE_TABLES`: `true`
  - `MEMBRA_DATA_ENCRYPTION_KEY`: (generate)
  - `ACCESS_SIGNING_SECRET`: (generate)

### 5. Wait for Deployment
- Monitor logs
- Takes 2-5 minutes
- Green checkmark = success

### 6. Get Public URL
- Render provides URL like: `https://membra-kernel.onrender.com`
- This is your public backend

### 7. Configure macOS Extension
- Open Membra Folder Link app
- Enter Render URL in Backend URL field
- Click "Save"
- Extension now uses public backend

## 🧪 Test Deployment

```bash
# Health check
curl https://your-app.onrender.com/public/v1/health

# Create test share
curl -X POST https://your-app.onrender.com/api/share/folder \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/tmp/test",
    "owner_wallet": "test",
    "expiration": "never",
    "base_url": "https://your-app.onrender.com"
  }'
```

## 💰 Cost

**Free tier:**
- PostgreSQL: $0
- Web Service: $0
- **Total: $0/month**

**Paid tier (recommended for production):**
- PostgreSQL: $7/month
- Web Service: $7/month
- **Total: ~$14/month**

## ⚠️ Notes

- Free tier services spin down after inactivity
- First request after spin-down takes 30-60 seconds
- Upgrade to paid for instant response
- Render automatically handles SSL
- Custom domains supported on paid plans

## 📚 Documentation

- Full guide: `DEPLOYMENT.md`
- macOS extension: `MembraFolderLink/README.md`
- Quick start: `MembraFolderLink/QUICKSTART.md`

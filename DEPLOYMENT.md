# Deploy MEMBRA Backend to Render

This guide explains how to deploy the MIP-008 MEMBRA Public Folder Link Gateway backend to Render.

## Prerequisites

- Render account (free tier available)
- GitHub repository with this code
- Render CLI (optional, for command-line deployment)

## Quick Deploy via Dashboard

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "feat: add MIP-008 backend and macOS Finder extension"
   git remote add origin <your-github-repo>
   git push -u origin main
   ```

2. **Create PostgreSQL database on Render**
   - Go to [render.com](https://render.com)
   - Dashboard → New → PostgreSQL
   - Name: `membra-db`
   - Database: `membra`
   - User: `membra_user`
   - Region: Choose nearest
   - Plan: Free (or paid for production)
   - Click "Create Database"
   - Copy the **Internal Database URL** (you'll need this)

3. **Create Web Service**
   - Dashboard → New → Web Service
   - Connect your GitHub repository
   - Name: `membra-kernel`
   - Region: Same as database
   - Branch: `main`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Click "Advanced"
   - Add Environment Variables:
     - `DATABASE_URL`: (paste the Internal Database URL from step 2)
     - `AUTO_CREATE_TABLES`: `true`
     - `MEMBRA_DATA_ENCRYPTION_KEY`: (click "Generate" or use a secure random string)
     - `ACCESS_SIGNING_SECRET`: (click "Generate" or use a secure random string)
   - Click "Create Web Service"

4. **Wait for deployment**
   - Render will build and deploy your service
   - This takes 2-5 minutes
   - Monitor the logs for any errors

5. **Get your public URL**
   - Once deployed, Render will provide a URL like: `https://membra-kernel.onrender.com`
   - This is your public backend URL

## Deploy via render.yaml (Automatic)

If you have the Render CLI installed:

```bash
# Install Render CLI
npm install -g @renderinc/cli

# Login
render login

# Deploy from render.yaml
render blueprint
```

The `render.yaml` file in this repository handles:
- PostgreSQL database creation
- Web service configuration
- Environment variable setup
- Database connection linking

## Configure macOS Extension

After deployment:

1. Open the Membra Folder Link app
2. In the Backend URL field, enter your Render URL:
   - Example: `https://membra-kernel.onrender.com`
3. Click "Save"
4. The Finder extension will now use the public backend

## Test the Deployment

1. **Test health endpoint**
   ```bash
   curl https://your-app.onrender.com/public/v1/health
   ```

2. **Test folder share creation**
   ```bash
   curl -X POST https://your-app.onrender.com/api/share/folder \
     -H "Content-Type: application/json" \
     -d '{
       "folder_path": "/tmp/test",
       "owner_wallet": "test_user",
       "expiration": "never",
       "base_url": "https://your-app.onrender.com"
     }'
   ```

3. **Access the share page**
   - Use the `public_link` from the response
   - Open in browser to verify

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `AUTO_CREATE_TABLES` | Auto-create tables on startup | Yes (set to `true`) |
| `MEMBRA_DATA_ENCRYPTION_KEY` | Encryption key for sensitive data | Yes |
| `ACCESS_SIGNING_SECRET` | Secret for signing access tokens | Yes |
| `PLATFORM_API_KEY` | Platform API key (optional) | No |
| `WEBHOOK_SECRET` | Webhook secret (optional) | No |

## Troubleshooting

**Deployment fails:**
- Check the Render logs for specific error messages
- Ensure all dependencies are in `requirements.txt`
- Verify Python version compatibility

**Database connection errors:**
- Verify `DATABASE_URL` is correct
- Ensure database is in the same region as web service
- Check database is running (not in suspended state)

**Extension can't connect:**
- Verify backend URL in macOS app matches Render URL
- Check if Render service is running (not suspended)
- Test backend URL directly in browser

**Free tier limitations:**
- Free PostgreSQL spins down after inactivity
- Free web services spin down after 15 minutes of inactivity
- First request after spin-down may take 30-60 seconds

## Production Considerations

For production use:

1. **Upgrade to paid plans**
   - Eliminates spin-down delays
   - Better performance
   - Higher resource limits

2. **Add custom domain**
   - Render supports custom domains
   - Configure DNS records
   - Enable SSL (automatic on Render)

3. **Enable monitoring**
   - Render provides built-in metrics
   - Set up alerts for errors
   - Monitor database performance

4. **Backup strategy**
   - Render automatically backs up PostgreSQL
   - Configure backup retention policy

5. **Security**
   - Use strong encryption keys
   - Rotate secrets periodically
   - Enable Render's built-in DDoS protection

## Cost Estimate (Render Free Tier)

- PostgreSQL: $0/month (512 MB)
- Web Service: $0/month (512 MB RAM, 0.1 CPU)
- Total: $0/month

**Paid tier starting at:**
- PostgreSQL: $7/month (1 GB)
- Web Service: $7/month (512 MB RAM, 0.1 CPU)
- Total: ~$14/month

## Alternative: Vercel

Vercel is not recommended for this backend because:
- Vercel is optimized for frontend/serverless functions
- FastAPI requires a long-running process
- PostgreSQL integration is more complex on Vercel
- Render provides better Python/database support

If you must use Vercel, you would need:
- Vercel serverless functions (limited execution time)
- External PostgreSQL (e.g., Neon, Supabase)
- Significant code refactoring

Render is the better choice for this use case.

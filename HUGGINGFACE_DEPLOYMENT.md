# Deploy to Hugging Face Spaces

This guide explains how to deploy the MIP-008 MEMBRA Public Folder Link Gateway to Hugging Face Spaces.

## Prerequisites

- Hugging Face account (free)
- GitHub repository with this code

## Quick Deploy

### 1. Create a New Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Fill in:
   - **Space name**: `membra-folder-link`
   - **License**: MIT
   - **SDK**: Docker
   - **Hardware**: CPU basic (free)
4. Click "Create Space"

### 2. Connect GitHub Repository

1. In your Space, go to "Settings" → "Repository"
2. Click "Connect to GitHub"
3. Select your repository
4. Choose the branch (usually `main`)
5. Click "Connect"

The Space will automatically build and deploy.

### 3. Add PostgreSQL Database

1. In your Space, go to "Settings" → "Variables and Secrets"
2. Add a new PostgreSQL database:
   - Click "New Database"
   - Choose "PostgreSQL"
   - Name it `membra-db`
3. Copy the connection string

### 4. Configure Environment Variables

In "Settings" → "Variables and Secrets", add:

| Variable | Value | Required |
|----------|-------|----------|
| `DATABASE_URL` | (paste PostgreSQL connection string) | Yes |
| `AUTO_CREATE_TABLES` | `true` | Yes |
| `MEMBRA_DATA_ENCRYPTION_KEY` | (generate random string) | Yes |
| `ACCESS_SIGNING_SECRET` | (generate random string) | Yes |

### 5. Wait for Deployment

- The Space will automatically rebuild with new variables
- Monitor the "Logs" tab for progress
- Takes 2-5 minutes

### 6. Get Your Space URL

Once deployed, your Space URL will be:
```
https://your-space-name.hf.space
```

## Test the Deployment

```bash
# Health check
curl https://your-space-name.hf.space/public/v1/health

# Create a test share
curl -X POST https://your-space-name.hf.space/api/share/folder \
  -H "Content-Type: application/json" \
  -d '{
    "folder_path": "/tmp/test",
    "owner_wallet": "test_user",
    "expiration": "never",
    "base_url": "https://your-space-name.hf.space"
  }'
```

## Configure macOS Extension

1. Open the Membra Folder Link app
2. Enter your Hugging Face Space URL
3. Click "Save"
4. The extension will now use the public backend

## Important Notes

### File Storage Limitations

Hugging Face Spaces have **persistent storage**, but:
- Free tier: ~20GB storage
- Files are stored on the Space's filesystem
- For production with large files, consider using external storage (S3, Cloudflare R2)

### Database

- Hugging Face provides managed PostgreSQL
- Connection string format: `postgresql://user:password@host:port/dbname`
- Database is persistent and backed up

### Hardware Options

- **CPU basic (free)**: Good for testing, limited resources
- **CPU upgrade**: $0.10/hour, better performance
- **GPU**: Not needed for this application

### Cold Start

Free Spaces may have cold starts (30-60 seconds) after inactivity. Upgrade to avoid this.

## Troubleshooting

**Build fails:**
- Check the "Logs" tab for errors
- Verify Dockerfile syntax
- Ensure all dependencies are in requirements.txt

**Database connection error:**
- Verify DATABASE_URL is correct
- Check database is running in Space settings
- Ensure database is in the same region

**Extension can't connect:**
- Verify Space URL in macOS app
- Check if Space is running (not sleeping)
- Test Space URL directly in browser

**Storage full:**
- Free tier has ~20GB limit
- Clean up old shares via API
- Consider upgrading to paid tier

## Cost

**Free tier:**
- CPU basic: $0
- PostgreSQL: $0
- Storage: ~20GB
- **Total: $0/month**

**Paid tier:**
- CPU upgrade: ~$72/month
- More storage available
- No cold starts
- Better performance

## Comparison: Hugging Face vs Render

| Feature | Hugging Face Spaces | Render |
|---------|-------------------|--------|
| Free tier | Yes | Yes |
| PostgreSQL | Yes (managed) | Yes (managed) |
| Persistent storage | Yes (~20GB) | No (ephemeral) |
| Cold starts | Yes (free) | Yes (free) |
| Docker support | Yes | Yes |
| Community | ML/AI focused | General purpose |
| File serving | Good | Good |

**Hugging Face is better if:**
- You want persistent storage for files
- You're in the ML/AI community
- You want simple deployment

**Render is better if:**
- You need more control over infrastructure
- You want general-purpose hosting
- You need custom domains (free on both)

## Advanced: External Storage

For production with large files:

1. Use Cloudflare R2 or AWS S3 for file storage
2. Update the backend to upload files to external storage
3. Store external URLs in the manifest
4. Serve files from CDN

This is beyond the scope of this guide but recommended for production use.

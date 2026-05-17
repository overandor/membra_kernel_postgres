#!/bin/bash
# Deploy MEMBRA to Hugging Face Spaces
# Run this script yourself - do not share tokens in chat

set -e

echo "🚀 MEMBRA Hugging Face Spaces Deployment Script"
echo ""
echo "⚠️  IMPORTANT: You must authenticate with Hugging Face yourself."
echo "   Do NOT paste tokens into chat or share them with AI assistants."
echo ""

# Check for huggingface-cli
if ! command -v huggingface-cli &> /dev/null; then
    echo "❌ huggingface-cli not found"
    echo "Install with: pip install huggingface-hub"
    exit 1
fi

# Check login status
echo "🔍 Checking Hugging Face authentication..."
if ! huggingface-cli whoami &> /dev/null; then
    echo "❌ Not logged in to Hugging Face"
    echo ""
    echo "Login with:"
    echo "  huggingface-cli login"
    echo ""
    echo "Or set token via environment variable:"
    echo "  export HF_TOKEN=your_token_here"
    echo ""
    exit 1
fi

echo "✅ Authenticated as: $(huggingface-cli whoami)"
echo ""

# Get space name
read -p "Enter your Hugging Face username: " HF_USERNAME
read -p "Enter space name (e.g., membra-folder-link): " SPACE_NAME

SPACE_ID="${HF_USERNAME}/${SPACE_NAME}"

echo ""
echo "📦 Creating Space: ${SPACE_ID}"
echo ""

# Create space using API
python3 << EOF
import os
import sys

try:
    from huggingface_hub import HfApi
    api = HfApi()
    
    api.create_repo(
        repo_id="${SPACE_ID}",
        repo_type="space",
        space_sdk="docker",
        private=False
    )
    print(f"✅ Space created: https://huggingface.co/spaces/${SPACE_ID}")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"ℹ️  Space already exists: https://huggingface.co/spaces/${SPACE_ID}")
    else:
        print(f"❌ Error creating space: {e}")
        sys.exit(1)
EOF

# Clone the space
echo ""
echo "📂 Cloning space repository..."
if [ -d "hf-space-temp" ]; then
    rm -rf hf-space-temp
fi

git clone "https://huggingface.co/spaces/${SPACE_ID}" hf-space-temp 2>/dev/null || true

# Copy files to space
echo ""
echo "📁 Copying deployment files..."
cp -r /Users/alep/Desktop/membra_kernel_postgres/* hf-space-temp/ 2>/dev/null || true

# Clean up unnecessary files
cd hf-space-temp
rm -rf .git
rm -rf __pycache__
rm -rf MembraFolderLink  # macOS extension - not needed in backend
rm -f *.zip
rm -f deploy_to_hf.sh
rm -f render.yaml
rm -f Procfile
rm -f DEPLOYMENT.md
rm -f DEPLOYMENT_CHECKLIST.md
rm -f HUGGINGFACE_DEPLOYMENT.md

cd ..

# Commit and push
echo ""
echo "📤 Pushing to Hugging Face Spaces..."
cd hf-space-temp
git init
git add .
git commit -m "Deploy MEMBRA MIP-008 backend"
git push --force origin main

cd ..
rm -rf hf-space-temp

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your Space URL: https://huggingface.co/spaces/${SPACE_ID}"
echo ""
echo "⏳ Wait 2-5 minutes for the build to complete."
echo "   Monitor progress at: https://huggingface.co/spaces/${SPACE_ID}"
echo ""
echo "📋 Next steps:"
echo "   1. Go to Space Settings → Variables and Secrets"
echo "   2. Add PostgreSQL database"
echo "   3. Set DATABASE_URL, AUTO_CREATE_TABLES=true"
echo "   4. Set MEMBRA_DATA_ENCRYPTION_KEY and ACCESS_SIGNING_SECRET"
echo "   5. Wait for rebuild"
echo "   6. Configure macOS extension with your Space URL"
echo ""

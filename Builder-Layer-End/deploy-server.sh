#!/bin/bash

# Complete Deployment Script for All Layers
# This script deploys both Builder-Layer-End (Pipeline) and Layer-Business (Backend + Frontend)

set -e  # Exit on error

PROJECT_DIR="/home/deepminds/deploy"

echo "============================================"
echo "Starting Complete Deployment Process"
echo "============================================"

# Navigate to project directory
cd $PROJECT_DIR

# Pull latest code
echo ""
echo "=========================================="
echo "Step 1: Pulling latest code from GitHub"
echo "=========================================="
git fetch origin
git reset --hard origin/main || git reset --hard origin/master

# ===========================================
# DEPLOY BUILDER-LAYER-END (PIPELINE)
# ===========================================
echo ""
echo "=========================================="
echo "Step 2: Deploying Builder-Layer-End"
echo "=========================================="
cd $PROJECT_DIR/Builder-Layer-End

# Stop and remove old containers
echo "Stopping pipeline containers..."
docker-compose -f docker-compose.test.yml down

# Pull latest images
echo "Pulling latest Docker images..."
docker-compose -f docker-compose.test.yml pull

# Build and start containers
echo "Building and starting pipeline containers..."
docker-compose -f docker-compose.test.yml up -d --build

# Wait for services to be ready
echo "Waiting for pipeline services to start..."
sleep 10

# Check pipeline health
echo "Checking pipeline containers..."
docker-compose -f docker-compose.test.yml ps

# ===========================================
# DEPLOY LAYER-BUSINESS (BACKEND)
# ===========================================
echo ""
echo "=========================================="
echo "Step 3: Deploying Backend"
echo "=========================================="
cd $PROJECT_DIR/Layer-Business/backend

# Install/Update dependencies
if [ ! -d "node_modules" ]; then
  echo "Installing backend dependencies..."
  npm install
else
  echo "Updating backend dependencies..."
  npm install --production
fi

# Build backend
echo "Building backend..."
npm run build

# Deploy with PM2
echo "Deploying backend with PM2..."
if command -v pm2 &> /dev/null; then
  pm2 delete hcmc-backend || true
  pm2 start dist/server.js --name hcmc-backend --max-memory-restart 4G
  pm2 save
else
  echo "Installing PM2..."
  npm install -g pm2
  pm2 start dist/server.js --name hcmc-backend --max-memory-restart 4G
  pm2 startup
  pm2 save
fi

# ===========================================
# DEPLOY LAYER-BUSINESS (FRONTEND)
# ===========================================
echo ""
echo "=========================================="
echo "Step 4: Deploying Frontend"
echo "=========================================="
cd $PROJECT_DIR/Layer-Business/frontend

# Install/Update dependencies
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
else
  echo "Updating frontend dependencies..."
  npm install
fi

# Build frontend
echo "Building frontend..."
npm run build

# Deploy with PM2
echo "Deploying frontend with PM2..."
pm2 delete hcmc-frontend || true
pm2 start npm --name hcmc-frontend -- run preview
pm2 save

# ===========================================
# VERIFICATION AND CLEANUP
# ===========================================
echo ""
echo "=========================================="
echo "Step 5: Verification"
echo "=========================================="

# Wait for all services
echo "Waiting for all services to stabilize..."
sleep 10

# Check Pipeline
echo ""
echo "--- Pipeline Containers ---"
cd $PROJECT_DIR/Builder-Layer-End
RUNNING=$(docker-compose -f docker-compose.test.yml ps --services --filter "status=running" | wc -l)
TOTAL=$(docker-compose -f docker-compose.test.yml ps --services | wc -l)
echo "Pipeline: $RUNNING/$TOTAL containers running"

if [ $RUNNING -lt $TOTAL ]; then
    echo "WARNING: Not all pipeline containers are running!"
    docker-compose -f docker-compose.test.yml ps
else
    echo "SUCCESS: All pipeline containers running!"
fi

# Check PM2 Services
echo ""
echo "--- Backend & Frontend (PM2) ---"
pm2 list

# Show logs
echo ""
echo "--- Recent Pipeline Logs ---"
cd $PROJECT_DIR/Builder-Layer-End
docker-compose -f docker-compose.test.yml logs --tail=30

echo ""
echo "--- Backend Logs ---"
pm2 logs hcmc-backend --lines 20 --nostream

echo ""
echo "--- Frontend Logs ---"
pm2 logs hcmc-frontend --lines 20 --nostream

# Clean up
echo ""
echo "=========================================="
echo "Step 6: Cleanup"
echo "=========================================="
echo "Cleaning up unused Docker resources..."
docker system prune -f

echo ""
echo "============================================"
echo "Complete Deployment Finished!"
echo "============================================"
echo ""
echo "Services Status:"
echo "  - Pipeline (Docker):  $RUNNING/$TOTAL containers"
echo "  - Backend (PM2):      Check 'pm2 status'"
echo "  - Frontend (PM2):     Check 'pm2 status'"
echo ""
echo "Useful commands:"
echo "  - Check pipeline:  cd $PROJECT_DIR/Builder-Layer-End && docker-compose -f docker-compose.test.yml ps"
echo "  - Check apps:      pm2 status"
echo "  - View logs:       pm2 logs"
echo "  - Restart backend: pm2 restart hcmc-backend"
echo "  - Restart frontend: pm2 restart hcmc-frontend"
echo "============================================"

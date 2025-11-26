# Quick Setup Script for Server
# Run this once on the server to prepare for deployments

#!/bin/bash

echo "============================================"
echo "Server Setup Script"
echo "============================================"

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "Docker already installed"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "Docker Compose already installed"
fi

# Install Node.js v20.x
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    echo "Node.js already installed"
fi

# Install PM2
if ! command -v pm2 &> /dev/null; then
    echo "Installing PM2..."
    sudo npm install -g pm2
    
    # Setup PM2 startup
    echo "Setting up PM2 startup..."
    pm2 startup
else
    echo "PM2 already installed"
fi

# Install useful tools
echo "Installing useful tools..."
sudo apt-get install -y git curl wget nano htop net-tools

# Create project directory
echo "Creating project directory..."
cd /home/deepminds
if [ ! -d "deploy" ]; then
    echo "Cloning repository..."
    git clone https://github.com/NguyenDinhAnhTuan04/deploy.git
    cd deploy
else
    echo "Repository already exists"
    cd deploy
    git pull
fi

# Setup Git credentials store
echo "Setting up Git credentials..."
git config --global credential.helper store

# Create necessary directories
echo "Creating directories..."
mkdir -p /home/deepminds/deploy/Layer-Business/backend/logs
mkdir -p /home/deepminds/deploy/Layer-Business/backend/data

# Set permissions
echo "Setting permissions..."
sudo chown -R deepminds:deepminds /home/deepminds/deploy

# Display versions
echo ""
echo "============================================"
echo "Installation Complete! Versions:"
echo "============================================"
docker --version
docker-compose --version
node --version
npm --version
pm2 --version
git --version

echo ""
echo "============================================"
echo "Next Steps:"
echo "============================================"
echo "1. Configure Git credentials (if using HTTPS):"
echo "   cd /home/deepminds/deploy"
echo "   git pull  # Enter credentials when prompted"
echo ""
echo "2. Copy and configure environment files:"
echo "   cp Layer-Business/.env.production Layer-Business/backend/.env"
echo "   cp Layer-Business/frontend/.env.production Layer-Business/frontend/.env"
echo "   nano Layer-Business/backend/.env  # Edit API keys"
echo ""
echo "3. Test initial deployment:"
echo "   chmod +x deploy-server.sh"
echo "   ./deploy-server.sh"
echo ""
echo "4. Push code to GitHub to trigger CI/CD"
echo "============================================"

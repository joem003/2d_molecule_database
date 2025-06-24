#!/bin/bash

# Google Cloud VM setup script
set -e

echo "☁️  Setting up Google Cloud VM for 2D Molecule Database"
echo "====================================================="

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
echo "📦 Installing required packages..."
sudo apt-get install -y \
    git \
    python3 \
    python3-pip \
    build-essential \
    curl

# Install Podman
echo "🐳 Installing Podman..."
sudo apt-get install -y podman

# Install podman-compose
echo "🔧 Installing podman-compose..."
pip3 install podman-compose

# Configure firewall for web access
echo "🔥 Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 5000/tcp
sudo ufw --force enable

# Create app directory
echo "📁 Setting up application directory..."
mkdir -p ~/molecule-db
cd ~/molecule-db

# Clone repository (you'll need to update this URL)
echo "📥 Cloning repository..."
# git clone https://github.com/YOUR_USERNAME/2d-molecule-database.git .

echo ""
echo "✅ VM setup complete!"
echo ""
echo "Next steps:"
echo "1. Clone your repository to ~/molecule-db"
echo "2. Run: cd ~/molecule-db && ./scripts/build_database.sh"
echo "3. Run: ./scripts/start_services.sh"
echo ""
echo "🌐 External access:"
echo "  API: http://[VM_EXTERNAL_IP]:5000"
echo "  Web: http://[VM_EXTERNAL_IP]:3000"
#!/bin/bash

# Start services using Podman Compose
set -e

echo "🚀 Starting 2D Molecule Database Services"
echo "========================================"

# Check if podman-compose is available
if ! command -v podman-compose &> /dev/null; then
    echo "⚠️  podman-compose not found. Installing..."
    pip install podman-compose
fi

# Stop any existing services
echo "🛑 Stopping existing services..."
podman-compose -f podman-compose.yml down 2>/dev/null || true

# Build and start services
echo "🔨 Building and starting services..."
podman-compose -f podman-compose.yml up --build -d

echo ""
echo "✅ Services started successfully!"
echo ""
echo "🌐 Access points:"
echo "  API: http://localhost:5000"
echo "  Web: http://localhost:3000"
echo ""
echo "📊 To check status:"
echo "  podman-compose -f podman-compose.yml ps"
echo ""
echo "📋 To view logs:"
echo "  podman-compose -f podman-compose.yml logs -f"
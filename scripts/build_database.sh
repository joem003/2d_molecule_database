#!/bin/bash

# Build database script for production deployment
set -e

echo "🧬 Building PubChem 2D Molecule Database"
echo "========================================"

# Check if data directory exists
mkdir -p data

# Set default values
MAX_FILES=${MAX_FILES:-1}
KEEP_DOWNLOADS=${KEEP_DOWNLOADS:-false}

echo "Configuration:"
echo "  Max files: $MAX_FILES"
echo "  Keep downloads: $KEEP_DOWNLOADS"
echo "  Output: data/molecule_2d_minimal.lmdb"

# Build command
BUILD_CMD="python build_molecule_db_minimal.py --db-path data/molecule_2d_minimal.lmdb --download-dir data/downloads --max-files $MAX_FILES"

if [ "$KEEP_DOWNLOADS" = "true" ]; then
    BUILD_CMD="$BUILD_CMD --keep-downloads"
fi

echo ""
echo "Running: $BUILD_CMD"
echo ""

# Run the build
$BUILD_CMD

echo ""
echo "✅ Database build complete!"
echo ""

# Show statistics
if [ -f "query_minimal.py" ]; then
    echo "Database Statistics:"
    python query_minimal.py
fi
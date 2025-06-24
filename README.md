# Minimal 2D Molecule Database

An ultra-efficient system for storing and rendering 2D molecular structures from PubChem SDF files. Stores only essential data: atom coordinates, elements, and bond connectivity.

## Key Features

- **45% smaller database** than storing full MOL blocks  
- **Minimal data format**: Only 2D coordinates, elements, and bonds
- **Fast rendering**: Optimized JSON format for web display
- **TypeScript web viewer** with clean 2D structure rendering
- **Containerized deployment** with Podman support
- **Google Cloud ready** with deployment scripts

## Database Scale

- **Current**: 367k molecules from 1 file (~700MB)
- **Full PubChem**: ~129M molecules estimated (~238GB)
- **Space savings**: 45% vs full MOL format (~197GB saved)

## Quick Start

### Local Development

```bash
# 1. Clone repository
git clone <repository-url>
cd 2d-molecule-database

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build database (first file)
./scripts/build_database.sh

# 4. Start services
./scripts/start_services.sh
```

### Production Deployment (Google Cloud)

```bash
# 1. Create and setup VM
gcloud compute instances create molecule-db-vm \
  --machine-type=e2-standard-8 \
  --disk-size=500GB \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud

# 2. SSH to VM and run setup
gcloud compute ssh molecule-db-vm
./deploy/gcp-vm-setup.sh

# 3. Build full database
MAX_FILES=352 ./scripts/build_database.sh

# 4. Start services
./scripts/start_services.sh
```

## Architecture

### Components
- **build_molecule_db_minimal.py** - Creates optimized LMDB database
- **api_server_minimal.py** - FastAPI server for minimal structure data  
- **web/** - TypeScript web application for viewing molecules

### Data Format
```json
{
  "a": [{"x": 2.866, "y": 0.75, "e": "O"}, ...],  // atoms
  "b": [{"f": 0, "t": 6, "o": 1}, ...]            // bonds  
}
```

Where:
- `a`: atoms with x,y coordinates and element symbol
- `b`: bonds with from/to atom indices and bond order

## Container Deployment

### Using Podman Compose
```bash
# Build and start all services
podman-compose -f podman-compose.yml up --build -d

# Check status
podman-compose -f podman-compose.yml ps

# View logs
podman-compose -f podman-compose.yml logs -f
```

### Manual Container Build
```bash
# Build API container
podman build -f Containerfile -t molecule-api .

# Build web container  
podman build -f web/Containerfile -t molecule-web ./web

# Run with volume mount for database
podman run -d -p 5000:5000 -v ./data:/app/data:Z molecule-api
podman run -d -p 3000:3000 molecule-web
```

## Environment Variables

- `MAX_FILES` - Number of SDF files to process (default: 1)
- `KEEP_DOWNLOADS` - Keep downloaded SDF files (default: false)
- `DB_PATH` - Database path (default: data/molecule_2d_minimal.lmdb)

## Performance

### Local Testing (1 file)
- **367,783 molecules**
- **693 MB database**
- **~1,174 bytes per molecule**
- **Processing time**: ~2 hours

### Full Scale Estimates (352 files)
- **~129 million molecules**
- **~238 GB database**
- **~704 hours processing** (~29 days)
- **112 GB download size**

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/molecule/{inchikey}` - Get minimal 2D structure data

## Example InChIKeys

- RDHQFKQIGNGIED-UHFFFAOYSA-N
- AAAFZMYJJHWUPN-UHFFFAOYSA-N  
- AAAGUOJHUURVQP-UHFFFAOYSA-N

## Development

### Project Structure
```
├── api_server_minimal.py      # FastAPI server
├── build_molecule_db_minimal.py # Database builder
├── estimate_total_size.py     # Size estimation tool
├── scripts/                   # Deployment scripts
├── deploy/                    # Cloud deployment configs
├── web/                       # TypeScript frontend
├── Containerfile             # API container config
└── podman-compose.yml        # Service orchestration
```

### Testing
```bash
python test_minimal_system.py
python estimate_total_size.py
```

## License

MIT License - see LICENSE file for details.
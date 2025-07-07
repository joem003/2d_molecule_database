# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a 2D molecular database system that stores and renders minimal 2D molecular structures from PubChem SDF files. The system uses only essential data (atom coordinates, elements, bond connectivity) achieving 45% space savings compared to full MOL format.

## Architecture

### Core Components
- **build_molecule_db_minimal.py**: Downloads PubChem SDF files and creates optimized LMDB database
- **api_server_minimal.py**: FastAPI server serving minimal 2D structure data via REST API
- **web/**: TypeScript/Vite frontend for interactive molecule visualization

### Data Flow
1. SDF files downloaded from PubChem FTP
2. Processed with RDKit to extract 2D coordinates
3. Stored in LMDB as minimal JSON: `{"a": [atoms], "b": [bonds]}`
4. API serves data by InChIKey lookup
5. Web frontend renders molecules on HTML5 canvas

## Development Commands

### Database Building
```bash
# Build with default settings (1 file)
./scripts/build_database.sh

# Build with custom settings
MAX_FILES=352 KEEP_DOWNLOADS=true ./scripts/build_database.sh

# Direct Python command
python build_molecule_db_minimal.py --db-path data/molecule_2d_minimal.lmdb --max-files 1
```

### Services
```bash
# Start all services with Podman Compose
./scripts/start_services.sh

# Manual service control
podman-compose -f podman-compose.yml up --build -d
podman-compose -f podman-compose.yml down
```

### Frontend Development
```bash
# From web/ directory
npm run dev        # Development server (port 3000)
npm run build      # TypeScript compilation + Vite build
npm run preview    # Preview built application
```

### Testing
```bash
python test_minimal_system.py    # Test API endpoints and data format
python estimate_total_size.py    # Database size estimation
```

## Key Environment Variables

- `MAX_FILES`: Number of SDF files to process (default: 1, full: 352)
- `KEEP_DOWNLOADS`: Keep downloaded SDF files (default: false)
- `DB_PATH`: Database path (default: data/molecule_2d_minimal.lmdb)

## API Endpoints

- `GET /api/health`: Health check
- `GET /api/molecule/{inchikey}`: Get minimal 2D structure data

## Development Notes

- Database uses LMDB for high-performance key-value storage
- Minimal JSON format: atoms as `{x, y, e}`, bonds as `{f, t, o}`
- Web frontend uses HTML5 Canvas for 2D molecule rendering
- API has CORS enabled for development
- Production deployment uses Podman containers
- System designed for ~129M molecules (~238GB at full scale)
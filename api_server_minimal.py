#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Optional, List
import lmdb
import logging
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Minimal 2D Molecule API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MoleculeDB:
    def __init__(self, db_path="molecule_2d_minimal.lmdb"):
        self.db_path = db_path
        self.env = lmdb.open(db_path, readonly=True)
    
    def get_molecule(self, inchikey: str) -> Optional[str]:
        """Retrieve molecule data by InChIKey"""
        with self.env.begin() as txn:
            mol_data = txn.get(inchikey.encode())
            return mol_data.decode() if mol_data else None

# Initialize database
db = MoleculeDB()

@app.get("/api/molecule/{inchikey}")
async def get_molecule(inchikey: str):
    """Get molecule 2D structure data by InChIKey"""
    molecule_data = db.get_molecule(inchikey)
    
    if molecule_data:
        return Response(content=molecule_data, media_type="application/json")
    else:
        raise HTTPException(status_code=404, detail="Molecule not found")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Minimal FastAPI server for molecule database")
    parser.add_argument('--db-path', default='molecule_2d_minimal.lmdb', help='Path to LMDB database')
    parser.add_argument('--port', type=int, default=5000, help='Port to run server on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    
    args = parser.parse_args()
    
    db = MoleculeDB(args.db_path)
    uvicorn.run(app, host=args.host, port=args.port)
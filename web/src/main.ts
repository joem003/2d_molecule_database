interface MoleculeData {
  a: Array<{x: number, y: number, e: string}>; // atoms
  b: Array<{f: number, t: number, o: number}>; // bonds
}

class MoleculeViewer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private inchikeyInput: HTMLInputElement;
  private searchBtn: HTMLButtonElement;
  private loadingEl: HTMLElement;
  private errorEl: HTMLElement;
  private moleculeInfo: HTMLElement;
  private apiUrl: string = 'http://127.0.0.1:5000/api';

  constructor() {
    this.canvas = document.getElementById('molecule-canvas') as HTMLCanvasElement;
    this.ctx = this.canvas.getContext('2d')!;
    this.inchikeyInput = document.getElementById('inchikey-input') as HTMLInputElement;
    this.searchBtn = document.getElementById('search-btn') as HTMLButtonElement;
    this.loadingEl = document.getElementById('loading')!;
    this.errorEl = document.getElementById('error')!;
    this.moleculeInfo = document.getElementById('molecule-info')!;

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    this.searchBtn.addEventListener('click', () => this.searchMolecule());
    this.inchikeyInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.searchMolecule();
      }
    });
  }

  private async searchMolecule(): Promise<void> {
    const inchikey = this.inchikeyInput.value.trim();
    
    if (!inchikey) {
      this.showError('Please enter an InChIKey');
      return;
    }

    if (!this.validateInChIKey(inchikey)) {
      this.showError('Invalid InChIKey format');
      return;
    }

    this.showLoading();

    try {
      const response = await fetch(`${this.apiUrl}/molecule/${inchikey}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Molecule not found in database');
        }
        throw new Error('Failed to fetch molecule data');
      }

      const data: MoleculeData = await response.json();
      this.displayMolecule(data);
      this.displayMoleculeInfo(inchikey);
    } catch (error) {
      this.showError(error instanceof Error ? error.message : 'An error occurred');
    }
  }

  private validateInChIKey(inchikey: string): boolean {
    const inchikeyRegex = /^[A-Z]{14}-[A-Z]{10}-[A-Z]$/;
    return inchikeyRegex.test(inchikey);
  }

  private displayMolecule(data: MoleculeData): void {
    this.hideLoading();
    this.hideError();

    // Convert to rendering format
    const atoms = data.a.map(atom => ({
      x: atom.x,
      y: atom.y,
      element: atom.e
    }));
    
    const bonds = data.b.map(bond => ({
      from: bond.f,
      to: bond.t,
      type: bond.o
    }));

    this.drawMolecule(atoms, bonds);
  }

  private drawMolecule(
    atoms: Array<{x: number, y: number, element: string}>,
    bonds: Array<{from: number, to: number, type: number}>
  ): void {
    // Calculate bounds
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    atoms.forEach(atom => {
      minX = Math.min(minX, atom.x);
      minY = Math.min(minY, atom.y);
      maxX = Math.max(maxX, atom.x);
      maxY = Math.max(maxY, atom.y);
    });

    // Set canvas size
    const padding = 50;
    const targetSize = 600;
    const molWidth = maxX - minX;
    const molHeight = maxY - minY;
    const scale = Math.min(targetSize / molWidth, targetSize / molHeight) * 0.8;
    
    this.canvas.width = targetSize;
    this.canvas.height = targetSize;
    
    // Clear canvas
    this.ctx.fillStyle = 'white';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Transform coordinates
    const transformX = (x: number) => (x - minX) * scale + padding;
    const transformY = (y: number) => (y - minY) * scale + padding;
    
    // Draw bonds
    this.ctx.strokeStyle = '#333';
    this.ctx.lineWidth = 2;
    
    bonds.forEach(bond => {
      const from = atoms[bond.from];
      const to = atoms[bond.to];
      
      this.ctx.beginPath();
      this.ctx.moveTo(transformX(from.x), transformY(from.y));
      this.ctx.lineTo(transformX(to.x), transformY(to.y));
      this.ctx.stroke();
      
      // Draw double/triple bonds
      if (bond.type === 2) {
        const angle = Math.atan2(to.y - from.y, to.x - from.x);
        const offset = 4;
        const dx = Math.sin(angle) * offset;
        const dy = -Math.cos(angle) * offset;
        
        this.ctx.beginPath();
        this.ctx.moveTo(transformX(from.x) + dx, transformY(from.y) + dy);
        this.ctx.lineTo(transformX(to.x) + dx, transformY(to.y) + dy);
        this.ctx.stroke();
      }
    });
    
    // Draw atoms
    this.ctx.font = '16px Arial';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    
    atoms.forEach(atom => {
      if (atom.element !== 'C') {
        // Draw background circle for non-carbon atoms
        this.ctx.fillStyle = 'white';
        this.ctx.beginPath();
        this.ctx.arc(transformX(atom.x), transformY(atom.y), 12, 0, 2 * Math.PI);
        this.ctx.fill();
        
        // Draw element symbol
        this.ctx.fillStyle = this.getElementColor(atom.element);
        this.ctx.fillText(atom.element, transformX(atom.x), transformY(atom.y));
      }
    });
  }

  private getElementColor(element: string): string {
    const colors: Record<string, string> = {
      'H': '#666',
      'C': '#333',
      'N': '#3050F8',
      'O': '#FF0D0D',
      'F': '#90E050',
      'P': '#FF8000',
      'S': '#FFFF30',
      'Cl': '#1FF01F',
      'Br': '#A62929',
      'I': '#940094'
    };
    return colors[element] || '#333';
  }

  private displayMoleculeInfo(inchikey: string): void {
    this.moleculeInfo.classList.remove('hidden');
    
    document.getElementById('inchikey-display')!.textContent = inchikey;
    document.getElementById('formula-display')!.textContent = 'N/A';
    document.getElementById('smiles-display')!.textContent = 'N/A';
  }

  private showLoading(): void {
    this.loadingEl.classList.remove('hidden');
    this.errorEl.classList.add('hidden');
    this.moleculeInfo.classList.add('hidden');
    this.canvas.style.display = 'none';
  }

  private hideLoading(): void {
    this.loadingEl.classList.add('hidden');
    this.canvas.style.display = 'block';
  }

  private showError(message: string): void {
    this.errorEl.textContent = message;
    this.errorEl.classList.remove('hidden');
    this.loadingEl.classList.add('hidden');
    this.canvas.style.display = 'none';
    this.moleculeInfo.classList.add('hidden');
  }

  private hideError(): void {
    this.errorEl.classList.add('hidden');
  }
}

// Initialize the viewer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new MoleculeViewer();
});
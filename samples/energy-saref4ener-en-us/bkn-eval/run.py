"""Run local historical-projection regression; not model or platform acceptance."""
import subprocess,sys
from pathlib import Path
raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve().parents[3]/'tools/energy_saref4ener/verify.py'),'--sample',Path(__file__).resolve().parents[1].name.rsplit('saref4ener-',1)[1]]))

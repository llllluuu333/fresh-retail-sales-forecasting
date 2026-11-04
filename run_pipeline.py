"""Run learning scripts in dependency order with the current Python interpreter."""
from pathlib import Path
import subprocess
import sys

scripts = Path(__file__).resolve().parent / 'scripts'
for script in sorted(scripts.glob('[0-9][0-9]_*.py')):
    print(f'\n=== {script.name} ===', flush=True)
    subprocess.run([sys.executable, str(script)], check=True)

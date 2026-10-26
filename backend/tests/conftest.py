import sys
from pathlib import Path

# Os módulos do backend são importados pelo nome (como faz ecovision_local_modf.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import sys
from pathlib import Path


backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-32-bytes-long-key")

import importlib.util
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP = ROOT / "Hire_Reactor_Recruitment_Manager_FINAL(1).zip"

# Gunicorn can start multiple workers at the same time. Each worker must have
# its own extraction directory so workers never delete/rebuild each other's
# templates while the full Flask application is importing.
EXTRACT = Path(tempfile.gettempdir()) / f"hire_reactor_recruitment_app_{os.getpid()}"
APP_DIR = EXTRACT / "Hire_Reactor_Recruitment_Manager_FINAL"

required = [
    APP_DIR / "app.py",
    APP_DIR / "templates" / "login.html",
    APP_DIR / "static" / "style.css",
]
if not all(path.exists() for path in required):
    EXTRACT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as archive:
        archive.extractall(EXTRACT)

os.environ.setdefault("HR_AUTO_INIT_DB", "1")
os.environ.setdefault("HR_HTTPS", "1")

sys.path.insert(0, str(APP_DIR))
spec = importlib.util.spec_from_file_location("hire_reactor_full_app", APP_DIR / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app

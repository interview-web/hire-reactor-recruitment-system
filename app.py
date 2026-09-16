import importlib.util
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP = ROOT / "Hire_Reactor_Recruitment_Manager_FINAL(1).zip"
EXTRACT = Path(tempfile.gettempdir()) / "hire_reactor_recruitment_app"
APP_DIR = EXTRACT / "Hire_Reactor_Recruitment_Manager_FINAL"

# Rebuild the extracted application if any required runtime file is missing.
# This avoids a stale/incomplete /tmp extraction surviving a redeploy.
required = [APP_DIR / "app.py", APP_DIR / "templates" / "login.html", APP_DIR / "static" / "style.css"]
if not all(path.exists() for path in required):
    if EXTRACT.exists():
        shutil.rmtree(EXTRACT, ignore_errors=True)
    EXTRACT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as archive:
        archive.extractall(EXTRACT)

# The full application initializes its schema when HR_AUTO_INIT_DB is enabled.
os.environ.setdefault("HR_AUTO_INIT_DB", "1")
os.environ.setdefault("HR_HTTPS", "1")

sys.path.insert(0, str(APP_DIR))
spec = importlib.util.spec_from_file_location("hire_reactor_full_app", APP_DIR / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app

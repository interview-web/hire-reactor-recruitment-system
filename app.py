import importlib.util
import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIP = ROOT / "Hire_Reactor_Recruitment_Manager_FINAL(1).zip"
EXTRACT = Path(tempfile.gettempdir()) / "hire_reactor_recruitment_app"
APP_DIR = EXTRACT / "Hire_Reactor_Recruitment_Manager_FINAL"

if not (APP_DIR / "app.py").exists():
    EXTRACT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as archive:
        archive.extractall(EXTRACT)

# The full application initializes its schema when HR_AUTO_INIT_DB is enabled.
# DATABASE_URL can be supplied by Render later to move persistence to PostgreSQL.
os.environ.setdefault("HR_AUTO_INIT_DB", "1")
os.environ.setdefault("HR_HTTPS", "1")

sys.path.insert(0, str(APP_DIR))
spec = importlib.util.spec_from_file_location("hire_reactor_full_app", APP_DIR / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app

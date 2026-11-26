import os
import tempfile

# Tests use throwaway SQLite files, never your real data/sqlite databases.
_tmp = tempfile.mkdtemp(prefix="incident-tests-")
os.environ["APP_DB"] = os.path.join(_tmp, "app.db")
os.environ["CHECKPOINT_DB"] = os.path.join(_tmp, "checkpoints.db")

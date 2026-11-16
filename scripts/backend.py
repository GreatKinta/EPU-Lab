"""Run backend CLI on host with private root .env, mapped localhost database."""

import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        root
        / "backend"
        / ".venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    ),
)
from dotenv import dotenv_values

env = {
    **os.environ,
    **{k: v for k, v in dotenv_values(root / ".env").items() if v is not None},
}
env["DATABASE_URL"] = env["DATABASE_URL"].replace("@postgres:", "@127.0.0.1:")
env["UPLOAD_DIR"] = str(root / "uploads")
env["CHAIN_CONFIG_PATH"] = str(root / "runtime" / "local.json")
env["RPC_URL"] = "http://127.0.0.1:8545"
if "--test-db" in sys.argv:
    sys.argv.remove("--test-db")
    env["DATABASE_URL"] = env["DATABASE_URL"].rsplit("/", 1)[0] + "/labchain_test"
command = sys.argv[1:]
if not command:
    command = ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]
command[0] = str(root / "backend" / ".venv" / "bin" / command[0])
raise SystemExit(subprocess.call(command, cwd=root / "backend", env=env))

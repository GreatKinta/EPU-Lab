"""Check prerequisites without installing packages or changing host configuration."""

import argparse
import json
import platform
import shutil
import subprocess
from pathlib import Path


def probe(command):
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=20
        )
        return {
            "ok": result.returncode == 0,
            "output": (result.stdout + result.stderr).strip()[:1500],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "output": type(exc).__name__}


parser = argparse.ArgumentParser()
parser.add_argument("--context", default="desktop-linux")
parser.add_argument("--json", action="store_true")
args = parser.parse_args()
report = {"python": {"ok": True, "output": platform.python_version()}}
for label, command in {
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "git": ["git", "--version"],
    "docker": ["docker", "--version"],
    "compose": ["docker", "compose", "version"],
    "docker_daemon": [
        "docker",
        "--context",
        args.context,
        "info",
        "--format",
        "{{.ServerVersion}}",
    ],
}.items():
    report[label] = probe(command)
usage = shutil.disk_usage(Path(__file__).resolve().parents[1])
report["disk"] = {
    "ok": usage.free > 10 * 1024**3,
    "output": f"{usage.free / 1024**3:.1f} GiB available",
}
report["deployment_ready"] = all(
    report[key]["ok"] for key in ["docker", "compose", "docker_daemon", "disk"]
)
print(
    json.dumps(report, indent=2)
    if args.json
    else "\n".join(f"{key}: {value}" for key, value in report.items())
)
raise SystemExit(0 if report["deployment_ready"] else 1)

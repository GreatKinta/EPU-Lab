"""Create local secrets once. Never overwrite an existing .env."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    print(".env already exists; kept unchanged")
else:
    content = (root / ".env.example").read_text()
    content = content.replace("replace-with-random-password", secrets.token_hex(24))
    content = content.replace(
        "replace-with-at-least-32-random-characters", secrets.token_hex(32)
    )
    content = content.replace(
        "DEMO_PASSWORD=\n", f"DEMO_PASSWORD={secrets.token_urlsafe(16)}\n"
    )
    fd = path.open("x")
    path.chmod(0o600)
    with fd:
        fd.write(content)
    print("Created private .env with generated local credentials")

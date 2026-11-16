"""Generate an optional, local Compose build override for broken Docker Desktop DNS.
IP addresses are resolved afresh on the host; system DNS settings stay unchanged.
"""

import socket
from pathlib import Path

root = Path(__file__).resolve().parents[1]
hosts = [
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "download.pytorch.org",
    "download-r2.pytorch.org",
]
entries = []
for host in hosts:
    try:
        ip = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    except socket.gaierror:
        print(f"Skipping unresolvable optional host: {host}")
        continue
    entries.append(f'        - "{host}:{ip}"')
text = "services:\n"
for service in ["backend", "ocr-init", "migrate", "frontend", "hardhat-node"]:
    text += (
        f"  {service}:\n    build:\n      extra_hosts:\n" + "\n".join(entries) + "\n"
    )
(root / "runtime").mkdir(exist_ok=True)
(root / "runtime" / "compose.build-dns.yml").write_text(text)
print(
    "Generated runtime/compose.build-dns.yml (use with -f docker-compose.yml -f runtime/compose.build-dns.yml)"
)

# Decisions

- PostgreSQL 17, Python 3.12 and Node 24 in containers. Host Python 3.14 / Node 26 are not required for container execution.
- Use stable compatible dependencies with pinned lockfiles after installing and testing. Hardhat 3 ESM configuration and ethers adapter.
- HTTP bearer JWT with a short lifetime; frontend holds token in memory. Reload requires signing in again. Production needs HTTPS.
- Secret generation is explicit and idempotent; no production/demo password hardcoded in application source.
- References: [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [Vite requirements](https://vite.dev/guide/), [Hardhat configuration](https://hardhat.org/docs/reference/configuration).

- All batch inventory operations are atomic. Equipment deletion always archives to simplify historical integrity. Copying never copies reserved stock.
- Staff can cancel APPROVED, students can cancel only their own PENDING requests. Full returns only. Creation supports per-user idempotency keys; transitions enforce status under a row lock, repeated commands return 409.
- EasyOCR CPU is the documented fallback permitted by the plan. OCR is optional to keep the default environment small; the adapter uses a real neural model, never a mock in runtime. Unit tests mock the adapter only. Real-model acceptance stays pending until its opt-in test passes.
- The host initially had a Docker Desktop DNS issue (`EAI_AGAIN`). An optional generated Compose build override maps dependency hosts using current host DNS results. It changes no OS/daemon settings and is gitignored. Images/services keep their ordinary internal Docker DNS.
- Hardhat compiler is pinned as npm `solc@0.8.28`, avoiding a second compiler download endpoint. Dependency audit overrides zod/glob/minimatch to patched versions; compatibility is checked by contract tests.
- Login limiter is in-process, designed for the default single API process. Multiple API replicas require a shared limiter before public deployment. Production account provisioning and HTTPS are operator responsibilities.
- Original uploaded images are normalized to JPEG and stored privately. OCR image requests do not persist the image or create equipment. Frontend applies suggestions only after explicit confirmation.

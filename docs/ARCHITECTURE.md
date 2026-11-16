# Architecture

Modular monolith: React SPA → FastAPI `/api/v1` → PostgreSQL. Feature modules: identity, inventory, borrowing, audit, reporting, ai. Services control transactions, repositories do not commit. Outbox worker shares the backend image and polls PostgreSQL; Web3.py and OCR are external adapters. Files are private, accessed through authenticated API.

Docker deployment serves the compiled React SPA through Nginx and proxies `/api/` to FastAPI. Python/Node toolchains, PostgreSQL, Hardhat, migrations, demo seed, worker and EasyOCR CPU all run in containers. The API uses the OCR image, while migrations/seed/worker use the smaller base backend image. An `ocr-init` job validates downloaded en/vi models in a shared named volume before API startup. Host requirements are Docker + Compose only; the separate setup Compose file generates private environment settings without host Python.

Course mapping: scripting language = Product CRUD, bulk actions, XLSX/JSON/XML, shortcuts, OCR. Blockchain = Solidity attestation, canonical snapshot, worker, receipt and independent verification. No PII or images are placed on chain.

## Attestation and recovery

Approval/return commits stock, loan state, audit, immutable snapshot, outbox and transaction metadata together. Worker claims with `FOR UPDATE SKIP LOCKED`, expires a lease after 2 minutes and acquires a session advisory lock for the shared signer. It persists nonce, signed bytes and deterministic tx hash before broadcast; uncertain delivery reuses those bytes. It reconciles contract records and receipts before marking CONFIRMED. Exceptions retry exponentially (2^attempt seconds, capped at 300), maximum 8 failed attempts; staff can retry FAILED explicitly. A known reverted receipt can receive a newly signed transaction on manual retry; an uncertain submission keeps the original bytes.

A single signer is intentionally serialized in this MVP. Readiness depends on DB/migration; RPC/OCR availability does not block inventory or physical handover. Pending/failed blockchain state remains visible independently. Local chain is ephemeral: resetting Hardhat invalidates previous attestations; preserve the node process during demos, and clearly show NOT_RECORDED after resets instead of treating stored tx hashes as proof.

Canonical v1: JSON UTF-8, sorted keys, no extra whitespace (`separators=(',', ':')`), Unicode unescaped, no NaN; integer quantities; items sorted by equipment_code; UTC timestamps with exactly six fractional digits and Z. Keccak-256 of these exact bytes. Snapshot is captured at approval/return and preserved in outbox JSONB, never rebuilt from mutable live inventory. loanRef = keccak256 UTF-8 `labchain.loan.v1:<loan UUID>`; operationId = keccak256 UTF-8 `labchain.operation.v1:<event UUID>`. On-chain contract stores only bytes32 refs/digests, kind and block timestamp. Verification recomputes the original event snapshot and reads the contract directly.

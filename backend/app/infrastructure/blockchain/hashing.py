import json

from web3 import Web3


def digest(text):
    return Web3.to_hex(Web3.keccak(text=text))


def loan_ref(loan_id):
    return digest(f"labchain.loan.v1:{loan_id}")


def operation_id(event_id):
    return digest(f"labchain.operation.v1:{event_id}")


def canonical(payload):
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported schema_version")
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def snapshot_hash(payload):
    return digest(canonical(payload))
